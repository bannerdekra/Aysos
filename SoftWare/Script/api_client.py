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
        print("[OK] Google GenAI SDK (genai) 已加载")
    except ImportError:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
        print("[OK] Google GenAI SDK (generativeai) 已加载")
except ImportError:
    print("[ERROR] Google GenAI SDK 未安装")
    GENAI_AVAILABLE = False

from api_config import (
    get_current_provider_config,
    get_current_provider_name,
    enable_proxy,
    disable_proxy,
    get_deepseek_api_key,
)

# 导入 Gemini 上下文管理器
try:
    from gemini_context_manager import get_gemini_context_manager
    GEMINI_CONTEXT_AVAILABLE = True
    print("✅ Gemini 上下文管理器已导入")
except ImportError:
    GEMINI_CONTEXT_AVAILABLE = False
    print("⚠️ Gemini 上下文管理器未导入")

# 导入工具执行器（Function Calling）
try:
    from tool_executor import get_tool_executor, get_all_tool_schemas
    TOOL_EXECUTOR_AVAILABLE = True
    print("✅ 工具执行器已导入")
except ImportError:
    TOOL_EXECUTOR_AVAILABLE = False
    print("⚠️ 工具执行器未导入")


# 修改为正确的相对路径
SPINNER_GIF_URL = os.path.join('SoftWare', 'Image', 'loading', 'loading3.gif')

def get_ai_reply(messages, conversation_id=None, files=None, is_one_time_attachment=None, enable_tools=True):
    """
    Calls the configured AI API and returns the AI's reply.
    Supports DeepSeek, Gemini (with context and files), and other providers.
    Supports Function Calling for tool use.
    
    Args:
        messages (list): A list of dictionaries, where each dictionary represents a message
                         with 'role' and 'content' keys. This is the chat history.
        conversation_id (str, optional): 对话ID，用于 Gemini 上下文管理
        files (list, optional): 文件信息，支持两种格式：
                               1. 字典列表 [{'path': str, 'mode': str, 'file_id': str}]
                               2. 简单路径列表 [str]（配合 is_one_time_attachment 参数）
        is_one_time_attachment (bool, optional): 如果为 True，使用 Base64 内嵌（仅本次使用）；
                                                如果为 False，使用 File API 上传（上下文持久化）。
                                                当 files 为字典列表时，此参数被忽略。
        enable_tools (bool, optional): 是否启用 Function Calling 工具调用（默认True）
    """
    
    provider_name = get_current_provider_name()
    _apply_proxy_policy(provider_name)
    provider_config = get_current_provider_config()
    
    api_key = (provider_config.get('api_key') or '').strip()
    api_url = (provider_config.get('api_url') or '').strip()
    model_name = (provider_config.get('model') or '').strip()

    # 对于 Gemini，直接使用系统环境变量 GEMINI_API_KEY
    if provider_name == 'gemini':
        # Gemini 使用系统环境变量，不需要在这里检查 API key
        pass
    else:
        if provider_name == 'deepseek':
            env_key = get_deepseek_api_key()
            if env_key:
                api_key = env_key.strip()
            else:
                print("[WARNING] DeepSeek 环境变量未设置: DeepSeek-APIKEY")

        # 对于其他提供商，需要 API key 和 URL
        if not api_key or not api_url:
            return f"Error: API key or URL is not configured for {provider_name}. Please set it in Settings > API."

    try:
        if provider_name == 'deepseek':
            return _call_deepseek_api(messages, api_key, api_url, model_name, enable_tools=enable_tools)
        elif provider_name == 'gemini':
            return _call_gemini_api_with_context(messages, api_key, model_name, conversation_id, files, is_one_time_attachment, enable_tools=enable_tools)
        else:
            # Default to OpenAI-compatible format
            return _call_openai_compatible_api(messages, api_key, api_url, model_name, enable_tools=enable_tools)
            
    except requests.exceptions.Timeout:
        return f"Error: {provider_name} API request timed out after 120 seconds."
    except Exception as e:
        return f"Error calling {provider_name} API: {str(e)}"


