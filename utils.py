import os
import json
import time
import re
from zhipuai import ZhipuAI, APIRequestFailedError, APITimeoutError
try:
    from zhipuai import APIError
except ImportError:
    # Handle older versions or different structure where APIError might be named differently or not exported
    # But usually it is there. Let's check if it's ZhipuAIError or similar.
    # Actually, let's just use Exception as fallback if not found.
    class APIError(Exception): pass
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ZhipuAI client with timeout configuration
client = ZhipuAI(
    api_key=settings.final_api_key,
    base_url=settings.BASE_URL
)

def get_chat_completion(messages, stream=False, json_mode=False, max_retries=3, timeout=30, callback=None, raise_error=False):
    """
    Wrapper for ZhipuAI chat completion with retry logic and timeout.
    
    Args:
        callback: Optional async function(error_msg: str) to report errors to system log
        raise_error: If True, raise the last exception instead of returning None when all retries fail.
    """
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
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
            
        except APIRequestFailedError as e:
            # 429 Rate Limit or 500 Server Error
            error_msg = f"API Request Failed (Attempt {attempt+1}/{max_retries}): {e}"
            logger.warning(error_msg)
            if callback:
                # We can't await here easily as this is sync function, 
                # but caller usually wraps this in to_thread.
                # So we can't call async callback directly.
                # Just log for now.
                pass
            last_error = e
            
        except APITimeoutError as e:
            error_msg = f"API Timeout ({timeout}s) (Attempt {attempt+1}/{max_retries})"
            logger.warning(error_msg)
            last_error = e
            
        except APIError as e:
            error_msg = f"API Error (Attempt {attempt+1}/{max_retries}): {e}"
            logger.warning(error_msg)
            last_error = e
            
        except Exception as e:
            error_msg = f"Unknown Error (Attempt {attempt+1}/{max_retries}): {e}"
            logger.error(error_msg)
            last_error = e
            
        attempt += 1
        if attempt < max_retries:
            time.sleep(1 + attempt) # Exponential backoff: 2s, 3s, 4s...
            
    logger.error(f"Chat completion failed after {max_retries} attempts. Last error: {last_error}")
    
    if raise_error and last_error:
        raise last_error
        
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
