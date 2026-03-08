import os
import json
import time
import re
from zhipuai import ZhipuAI
from app.core.config import settings

# ZhipuAI client with timeout configuration
client = ZhipuAI(
    api_key=settings.API_KEY,
    base_url=settings.BASE_URL
)

def get_chat_completion(messages, stream=False, json_mode=False, max_retries=3, timeout=30):
    """
    Wrapper for ZhipuAI chat completion with retry logic and timeout.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            # We can't directly set timeout on method call for zhipuai easily without modifying client init
            # But the underlying httpx client respects global timeout if set on client.
            # For now, we rely on the default or network level timeouts.
            # To implement custom timeout per request, we would need to recreate client or use threading.
            # ZhipuAI 2.0+ uses httpx.Client under the hood.
            
            # Simple retry wrapper
            if stream:
                return client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=messages,
                    stream=True,
                    temperature=0.8,
                    max_tokens=4096,
                    top_p=0.7,
                    timeout=timeout
                )
            
            response = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                stream=False,
                temperature=0.8,
                max_tokens=4096,
                top_p=0.7,
                timeout=timeout
            )
            return response
            
        except Exception as e:
            attempt += 1
            # Check for rate limit error (429) specifically
            is_rate_limit = "429" in str(e) or "rate_limit" in str(e).lower()
            
            print(f"Error calling API (Attempt {attempt}/{max_retries}): {e}")
            if attempt >= max_retries:
                print("Max retries reached. Returning None.")
                return None
            
            # If it's a rate limit error, wait longer
            backoff = attempt * 2 if is_rate_limit else attempt
            time.sleep(backoff) 
    return None

def parse_json_from_response(content):
    """
    Attempts to parse JSON from a string, handling code blocks if present.
    Also handles common LLM JSON errors like unescaped quotes.
    """
    try:
        content = content.strip()
        
        # 1. Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)
        else:
            # 2. If no code blocks, try to find the first outer-most JSON object or array
            # Find the first '{' or '['
            start_idx = -1
            end_idx = -1
            stack = []
            
            for i, char in enumerate(content):
                if char in '{[':
                    if start_idx == -1:
                        start_idx = i
                    stack.append(char)
                elif char in '}]':
                    if stack:
                        last = stack[-1]
                        if (last == '{' and char == '}') or (last == '[' and char == ']'):
                            stack.pop()
                            if not stack:
                                end_idx = i + 1
                                break
            
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx]

        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Standard JSON parse failed: {e}. Attempting cleanup...")
        
        try:
            import dirtyjson
            return dirtyjson.loads(content)
        except Exception:
            pass

        # Cleanup: remove trailing commas, comments
        try:
            # Remove single-line comments // ...
            content = re.sub(r'//.*', '', content)
            # Remove trailing commas before } or ]
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            
            return json.loads(content)
        except Exception:
            pass
            
        print(f"Failed to parse JSON content: {content[:200]}...")
        return None