def _call_deepseek_api(messages, api_key, api_url, model_name, enable_tools=True, max_iterations=5):
    """
    Call DeepSeek API (OpenAI-compatible format) with Function Calling support.
    支持多轮工具调用迭代，直到 AI 给出最终答案。
    
    Args:
        messages: 消息列表
        api_key: API密钥
        api_url: API地址
        model_name: 模型名称
        enable_tools: 是否启用工具调用
        max_iterations: 最大工具调用迭代次数（防止无限循环）
    
    Returns:
        str: AI回复文本
    """
    try:
        # 准备基础 payload
        payload = {
            "messages": messages.copy()  # 使用副本避免修改原始消息
        }
        if model_name:
            payload["model"] = model_name

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 如果启用工具且工具执行器可用，添加工具定义和引导提示
        tool_schemas = None
        if enable_tools and TOOL_EXECUTOR_AVAILABLE:
            try:
                tool_schemas = get_all_tool_schemas()
                if tool_schemas:
                    payload["tools"] = tool_schemas
                    print(f"[DeepSeek] 📦 已添加 {len(tool_schemas)} 个工具")
                    
                    # 🔧 在系统消息中添加工具使用引导
                    if not any(msg.get('role') == 'system' for msg in payload["messages"]):
                        payload["messages"].insert(0, {
                            "role": "system",
                            "content": (
                                "你是一个智能助手，拥有搜索工具。\n"
                                "重要规则：\n"
                                "1. 当用户询问你不了解的信息（如实时新闻、天气、股票等）时，必须主动调用搜索工具\n"
                                "2. 如果第一次搜索结果不准确，继续调用工具直到获得正确信息\n"
                                "3. 只有在确认获得准确答案后才回复用户\n"
                                "4. 优先使用工具而非猜测或使用过时信息"
                            )
                        })
            except Exception as e:
                print(f"[DeepSeek] ⚠️ 工具Schema获取失败: {e}")
        
        # 🔧 多轮工具调用循环
        iteration = 0
        conversation_messages = payload["messages"].copy()
        
        while iteration < max_iterations:
            iteration += 1
            print(f"[DeepSeek] 📤 第 {iteration} 轮 API 调用...")
            
            # 更新 payload 消息
            payload["messages"] = conversation_messages
            
            # API 调用
            response = requests.post(api_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            message = data['choices'][0]['message']
            
            # 检查是否有工具调用
            if 'tool_calls' in message and message['tool_calls'] and TOOL_EXECUTOR_AVAILABLE:
                print(f"[DeepSeek] 🔧 第 {iteration} 轮检测到 {len(message['tool_calls'])} 个工具调用")
                
                # 执行工具调用
                tool_executor = get_tool_executor()
                tool_results = tool_executor.execute_tool_calls(message['tool_calls'])
                
                # 添加助手的工具调用消息
                conversation_messages.append({
                    "role": "assistant",
                    "content": message.get('content', ''),
                    "tool_calls": message['tool_calls']
                })
                
                # 添加工具执行结果
                for tool_result in tool_results:
                    if tool_result['success']:
                        conversation_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_result.get('tool_call_id', ''),
                            "name": tool_result['tool_name'],
                            "content": tool_result['result_json']
                        })
                    else:
                        conversation_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_result.get('tool_call_id', ''),
                            "name": tool_result.get('tool_name', 'unknown'),
                            "content": json.dumps({"error": tool_result['error']}, ensure_ascii=False)
                        })
                
                # 继续下一轮迭代（AI 会基于工具结果决定是否继续调用工具）
                print(f"[DeepSeek] 🔄 工具执行完成，等待 AI 下一步决策...")
                continue
            
            # 没有工具调用，返回最终结果
            final_content = message.get('content', '')
            if iteration > 1:
                print(f"[DeepSeek] ✅ 经过 {iteration} 轮迭代，获得最终答案")
            return final_content
        
        # 达到最大迭代次数
        print(f"[DeepSeek] ⚠️ 达到最大迭代次数 ({max_iterations})，返回当前结果")
        return message.get('content', '') if message else "抱歉，处理超时，请重试。"
        
    except requests.exceptions.Timeout:
        print(f"[DeepSeek] ❌ 请求超时")
        return "Error: API 请求超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        print(f"[DeepSeek] ❌ 网络请求失败: {e}")
        return f"Error: 网络请求失败 - {str(e)}"
    except KeyError as e:
        print(f"[DeepSeek] ❌ API 响应格式错误: {e}")
        return f"Error: API 响应格式异常 - {str(e)}"
    except Exception as e:
        print(f"[DeepSeek] ❌ 未知错误: {e}")
        return f"Error: 处理失败 - {str(e)}"


def _apply_proxy_policy(provider_name: str) -> None:
    """Enable or disable proxy based on provider selection."""
    if provider_name == 'gemini':
        enable_proxy()
    else:
        disable_proxy()


