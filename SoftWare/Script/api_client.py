import requests
import os

# --- USER CONFIGURATION ---
API_KEY = 'sk-91c8333c0f754ede8de847fadade03b4'
API_URL = 'https://api.deepseek.com/chat/completions'
# 修改为正确的相对路径
SPINNER_GIF_URL = os.path.join('SoftWare', 'Image', 'loading', 'loading3.gif')
# --- END USER CONFIGURATION --

def get_deepseek_reply(messages):
    """
    Calls the Deepseek API and returns the AI's reply.
    
    Args:
        messages (list): A list of dictionaries, where each dictionary represents a message
                         with 'role' and 'content' keys. This is the chat history.
    """
    payload = {
        "model": "deepseek-chat",
        "messages": messages
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # 添加一个120秒的超时设置，防止请求无限期挂起
        response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        return "Error: API request timed out after 120 seconds."
    except Exception as e:
        return f"Error: {str(e)}"

def get_topic_from_reply(user_question):
    """
    通过一个特殊的API请求，从用户问题中提取一个简短的对话主题。
    """
    messages = [
        {"role": "system", "content": "你是一位专业的标题生成助手。请根据用户的问题，用5个字以内，为该问题提炼一个简洁、清晰的标题。只需要返回标题，不要有任何额外的话。如果问题无法提炼，请返回'新对话'。"},
        {"role": "user", "content": user_question}
    ]
    
    try:
        reply = get_deepseek_reply(messages)
        # 确保返回的标题不包含多余的标点或换行
        clean_title = reply.strip().replace('"', '').replace("'", "").replace("。", "")
        return clean_title if clean_title else "新对话"
    except Exception as e:
        print(f"获取对话主题失败: {e}")
        return "新对话"