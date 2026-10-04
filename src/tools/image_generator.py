"""Report Image Generator Pipeline.

Generates and inserts high-quality 16:9/16:10 infographics into markdown reports:
1. Parses markdown figure callout blocks (**【그림 ...】** and AI 프롬프트).
2. Optimizes and compacts long prompts to comply with strict model token/character limits.
3. Primary generator: NVIDIA NIM (flux.2-klein-4b) with wide ratio (1344x768 / 16:9).
4. Fallback generator: Google Gemini Imagen (imagen-3.0-generate-002) with aspectRatio="16:9".
5. Rate limit protection: Configurable relaxed delay (default 4.0s) and exponential backoff.
6. Local image persistence under workspace/report/images/.
7. Injects markdown image tags (![Caption](images/file.png)) above figure specifications.
"""
from __future__ import annotations

import argparse
import base64
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

logger = logging.getLogger("report_generator.tools.image_generator")


def load_env_variables() -> None:
    """Safely loads .env variables if not already set in environment."""
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.split("#")[0].strip().strip("\"'")
                if key and not os.environ.get(key):
                    os.environ[key] = val


load_env_variables()


class ReportImageGenerator:
    """NVIDIA NIM Primary + Gemini Imagen Fallback 16:9 Image Generator."""

    def __init__(
        self,
        output_dir: str | Path = "workspace/report/images",
        sleep_interval: float = 4.0,
        aspect_ratio: str = "16:9",
        max_retries: int = 3,
        enabled: bool = False,  # 텍스트 깨짐 및 품질 이슈로 차세대 모델 출시 전까지 기본 비활성화(보류)
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sleep_interval = sleep_interval
        self.aspect_ratio = aspect_ratio
        self.max_retries = max_retries
        self.enabled = enabled

        # NVIDIA NIM credentials
        self.nim_api_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"
        self.nim_api_key = os.environ.get("NIM_API_KEY") or os.environ.get("NVIDIA_API_KEY")

        # Gemini API credentials
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={self.gemini_api_key}"
            if self.gemini_api_key
            else ""
        )

        # Resolution based on 16:9 / 16:10
        if self.aspect_ratio == "16:10":
            self.width = 1280
            self.height = 800
        else:  # 16:9 default
            self.width = 1344
            self.height = 768

    def compact_prompt(self, raw_prompt: str, max_words: int = 65) -> str:
        """Compacts and refines long prompts to avoid model token length errors.
        Extracts essential subject, flowchart structure, and clean corporate style.
        """
        clean = raw_prompt.strip()

        # Remove redundant boilerplate headers
        clean = re.sub(r"(?i)^(?:AI\s*프롬프트|프롬프트|Prompt)\s*:\s*", "", clean)

        # Truncate overly verbose parentheses lists: (step 1 -> step 2 -> ...)
        def trim_parentheses(m: re.Match) -> str:
            inner = m.group(1)
            steps = re.split(r"[➔→\->,]", inner)
            if len(steps) > 4:
                return f"({steps[0].strip()} to {steps[-1].strip()} workflow)"
            return m.group(0)

        clean = re.sub(r"\(([^)]+)\)", trim_parentheses, clean)

        # Token count management
        words = clean.split()
        if len(words) > max_words:
            core_words = words[:max_words]
            # Ensure essential styling tail is attached
            clean = " ".join(core_words)
            if not any(style in clean.lower() for style in ("palette", "vector", "infographic")):
                clean += ", clean corporate vector infographic, high resolution"

        # Final cleanup
        clean = re.sub(r"\s{2,}", " ", clean).strip(", ")
        return clean

    def generate_image_nim(self, prompt: str) -> Optional[bytes]:
        """Requests image generation using NVIDIA NIM flux.2-klein-4b."""
        if not self.nim_api_key:
            logger.warning("[ImageGen] NIM_API_KEY not configured.")
            return None

        headers = {
            "Authorization": f"Bearer {self.nim_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "prompt": prompt,
            "width": self.width,
            "height": self.height,
            "seed": 0,
            "steps": 4,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[ImageGen-NIM] Attempt {attempt}: requesting {self.width}x{self.height} image...")
                resp = requests.post(self.nim_api_url, headers=headers, json=payload, timeout=45)

                if resp.status_code == 200:
                    data = resp.json()
                    artifacts = data.get("artifacts", [])
                    if artifacts and "base64" in artifacts[0]:
                        b64_str = artifacts[0]["base64"]
                        logger.info("[ImageGen-NIM] ✅ Successfully generated via NVIDIA NIM!")
                        return base64.b64decode(b64_str)
                elif resp.status_code == 429:
                    wait_time = attempt * 5.0
                    logger.warning(f"[ImageGen-NIM] Rate limit (429) hit. Backing off for {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"[ImageGen-NIM] HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"[ImageGen-NIM] Connection error on attempt {attempt}: {e}")
                time.sleep(attempt * 3.0)

        return None

    def generate_image_gemini(self, prompt: str) -> Optional[bytes]:
        """Fallback image generation using Google Gemini Imagen (imagen-3.0-generate-002)."""
        if not self.gemini_api_key or not self.gemini_api_url:
            logger.warning("[ImageGen] GEMINI_API_KEY not configured.")
            return None

        headers = {"Content-Type": "application/json"}
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "outputMimeType": "image/png",
            },
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[ImageGen-Gemini] Attempt {attempt}: Fallback requesting Imagen-3 (16:9)...")
                resp = requests.post(self.gemini_api_url, headers=headers, json=payload, timeout=45)

                if resp.status_code == 200:
                    data = resp.json()
                    predictions = data.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        b64_str = predictions[0]["bytesBase64Encoded"]
                        logger.info("[ImageGen-Gemini] ✅ Successfully generated via Gemini Imagen-3!")
                        return base64.b64decode(b64_str)
                elif resp.status_code == 402:
                    logger.warning("[ImageGen-Gemini] Prepayment credits depleted (HTTP 402). Disabling Gemini Imagen fallback.")
                    return None
                elif resp.status_code == 429:
                    wait_time = attempt * 6.0
                    logger.warning(f"[ImageGen-Gemini] Rate limit (429) hit. Backing off for {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"[ImageGen-Gemini] HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"[ImageGen-Gemini] Connection error on attempt {attempt}: {e}")
                time.sleep(attempt * 3.0)

        return None

    def generate_image(self, prompt: str, target_filename: str) -> Optional[Path]:
        """Generates an image trying NVIDIA NIM first, falling back to Gemini Imagen."""
        if not self.enabled:
            logger.info(f"[ImageGen] ⏸️ AI 이미지 생성 기능 보류 상태 (건너뜀): {target_filename}")
            return None

        compact = self.compact_prompt(prompt)
        logger.info(f"[ImageGen] Generating '{target_filename}' with compacted prompt:\n  >> {compact}")

        # 1. Primary: NVIDIA NIM
        img_bytes = self.generate_image_nim(compact)

        # 2. Fallback: Gemini Imagen
        if not img_bytes:
            logger.info("[ImageGen] 🔄 NVIDIA NIM unavailable/failed. Switching to Gemini Imagen Fallback...")
            img_bytes = self.generate_image_gemini(compact)

        if not img_bytes:
            logger.error(f"[ImageGen] ❌ All image generation backends failed for: {target_filename}")
            return None

        # Save to disk
        dest_path = self.output_dir / target_filename
        dest_path.write_bytes(img_bytes)
        logger.info(f"[ImageGen] 💾 Saved image: {dest_path} ({len(img_bytes):,} bytes)")

        # Relaxed pacing to respect RPM limits
        if self.sleep_interval > 0:
            time.sleep(self.sleep_interval)

        return dest_path

    def process_markdown_file(
        self,
        markdown_path: str | Path,
        output_path: str | Path | None = None,
        skip_existing: bool = True,
        max_images: int = 999,
    ) -> Tuple[Path, int]:
        """Scans markdown for figure blocks, generates images, and inserts markdown links."""
        src = Path(markdown_path)
        if not src.exists():
            raise FileNotFoundError(f"File not found: {src}")

        text = src.read_text(encoding="utf-8")
        stem = src.stem

        lines = text.splitlines()
        new_lines: List[str] = []
        n = len(lines)
        i = 0

        generated_count = 0
        fig_pat = re.compile(r"^\*{0,2}(?:\[그림|【그림)\s*([ⅠⅡⅢⅣⅤⅥⅦⅧ\d\-]+)(?:\]|】)\*{0,2}\s*(.*?)$")

        while i < n:
            line = lines[i]
            m_fig = fig_pat.match(line.strip())

            if m_fig and generated_count < max_images:
                fig_num = m_fig.group(1).strip()
                fig_title = m_fig.group(2).strip().strip("*").strip()
                new_lines.append(line)
                i += 1

                # Skip blank lines right below the caption
                while i < n and not lines[i].strip():
                    i += 1

                # Check if there's already an image link right below
                has_existing_img = False
                existing_img_line = ""
                if i < n and lines[i].strip().startswith("!["):
                    has_existing_img = True
                    existing_img_line = lines[i].strip()
                    i += 1
                    while i < n and not lines[i].strip():
                        i += 1

                # Read callout block to find AI prompt or structure diagram
                callout_lines: List[str] = []
                prompt_text = ""
                diag_text = ""
                while i < n and lines[i].strip().startswith(">"):
                    cl = lines[i].strip()
                    callout_lines.append(cl)
                    if "AI 프롬프트" in cl:
                        prompt_text = cl.split("AI 프롬프트")[-1].lstrip(":* \t-")
                    elif "구조도" in cl and not diag_text:
                        diag_text = cl.split("구조도")[-1].lstrip(":* \t-")
                    i += 1

                # Sanitize filename
                safe_stem = re.sub(r"[^\w\-]", "_", stem)[:40]
                safe_fig_num = re.sub(r"[^\w\-]", "_", fig_num)
                img_filename = f"{safe_stem}_fig_{safe_fig_num}.png"
                img_dest = self.output_dir / img_filename
                rel_img_path = f"images/{img_filename}"

                # Generate image if needed
                if not has_existing_img:
                    if skip_existing and img_dest.exists() and img_dest.stat().st_size > 1000:
                        logger.info(f"[ImageGen] Using existing image: {img_dest}")
                        img_path = img_dest
                    else:
                        if prompt_text:
                            effective_prompt = prompt_text
                        elif diag_text:
                            effective_prompt = f"Professional vector infographic flowchart of {fig_title}: {diag_text[:120]}, clean corporate navy palette"
                        else:
                            effective_prompt = f"Professional vector infographic illustrating {fig_title}, isometric flowchart, corporate navy palette"

                        img_path = self.generate_image(effective_prompt, img_filename)
                        if img_path:
                            generated_count += 1

                    # Insert markdown image link right before the callout box
                    new_lines.append("")
                    new_lines.append(f"![【그림 {fig_num}】 {fig_title}]({rel_img_path})")
                    new_lines.append("")
                else:
                    new_lines.append("")
                    new_lines.append(existing_img_line)
                    new_lines.append("")

                # Re-append callout lines
                if callout_lines:
                    new_lines.extend(callout_lines)
                    new_lines.append("")
                continue

            new_lines.append(line)
            i += 1

        dest = Path(output_path) if output_path else src
        cleaned_markdown = "\n".join(new_lines)
        dest.write_text(cleaned_markdown, encoding="utf-8")
        logger.info(f"[ImageGen] Processed {src.name} -> {dest.name} ({generated_count} new images generated)")
        return dest, generated_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Report Image Generator & Markdown Inserter")
    parser.add_argument("--file", required=True, help="Path to markdown report file")
    parser.add_argument("--out", help="Path to output markdown file (default: inplace)")
    parser.add_argument("--output-dir", default="workspace/report/images", help="Directory to save generated images")
    parser.add_argument("--sleep", type=float, default=4.0, help="Sleep interval between image requests (seconds)")
    parser.add_argument("--ratio", default="16:9", choices=["16:9", "16:10"], help="Image aspect ratio")
    parser.add_argument("--max-images", type=int, default=999, help="Max images to generate")
    parser.add_argument("--export-hwpx", action="store_true", help="Auto-export to HWPX after insertion")
    parser.add_argument("--enable-generation", action="store_true", default=False, help="Explicitly enable AI image generation (default: False, suspended)")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

    generator = ReportImageGenerator(
        output_dir=args.output_dir,
        sleep_interval=args.sleep,
        aspect_ratio=args.ratio,
        enabled=args.enable_generation,
    )

    out_file = args.out if args.out else args.file
    res_path, count = generator.process_markdown_file(
        args.file,
        output_path=out_file,
        max_images=args.max_images,
    )

    if args.export_hwpx:
        from src.tools.hwpx_exporter import export_markdown_to_hwpx
        hwpx_res = export_markdown_to_hwpx(res_path)
        logger.info(f"[ImageGen] HWPX Exported: {hwpx_res}")


if __name__ == "__main__":
    main()