def _convert_openai_tools_to_gemini(openai_tools: list):
    """
    将 OpenAI 格式的工具 Schema 转换为 Gemini 格式
    
    OpenAI 格式示例：
    {
        "type": "function",
        "function": {
            "name": "baidu_search",
            "description": "...",
            "parameters": {...}
        }
    }
    
    Gemini 格式：使用 google.genai.types.Tool
    
    Args:
        openai_tools: OpenAI 格式的工具列表
    
    Returns:
        types.Tool 对象或 None
    """
    if not openai_tools or not GENAI_AVAILABLE:
        return None
    
    try:
        from google.genai import types
        
        function_declarations = []
        
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                function_declarations.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {})
                })
        
        if function_declarations:
            # 使用 types.Tool 包装 function_declarations
            gemini_tool = types.Tool(function_declarations=function_declarations)
            print(f"[Gemini] ✅ 成功转换 {len(function_declarations)} 个工具")
            return gemini_tool
        
        return None
        
    except Exception as e:
        print(f"[Gemini] ❌ 工具转换失败: {e}")
        return None


def _extract_function_calls_from_response(response):
    """
    从 Gemini Response 对象中提取 function_call 信息
    
    根据 Gemini 官方文档，function_call 位于：
    response.candidates[0].content.parts[i].function_call
    
    Args:
        response: Gemini API response 对象
    
    Returns:
        list: function_call 列表，每个元素为 {"name": ..., "args": {...}}
    """
    function_calls = []
    
    try:
        if not response or not hasattr(response, 'candidates'):
            return []
        
        for candidate in response.candidates:
            if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts'):
                continue
            
            for part in candidate.content.parts:
                if hasattr(part, 'function_call'):
                    fc = part.function_call
                    function_calls.append({
                        'name': fc.name,
                        'args': dict(fc.args) if hasattr(fc, 'args') else {}
                    })
        
    except Exception as e:
        print(f"[Gemini] ⚠️ 提取 function_call 失败: {e}")
    
    return function_calls


