import os
import requests
import json
import time

# 检查 Google GenAI SDK 是否可用
GENAI_AVAILABLE = False
try:
    # 尝试两种导入方式
    try:
        from google import genai
        GENAI_AVAILABLE = True
        print("✅ Google GenAI SDK (genai) 已加载")
    except ImportError:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
        print("✅ Google GenAI SDK (generativeai) 已加载")
except ImportError:
    print("❌ Google GenAI SDK 未安装")
    GENAI_AVAILABLE = False

from api_config import load_api_config, get_current_provider_config, get_current_provider_name

# 修改为正确的相对路径
SPINNER_GIF_URL = os.path.join('SoftWare', 'Image', 'loading', 'loading3.gif')

def get_ai_reply(messages):
    """
    Calls the configured AI API and returns the AI's reply.
    Supports DeepSeek, Gemini, and other providers.
    
    Args:
        messages (list): A list of dictionaries, where each dictionary represents a message
                         with 'role' and 'content' keys. This is the chat history.
    """
    provider_name = get_current_provider_name()
    provider_config = get_current_provider_config()
    
    api_key = (provider_config.get('api_key') or '').strip()
    api_url = (provider_config.get('api_url') or '').strip()
    model_name = (provider_config.get('model') or '').strip()

    # 对于 Gemini，直接使用系统环境变量 GEMINI_API_KEY
    if provider_name == 'gemini':
        # Gemini 使用系统环境变量，不需要在这里检查 API key
        pass
    else:
        # 对于其他提供商，需要 API key 和 URL
        if not api_key or not api_url:
            return f"Error: API key or URL is not configured for {provider_name}. Please set it in Settings > API."

    try:
        if provider_name == 'deepseek':
            return _call_deepseek_api(messages, api_key, api_url, model_name)
        elif provider_name == 'gemini':
            return _call_gemini_api_with_sdk(messages, api_key, model_name)
        else:
            # Default to OpenAI-compatible format
            return _call_openai_compatible_api(messages, api_key, api_url, model_name)
            
    except requests.exceptions.Timeout:
        return f"Error: {provider_name} API request timed out after 120 seconds."
    except Exception as e:
        return f"Error calling {provider_name} API: {str(e)}"


def _call_deepseek_api(messages, api_key, api_url, model_name):
    """Call DeepSeek API (OpenAI-compatible format)."""
    payload = {
        "messages": messages
    }
    if model_name:
        payload["model"] = model_name

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def _call_gemini_api_with_sdk(messages, api_key, model_name):
    """Call Google Gemini API using the official Google GenAI SDK with Client()."""
    if not GENAI_AVAILABLE:
        return "Error: Google GenAI SDK is not installed. Please run 'pip install google-generativeai'"
    
    try:
        # 检查系统环境变量 GEMINI_API_KEY
        env_api_key = os.getenv('GEMINI_API_KEY')
        if not env_api_key:
            return "Error: GEMINI_API_KEY 环境变量未设置。请在系统中设置 GEMINI_API_KEY 环境变量。"
        
        print(f"✅ 找到系统环境变量 GEMINI_API_KEY")
        
        # 使用您提供的实例格式：from google import genai
        from google import genai
        
        # The client gets the API key from the environment variable `GEMINI_API_KEY`.
        client = genai.Client()

        # 确保使用 gemini-2.5-flash 模型（根据您的快速入门指令）
        # Use the provided model name, or default to 'gemini-2.5-flash'
        model_to_use = model_name if model_name else 'gemini-2.5-flash'
        print(f"🤖 使用模型: {model_to_use}")

        # 简化消息处理 - 只取最后一条用户消息
        last_user_message = None
        for msg in reversed(messages):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break
        
        if not last_user_message:
            return "Error: No user message found."

        print(f"📤 发送消息: {last_user_message[:50]}...")
        
        # 使用您提供的格式调用 API
        response = client.models.generate_content(
            model=model_to_use, 
            contents=last_user_message
        )
        
        if response and response.text:
            print("✅ 收到回复")
            return response.text
        else:
            return "Error: Empty response from Gemini."
            
    except Exception as e:
        print(f"❌ Gemini API 错误: {str(e)}")
        return f"Error calling Gemini API: {str(e)}"


def _call_gemini_api(messages, api_key, api_url, model_name):
    """Call Google Gemini API (fallback REST API method)."""
    # Gemini API uses a different format
    # Convert OpenAI format to Gemini format
    
    gemini_messages = []
    for msg in messages:
        if msg['role'] == 'system':
            # Gemini doesn't have system role, prepend to first user message
            continue
        elif msg['role'] == 'user':
            gemini_messages.append({
                "role": "user",
                "parts": [{"text": msg['content']}]
            })
        elif msg['role'] == 'assistant':
            gemini_messages.append({
                "role": "model", 
                "parts": [{"text": msg['content']}]
            })
    
    # Add system message content to first user message if exists
    system_content = ""
    for msg in messages:
        if msg['role'] == 'system':
            system_content = msg['content'] + "\n\n"
            break
    
    if gemini_messages and system_content:
        gemini_messages[0]['parts'][0]['text'] = system_content + gemini_messages[0]['parts'][0]['text']
    
    payload = {
        "contents": gemini_messages,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        }
    }
    
    # Build the URL with model and API key
    full_url = f"{api_url}/{model_name}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(full_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    
    if 'candidates' in data and len(data['candidates']) > 0:
        candidate = data['candidates'][0]
        if 'content' in candidate and 'parts' in candidate['content']:
            return candidate['content']['parts'][0]['text']
    
    return "Error: Invalid response format from Gemini API."


def _call_openai_compatible_api(messages, api_key, api_url, model_name):
    """Call OpenAI-compatible API (fallback for other providers)."""
    payload = {
        "messages": messages
    }
    if model_name:
        payload["model"] = model_name

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


# Keep the old function name for backward compatibility
def get_deepseek_reply(messages):
    """Backward compatibility function."""
    return get_ai_reply(messages)

def get_topic_from_reply(user_question):
    """
    通过一个特殊的API请求，从用户问题中提取一个简短的对话主题。
    """
    messages = [
        {"role": "system", "content": "你是一位专业的标题生成助手。请根据用户的问题，用5个字以内，为该问题提炼一个简洁、清晰的标题。只需要返回标题，不要有任何额外的话。如果问题无法提炼，请返回'新对话'。"},
        {"role": "user", "content": user_question}
    ]
    
    try:
        reply = get_ai_reply(messages)
        # 确保返回的标题不包含多余的标点或换行
        clean_title = reply.strip().replace('"', '').replace("'", "").replace("。", "")
        return clean_title if clean_title else "新对话"
    except Exception as e:
        print(f"获取对话主题失败: {e}")
        return "新对话"