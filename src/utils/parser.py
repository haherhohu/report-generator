import json
import re
import ast

def extract_text_smartly(raw_content):
    """
    LLM의 응답이 JSON, 리스트, 파이썬 객체 등 어떤 형태로 래핑되어 있더라도 
    실제 마크다운 본문(텍스트)만 지능적으로 추출하여 반환합니다.
    """
    if isinstance(raw_content, (list, dict)):
        parsed = raw_content
    else:
        text = str(raw_content).strip()
        text = re.sub(r"^```(?:json|md|markdown)?\s*\n(.*?)\n```$", r"\1", text, flags=re.DOTALL | re.MULTILINE)
        
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return text

    def find_text_recursively(data):
        if isinstance(data, str):
            return data
        elif isinstance(data, list):
            return "\n\n".join(filter(None, [find_text_recursively(item) for item in data]))
        elif isinstance(data, dict):
            if data.get('type') == 'text' and 'text' in data:
                return str(data['text'])
            for key in ['text', 'content', 'message', 'output', 'draft', 'markdown', 'response']:
                if key in data and isinstance(data[key], str):
                    return data[key]
            
            longest_str = ""
            for val in data.values():
                extracted = find_text_recursively(val)
                if len(extracted) > len(longest_str):
                    longest_str = extracted
            return longest_str
        return str(data)
        
    extracted_text = find_text_recursively(parsed)
    return extracted_text if extracted_text else str(raw_content)