def _call_gemini_api_with_context(messages, api_key, model_name, conversation_id=None, files=None, is_one_time_attachment=None, enable_tools=True):
    """
    Call Google Gemini API with context management (Chat Session).
    支持上下文记忆和文件上传的 Gemini API 调用。
    支持 Function Calling 工具调用。
    
    核心逻辑：
    1. 检查并恢复 Chat Session 历史（如果未初始化）
    2. Chat Session 内部自动维护历史记录
    3. 只需发送最后一条用户消息
    4. 支持两种文件模式：临时（内嵌）和持久（File API）
    5. 历史同步由 Chat Session 管理，无需手动处理
    6. 支持 Function Calling（如果启用）
    
    Args:
        messages: 消息列表（OpenAI格式，用于历史恢复和提取最新消息）
        api_key: API 密钥（从环境变量获取）
        model_name: 模型名称
        conversation_id: 对话ID，用于管理上下文
        files: 文件信息（字典列表或路径列表）
        is_one_time_attachment: 文件模式标记（仅在 files 为路径列表时使用）
        enable_tools: 是否启用工具调用
    """
    if not GENAI_AVAILABLE:
        return "Error: Google GenAI SDK is not installed. Please run 'pip install google-generativeai'"
    
    # 检查是否启用上下文管理
    if not GEMINI_CONTEXT_AVAILABLE or not conversation_id:
        # 降级到无上下文模式
        print("⚠️ 使用无上下文模式（未提供 conversation_id 或上下文管理器不可用）")
        return _call_gemini_api_with_sdk(messages, api_key, model_name)
    
    try:
        # 获取上下文管理器
        context_manager = get_gemini_context_manager()
        if not context_manager:
            print("⚠️ 上下文管理器初始化失败，降级到无上下文模式")
            return _call_gemini_api_with_sdk(messages, api_key, model_name)
        
        # 检查系统环境变量 GEMINI_API_KEY
        env_api_key = os.getenv('GEMINI_API_KEY')
        if not env_api_key:
            return "Error: GEMINI_API_KEY 环境变量未设置。请在系统中设置 GEMINI_API_KEY 环境变量。"
        
        # 确保模型名称有效
        model_to_use = model_name if model_name else 'gemini-2.5-flash'
        print(f"🤖 使用模型: {model_to_use} (启用上下文)")
        
        # 【核心修正】在发送消息前，检查并恢复历史
        # 只有当上下文管理器中不存在此会话时才需要恢复
        if not context_manager.get_chat_session(conversation_id):
            print(f"🔍 会话 {conversation_id} 不存在，尝试从历史恢复...")
            # 如果 messages 包含多条历史记录（不只是当前消息），则需要恢复
            if len(messages) > 1:
                # 排除最后一条消息（这是当前要发送的）
                history_to_restore = messages[:-1]
                if history_to_restore:
                    print(f"📚 恢复 {len(history_to_restore)} 条历史记录...")
                    try:
                        context_manager.restore_chat_history(
                            conversation_id=conversation_id,
                            messages=history_to_restore,
                            model=model_to_use
                        )
                    except Exception as e:
                        print(f"⚠️ 历史恢复失败: {str(e)}")
                        # 继续执行，创建新的 Chat Session
            else:
                print(f"📝 这是新对话的第一条消息")
        else:
            print(f"✅ 使用现有的 Chat Session")
        
        # 【核心】提取最后一条用户消息（这是本次请求的唯一新增内容）
        # Chat Session 会自动将其与内部历史合并
        last_user_message = None
        for msg in reversed(messages):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break
        
        if not last_user_message:
            return "Error: No user message found."
        
        # 获取并转换工具 Schema（如果启用）
        gemini_tools = None
        if enable_tools and TOOL_EXECUTOR_AVAILABLE:
            try:
                openai_tools = get_all_tool_schemas()
                if openai_tools:
                    gemini_tools = _convert_openai_tools_to_gemini(openai_tools)
                    print(f"[Gemini] 🔧 已准备 {len(openai_tools)} 个工具（Gemini格式）")
            except Exception as e:
                print(f"[Gemini] ⚠️ 工具准备失败: {e}")
        
        # 判断是否有文件
        if files and len(files) > 0:
            # 【带文件】发送消息
            # 文件现在是字典列表，包含 path, mode, file_id
            print(f"📤 发送消息到 Chat Session（含 {len(files)} 个文件）")
            
            # 分离临时文件和持久文件
            temporary_files = [f['path'] for f in files if f.get('mode') == 'temporary']
            persistent_file_ids = [f['file_id'] for f in files if f.get('mode') == 'persistent' and f.get('file_id')]
            
            print(f"� 临时文件: {len(temporary_files)} 个")
            print(f"🔗 持久文件: {len(persistent_file_ids)} 个")
            
            for f in files:
                mode_icon = '📄' if f.get('mode') == 'temporary' else '🔗'
                print(f"  {mode_icon} {f['path']} (mode={f.get('mode')})")
            
            response = context_manager.send_message_with_files(
                conversation_id=conversation_id,
                message=last_user_message,
                file_paths=temporary_files,  # 临时文件路径
                persistent_file_ids=persistent_file_ids,  # 持久文件ID
                model=model_to_use,
                tools=gemini_tools  # 传递工具
            )
        else:
            # 【纯文本】发送消息
            # GeminiContextManager.send_message() 内部会：
            # 1. 获取或创建对应的 Chat Session
            # 2. 将消息添加到内部历史
            # 3. 发送 [内部历史 + 本次消息] 给模型
            # 4. 将模型回复也添加到内部历史
            print(f"📤 发送消息到 Chat Session: {last_user_message[:50]}...")
            response = context_manager.send_text_message(
                conversation_id=conversation_id,
                message=last_user_message,
                model=model_to_use,
                tools=gemini_tools  # 传递工具
            )
        
        # 检查 response 类型
        if isinstance(response, str):
            # 如果是字符串，说明是错误消息
            if response.startswith("Error:"):
                raise Exception(response)
            return response
        
        # 检查是否有 function_call（根据 Gemini 官方文档）
        # response.candidates[0].content.parts 中可能包含 function_call
        chat = context_manager.get_chat_session(conversation_id)
        function_calls = _extract_function_calls_from_response(response)
        
        if function_calls and TOOL_EXECUTOR_AVAILABLE:
            print(f"[Gemini] 🔧 检测到 {len(function_calls)} 个工具调用")
            from tool_executor import execute_tool
            from google.genai import types
            
            # 执行所有工具调用并构造 function_response
            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.get('name')
                tool_args = fc.get('args', {})
                print(f"[Gemini] 📞 调用工具: {tool_name}，参数: {tool_args}")
                result = execute_tool(tool_name, tool_args)
                print(f"[Gemini] ✅ 工具 {tool_name} 返回: {str(result)[:100]}...")
                
                # 根据 Gemini 官方文档，使用 Part 包装 FunctionResponse
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={'result': result}
                    )
                )
            
            # 发送 function_response 到 Chat Session
            # 根据 Gemini SDK，send_message 接受多个 Part 作为独立参数，而不是列表
            print(f"[Gemini] 📤 发送工具结果到模型...")
            final_response = chat.send_message(*function_response_parts)
            
            # 提取最终文本回复
            response_text = context_manager._extract_text_from_response(final_response)
            print(f"✅ 收到最终回复: {response_text[:50] if response_text else 'Empty'}...")
            return response_text
        else:
            # 没有 function_call，直接提取文本
            response_text = context_manager._extract_text_from_response(response)
            print(f"✅ 收到回复: {response_text[:50] if response_text else 'Empty'}...")
            return response_text
        
    except Exception as e:
        print(f"❌ Gemini 上下文 API 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        # 降级到无上下文模式
        print("⚠️ 降级到无上下文模式")
        return _call_gemini_api_with_sdk(messages, api_key, model_name)


def _call_gemini_api_with_sdk(messages, api_key, model_name):
    """Call Google Gemini API using the official Google GenAI SDK with Client() (无上下文模式)."""
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


def _call_gemini_api(messages, api_key, api_url, model_name, enable_tools=True):
    """
    Call Google Gemini API (fallback REST API method).
    
    Args:
        messages: List of message dicts
        api_key: API key for Gemini
        api_url: Base URL for Gemini API
        model_name: Model identifier
        enable_tools: Whether to enable function calling tools (default: True)
    
    Returns:
        str: The AI response text
    """
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
    
    # Add tools if enabled and available
    if enable_tools and TOOL_EXECUTOR_AVAILABLE:
        tools_schemas = get_all_tool_schemas()
        # Convert OpenAI format to Gemini format
        gemini_tools = []
        for tool_schema in tools_schemas:
            if tool_schema.get('type') == 'function':
                func = tool_schema['function']
                gemini_tools.append({
                    "function_declarations": [{
                        "name": func['name'],
                        "description": func['description'],
                        "parameters": func['parameters']
                    }]
                })
        if gemini_tools:
            payload["tools"] = gemini_tools
    
    # Build the URL with model and API key
    full_url = f"{api_url}/{model_name}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # First API call
    response = requests.post(full_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    
    if 'candidates' in data and len(data['candidates']) > 0:
        candidate = data['candidates'][0]
        if 'content' in candidate:
            content = candidate['content']
            
            # Check if there are function calls
            if 'parts' in content:
                parts = content['parts']
                # Check if any part contains function call
                has_function_call = any('functionCall' in part for part in parts)
                
                if has_function_call and enable_tools and TOOL_EXECUTOR_AVAILABLE:
                    # Extract function calls and execute them
                    tool_executor = get_tool_executor()
                    function_responses = []
                    
                    for part in parts:
                        if 'functionCall' in part:
                            func_call = part['functionCall']
                            tool_name = func_call.get('name', '')
                            tool_args = func_call.get('args', {})
                            
                            # Execute the tool
                            result = tool_executor.execute_tool(tool_name, tool_args)
                            
                            if result['success']:
                                function_responses.append({
                                    "functionResponse": {
                                        "name": tool_name,
                                        "response": {
                                            "content": result['result_json']
                                        }
                                    }
                                })
                            else:
                                function_responses.append({
                                    "functionResponse": {
                                        "name": tool_name,
                                        "response": {
                                            "error": result.get('error', 'Unknown error')
                                        }
                                    }
                                })
                    
                    if function_responses:
                        # Add assistant's function call and function responses to conversation
                        gemini_messages.append({
                            "role": "model",
                            "parts": parts
                        })
                        
                        gemini_messages.append({
                            "role": "function",
                            "parts": function_responses
                        })
                        
                        # Second API call with function results
                        payload["contents"] = gemini_messages
                        # Remove tools from second call as per Gemini best practices
                        if "tools" in payload:
                            del payload["tools"]
                        
                        response = requests.post(full_url, json=payload, headers=headers, timeout=120)
                        response.raise_for_status()
                        data = response.json()
                        
                        if 'candidates' in data and len(data['candidates']) > 0:
                            candidate = data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                # Get final text response
                                final_parts = candidate['content']['parts']
                                text_parts = [p['text'] for p in final_parts if 'text' in p]
                                if text_parts:
                                    return ' '.join(text_parts)
                        
                        return "Error: No valid response after tool execution."
                
                # No function call, return text response
                text_parts = [p['text'] for p in parts if 'text' in p]
                if text_parts:
                    return ' '.join(text_parts)
    
    return "Error: Invalid response format from Gemini API."


def _call_openai_compatible_api(messages, api_key, api_url, model_name, enable_tools=True):
    """
    Call OpenAI-compatible API (fallback for other providers).
    
    Args:
        messages: List of message dicts
        api_key: API key for authentication
        api_url: Base URL for the API endpoint
        model_name: Model identifier
        enable_tools: Whether to enable function calling tools (default: True)
    
    Returns:
        str: The AI response text
    """
    payload = {
        "messages": messages
    }
    if model_name:
        payload["model"] = model_name
    
    # Add tools if enabled and available
    if enable_tools and TOOL_EXECUTOR_AVAILABLE:
        tools_schemas = get_all_tool_schemas()
        if tools_schemas:
            payload["tools"] = tools_schemas
            payload["tool_choice"] = "auto"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # First API call
    response = requests.post(api_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    
    message = data['choices'][0]['message']
    
    # Check if there are tool calls
    if 'tool_calls' in message and message['tool_calls'] and enable_tools and TOOL_EXECUTOR_AVAILABLE:
        # Execute all tool calls
        tool_executor = get_tool_executor()
        tool_results = tool_executor.execute_tool_calls(message['tool_calls'])
        
        # Build messages with tool results
        messages_with_tools = messages.copy()
        
        # Add assistant message with tool calls
        messages_with_tools.append({
            "role": "assistant",
            "content": message.get('content') or '',
            "tool_calls": message['tool_calls']
        })
        
        # Add tool results
        for result in tool_results:
            messages_with_tools.append({
                "role": "tool",
                "content": result['result_json'],
                "tool_call_id": result['tool_call_id']
            })
        
        # Second API call with tool results
        payload["messages"] = messages_with_tools
        # Remove tool_choice for second call
        if "tool_choice" in payload:
            del payload["tool_choice"]
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        return data['choices'][0]['message']['content']
    
    # No tool calls, return content directly
    return message.get('content', '')


# Keep the old function name for backward compatibility
def get_deepseek_reply(messages):
    """Backward compatibility function."""
    return get_ai_reply(messages)

def get_topic_from_reply(ai_response):
    """
    通过一个特殊的API请求，从AI回复内容中提取一个简短的对话主题。
    特别适用于包含图片分析、文档分析等AI生成内容的情况。
    """
    messages = [
        {"role": "system", "content": "你是标题生成助手。根据AI回复内容生成3个标题，每个5字以内，用逗号分隔。示例格式：视频分析,内容解读,多媒体讨论。只返回标题，不要理由、不要换行、不要序号、不要其他任何内容。"},
        {"role": "user", "content": f"AI回复内容：{ai_response[:200]}"}  # 只取前200字避免过长
    ]
    
    try:
        reply = get_ai_reply(messages)
        # 清理返回内容
        clean_reply = reply.strip().replace('\n', ' ').replace('\r', '')
        
        # 解析标题（按逗号或顿号分隔）
        titles = []
        for separator in [',', '，', '、']:
            if separator in clean_reply:
                titles = [t.strip() for t in clean_reply.split(separator)]
                break
        
        # 如果没有分隔符，直接使用整个回复
        if not titles:
            titles = [clean_reply]
        
        # 过滤和清理标题
        valid_titles = []
        for t in titles:
            # 移除序号、标点、引号等
            t = t.replace('"', '').replace("'", '').replace("。", '').replace('*', '')
            t = t.replace('**', '').replace('《', '').replace('》', '')
            # 移除数字序号
            import re
            t = re.sub(r'^\d+[\.\、]?\s*', '', t)
            t = t.strip()
            
            # 只保留5个字以内的标题
            if t and len(t) <= 5:
                valid_titles.append(t)
        
        if valid_titles:
            # 随机选择一个标题
            import random
            selected_title = random.choice(valid_titles)
            print(f"[OK] 对话标题: {selected_title}")
            return selected_title
        else:
            # 如果没有有效标题，从AI回复中提取关键词
            words = ai_response[:20].split()
            fallback = words[0] if words else "新对话"
            print(f"[OK] 对话标题: {fallback}")
            return fallback[:5]  # 最多5个字
            
    except Exception as e:
        print(f"[ERROR] 获取对话主题失败: {e}")
        return "新对话"