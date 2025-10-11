"""
Gemini 上下文管理器
实现 Chat Session 和文件上下文管理，为 Gemini 模型提供连贯的多轮对话能力
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# 导入 Base64 和 MIME 类型处理库（用于文件处理）
import mimetypes

# 导入密钥获取函数
from api_config import get_gemini_api_key

# 检查 Google GenAI SDK 是否可用
GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai.types import Content, Part
    GENAI_AVAILABLE = True
    print("[OK] Gemini Context Manager: Google GenAI SDK loaded")
except ImportError:
    print("[ERROR] Gemini Context Manager: Google GenAI SDK not installed")
    GENAI_AVAILABLE = False

# --- 允许的文件MIME类型定义 ---
# 视频文件MIME类型（必须走 File API）
VIDEO_MIME_TYPES = [
    'video/mp4',
    'video/mov', 
    'video/mpeg',
    'video/avi',
    'video/quicktime',
    'video/x-msvideo',
    'video/webm'
]

# 图像文件MIME类型（小文件走内嵌，大文件走 File API）
IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/heic',
    'image/heif',
]

# PDF文件MIME类型（小文件走内嵌，大文件走 File API）
PDF_MIME_TYPE = 'application/pdf'

# 所有允许的MIME类型（仅支持图片、PDF、视频）
ALLOWED_MIME_TYPES = IMAGE_MIME_TYPES + [PDF_MIME_TYPE] + VIDEO_MIME_TYPES


class GeminiContextManager:
    """
    Gemini 上下文管理器
    
    功能：
    1. 管理 Chat Session（聊天会话），实现上下文记忆
    2. 管理文件引用，支持多模态上下文
    3. 支持系统指令设置
    4. 自动处理会话历史
    """
    
    def __init__(self, api_key: str):
        """
        初始化上下文管理器
        
        Args:
            api_key: Gemini API 密钥
        """
        if not GENAI_AVAILABLE:
            raise ImportError("Google GenAI SDK 未安装，无法使用上下文管理器")
        
        if not api_key:
            raise ValueError("api_key 参数不能为空")
        
        # 【核心修复】临时移除代理环境变量，避免与 gRPC 认证冲突
        # 保存原始代理设置
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        saved_proxies = {}
        
        for var in proxy_vars:
            if var in os.environ:
                saved_proxies[var] = os.environ.pop(var)
                print(f"🔧 临时移除代理变量: {var}")
        
        try:
            # 在无代理环境下创建客户端（避免 gRPC 认证问题）
            self.client = genai.Client(api_key=api_key)
            print("[OK] Gemini client created successfully (proxy isolated)")
        finally:
            # 恢复代理环境变量，确保其他模块（如 requests）能继续使用代理
            for var, value in saved_proxies.items():
                os.environ[var] = value
                print(f"🔄 恢复代理变量: {var}")
        
        # 会话管理：conversation_id -> chat_session
        self.chat_sessions: Dict[str, Any] = {}
        
        # 文件管理：file_id -> file_reference
        self.uploaded_files: Dict[str, Any] = {}
        
        # 系统指令（可选）
        self.system_instruction: Optional[str] = None
        
        print("[OK] Gemini Context Manager initialized successfully")
    
    def set_system_instruction(self, instruction: str):
        """
        设置系统指令（全局）
        
        Args:
            instruction: 系统指令内容，用于定义模型的行为、角色和语气
        """
        self.system_instruction = instruction
        print(f"📋 系统指令已设置: {instruction[:50]}...")
    
    def create_chat_session(self, conversation_id: str, model: str = "gemini-2.5-flash"):
        """
        为指定对话创建 Chat Session
        
        Args:
            conversation_id: 对话ID
            model: 使用的模型名称
        """
        if conversation_id in self.chat_sessions:
            print(f"[WARNING] Chat Session already exists for conversation {conversation_id}")
            return
        
        # 准备配置
        config = {}
        if self.system_instruction:
            config["system_instruction"] = self.system_instruction
        
        # 创建 Chat Session
        try:
            if config:
                chat = self.client.chats.create(model=model, config=config)
            else:
                chat = self.client.chats.create(model=model)
            
            self.chat_sessions[conversation_id] = {
                'chat': chat,
                'model': model,
                'created_at': datetime.now()
            }
            print(f"[OK] Chat Session created for conversation {conversation_id} (model: {model})")
        except Exception as e:
            print(f"[ERROR] Failed to create Chat Session: {str(e)}")
            raise
    
    def get_chat_session(self, conversation_id: str):
        """
        获取指定对话的 Chat Session
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Chat Session 对象，如果不存在则返回 None
        """
        session_info = self.chat_sessions.get(conversation_id)
        if session_info:
            return session_info['chat']
        return None
    
    def send_message(self, conversation_id: str, message: str, model: str = "gemini-2.5-flash") -> str:
        """
        在指定对话中发送消息（自动管理上下文）
        
        Args:
            conversation_id: 对话ID
            message: 用户消息内容
            model: 使用的模型名称
            
        Returns:
            模型的回复文本
        """
        # 确保 Chat Session 存在
        if conversation_id not in self.chat_sessions:
            self.create_chat_session(conversation_id, model)
        
        chat = self.get_chat_session(conversation_id)
        if not chat:
            raise ValueError(f"无法获取对话 {conversation_id} 的 Chat Session")
        
        try:
            print(f"📤 发送消息到对话 {conversation_id}: {message[:50]}...")
            
            # 发送消息（SDK 会自动管理历史记录）
            response = chat.send_message(message)
            
            if response and response.text:
                print(f"[OK] 收到回复: {response.text[:50]}...")
                return response.text
            else:
                return "Error: Empty response from Gemini."
        
        except Exception as e:
            print(f"[ERROR] 发送消息失败: {str(e)}")
            return f"Error: {str(e)}"
    
    ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif', '.mp4', '.mov', '.mpeg', '.avi', '.webm'}

    def send_message_with_files(self, conversation_id: str, message: str, 
                                file_paths: List[str] = None, 
                                persistent_file_ids: List[str] = None,
                                model: str = "gemini-2.5-flash") -> str:
        """
        发送包含文件的消息（多模态上下文）- 支持临时和持久两种模式
        
        文件上传策略：
        - 临时文件 (file_paths): 使用 Part.from_bytes 内嵌上传（<20MB），发送后自动删除
        - 持久文件 (persistent_file_ids): 使用已上传的 File API 引用，保留在服务器上
        
        Args:
            conversation_id: 对话ID
            message: 用户消息内容
            file_paths: 临时文件路径列表（内嵌上传）
            persistent_file_ids: 持久文件ID列表（File API引用）
            model: 使用的模型名称
            
        Returns:
            模型的回复文本
        """
        # 确保 Chat Session 存在
        if conversation_id not in self.chat_sessions:
            self.create_chat_session(conversation_id, model)
        
        chat = self.get_chat_session(conversation_id)
        if not chat:
            raise ValueError(f"无法获取对话 {conversation_id} 的 Chat Session")
        
        try:
            content_parts = []
            
            # 定义文件大小阈值
            MAX_INLINE_SIZE = 20 * 1024 * 1024  # 20 MB
            MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
            
            # 1. 处理临时文件：根据类型和大小选择上传方式
            if file_paths:
                for file_path in file_paths:
                    if not os.path.exists(file_path):
                        print(f"[WARNING] 文件不存在: {file_path}")
                        continue

                    file_ext = os.path.splitext(file_path)[1].lower()
                    if file_ext not in self.ALLOWED_EXTENSIONS:
                        print(f"[WARNING] 不支持的文件扩展名: {file_path}")
                        continue

                    file_size = os.path.getsize(file_path)
                    file_name = os.path.basename(file_path)
                    mime_type = self._get_mime_type(file_path)

                    # --- 【核心过滤】只允许图片、PDF、视频 ---
                    if mime_type not in ALLOWED_MIME_TYPES:
                        print(f"[ERROR] 文件类型不受支持，跳过: {file_name} (MIME: {mime_type})")
                        continue

                    # 检查文件大小硬限制
                    if file_size > MAX_FILE_SIZE:
                        print(f"[ERROR] 文件过大（> 2GB），无法上传: {file_name}")
                        continue

                    # 判断是否为视频文件
                    is_video = mime_type in VIDEO_MIME_TYPES
                    is_large_file = file_size >= MAX_INLINE_SIZE

                    # --- 视频/大文件（>= 20MB）使用 File API ---
                    if is_video or is_large_file:
                        file_type_desc = "视频文件" if is_video else "大文件"
                        print(f"[FILE] {file_type_desc}使用 File API: {file_name} ({file_size / (1024*1024):.2f} MB)")
                        try:
                            uploaded_file = self._upload_file_to_gemini(file_path, mime_type)
                            content_parts.append(uploaded_file)
                            print(f"  → File API 上传成功 (文件将在服务器保留48小时)")
                            
                        except Exception as upload_error:
                            print(f"[ERROR] File API 上传失败: {file_path}, 错误: {upload_error}")
                        continue

                    # --- 小文件（图片/PDF, < 20MB）内嵌上传 ---
                    print(f"�️ 内嵌上传小文件: {file_name} (MIME: {mime_type}, {file_size / (1024*1024):.2f} MB)")

                    try:
                        # 使用 Part.from_bytes 内嵌上传
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        inline_part = Part.from_bytes(data=file_data, mime_type=mime_type)
                        content_parts.append(inline_part)
                        print(f"  → 内嵌上传成功 (MIME: {mime_type})")
                        
                    except Exception as upload_error:
                        print(f"[ERROR] 内嵌上传失败: {file_path}, 错误: {upload_error}")
            
            # 2. 处理持久文件：使用 File API 引用
            if persistent_file_ids:
                for file_id in persistent_file_ids:
                    try:
                        # 检查文件是否在缓存中
                        if file_id in self.uploaded_files:
                            uploaded_file = self.uploaded_files[file_id]['file']
                            content_parts.append(uploaded_file)
                            print(f"[LINK] 引用持久文件: {file_id} (已缓存)")
                        else:
                            # 尝试使用 Part.from_uri 引用文件
                            file_uri = f"https://generativelanguage.googleapis.com/v1beta/{file_id}"
                            persistent_part = Part.from_uri(file_uri)
                            content_parts.append(persistent_part)
                            print(f"[LINK] 引用持久文件: {file_id} (URI)")
                            
                    except Exception as ref_error:
                        print(f"[ERROR] 引用持久文件失败: {file_id}, 错误: {ref_error}")
            
            # 【核心修复】文本消息必须转换为 Part 对象
            # 即使没有文件，也要使用 Part 结构发送
            text_part = Part(text=message)
            
            if not content_parts:
                print("[WARNING] 没有成功处理任何文件，但仍使用 Part 结构发送文本")
                contents = [text_part]
            else:
                # 构建完整的内容（文件 + 文本提示）
                # 注意：根据官方文档，图片应在前，文本在后
                contents = content_parts + [text_part]
            
            print(f"📤 发送消息（含 {len(content_parts)} 个文件）到对话 {conversation_id}")
            print(f"📝 内容顺序: [{len(content_parts)} 个文件 Part] + [1 个文本 Part]")
            
            # 发送消息（将 contents 列表作为单个参数传递，符合新版 SDK 要求）
            response = chat.send_message(contents)
            
            if response and response.text:
                print(f"[OK] 收到回复: {response.text[:50]}...")
                
                return response.text
            else:
                error_msg = "Empty response from Gemini."
                
                return f"Error: {error_msg}"
        
        except Exception as e:
            print(f"[ERROR] 发送包含文件的消息失败: {str(e)}")
            import traceback
            traceback.print_exc()
           
            return f"Error: {str(e)}"

    def _upload_file_to_gemini(self, file_path: str, mime_type: str):
        """使用 Gemini File API 上传文件，并缓存返回的文件引用。"""
        import time
        
        # 使用与 Chat Session 同源的客户端上传文件，以便返回 google.genai.types.File 实例
        # 注意：新 SDK 只支持 file 参数，不支持 display_name 和 mime_type
        uploaded_file = self.client.files.upload(file=file_path)
        
        file_id = uploaded_file.name if hasattr(uploaded_file, 'name') else str(len(self.uploaded_files))
        print(f"  → 文件已上传至 Gemini，ID: {file_id}")
        print(f"     初始状态: {uploaded_file.state}")
        
        # 对于视频文件，需要等待处理完成
        if mime_type in VIDEO_MIME_TYPES:
            print(f"  → 视频文件需要处理，等待 ACTIVE 状态...")
            max_wait = 120  # 最多等待2分钟
            waited = 0
            
            while uploaded_file.state.name == "PROCESSING" and waited < max_wait:
                time.sleep(3)
                waited += 3
                uploaded_file = self.client.files.get(name=file_id)
                if waited % 9 == 0:  # 每9秒打印一次
                    print(f"     处理中... ({waited}秒)")
            
            if uploaded_file.state.name == "ACTIVE":
                print(f"  → 视频处理完成，状态: {uploaded_file.state}")
            elif uploaded_file.state.name == "FAILED":
                print(f"  [ERROR] 视频处理失败: {uploaded_file.state}")
                raise Exception(f"视频处理失败: {file_id}")
            elif uploaded_file.state.name == "PROCESSING":
                print(f"  [WARNING] 视频仍在处理中（已等待{waited}秒），尝试继续...")
        
        # 缓存文件引用
        self.uploaded_files[file_id] = {
            'file': uploaded_file,
            'path': file_path,
            'uploaded_at': datetime.now()
        }
        
        return uploaded_file
    
    def _get_mime_type(self, file_path: str) -> str:
        """
        获取文件的 MIME 类型，对常见类型进行补充以提高准确性
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME 类型字符串
        """
        import mimetypes
        
        # 1. 使用 mimetypes 库进行猜测
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type
        
        # 2. 针对常见扩展名进行手动检查
        ext = os.path.splitext(file_path)[1].lower()
        
        # 视频文件
        if ext in ['.mp4', '.mov', '.mpeg', '.avi', '.webm']:
            video_mime_map = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.mpeg': 'video/mpeg',
                '.avi': 'video/x-msvideo',
                '.webm': 'video/webm'
            }
            return video_mime_map.get(ext, f'video/{ext[1:]}')
        
        # PDF文件
        if ext == '.pdf':
            return 'application/pdf'
        
        # 图片文件
        if ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        if ext == '.png':
            return 'image/png'
        if ext == '.webp':
            return 'image/webp'
        if ext == '.heic':
            return 'image/heic'
        if ext == '.heif':
            return 'image/heif'
        if ext == '.gif':
            return 'image/gif'
        
        # 3. 默认返回通用类型（如果不在允许列表内，后续会被过滤）
        return 'application/octet-stream'
    
    def get_chat_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        获取指定对话的历史记录（包含文件引用信息）
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            历史记录列表，格式为 [{'role': 'user', 'content': '...', 'files': [...]}, ...]
        """
        session_info = self.chat_sessions.get(conversation_id)
        if not session_info:
            print(f"[WARNING] 对话 {conversation_id} 的 Chat Session 不存在")
            return []
        
        chat = session_info['chat']
        if not chat:
            return []
        
        try:
            # 使用 get_history() 方法获取历史记录
            if not hasattr(chat, 'get_history'):
                print(f"[WARNING] Chat Session 没有 get_history 方法")
                return []
            
            chat_history = chat.get_history()
            print(f"📚 Chat Session 历史记录数量: {len(chat_history) if chat_history else 0}")
            
            if not chat_history:
                print(f"[WARNING] Chat Session 历史记录为空")
                return []
            
            history_data = []
            for item in chat_history:
                role = 'user' if item.role == 'user' else 'assistant'
                content = ''
                files_in_history = []
                
                if hasattr(item, 'parts'):
                    for part in item.parts:
                        # 1. 提取文本内容
                        if hasattr(part, 'text') and part.text:
                            content += part.text
                        
                        # 2. 提取文件引用信息 (File API 引用)
                        if hasattr(part, 'file_data') and part.file_data:
                            file_uri = part.file_data.file_uri
                            mime_type = getattr(part.file_data, 'mime_type', 'application/octet-stream')
                            files_in_history.append({
                                'type': 'file_ref',
                                'uri': file_uri,
                                'mime_type': mime_type
                            })
                            print(f"  📎 历史中发现文件引用: {file_uri}")
                        
                        # 3. 提取内嵌数据引用 (Inline Data)
                        if hasattr(part, 'inline_data') and part.inline_data:
                            mime_type = getattr(part.inline_data, 'mime_type', 'application/octet-stream')
                            # 内嵌数据较大，不存储完整数据，只标记存在
                            files_in_history.append({
                                'type': 'inline_data',
                                'mime_type': mime_type,
                                'note': '内嵌数据（无法恢复）'
                            })
                            print(f"  📎 历史中发现内嵌数据: {mime_type}")
                
                history_item = {'role': role, 'content': content}
                if files_in_history:
                    history_item['files'] = files_in_history
                
                history_data.append(history_item)
            
            print(f"[OK] 成功提取 {len(history_data)} 条历史记录")
            return history_data
            
        except Exception as e:
            print(f"[WARNING] 获取历史记录失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def clear_chat_session(self, conversation_id: str):
        """
        清除指定对话的 Chat Session（会丢失上下文）
        
        Args:
            conversation_id: 对话ID
        """
        if conversation_id in self.chat_sessions:
            del self.chat_sessions[conversation_id]
            print(f"🗑️ 已清除对话 {conversation_id} 的 Chat Session")
    
    def restore_chat_history(self, conversation_id: str, messages: List[Dict[str, Any]], 
                            model: str = "gemini-2.5-flash"):
        """
        从数据库恢复历史记录到 Chat Session（改进版 - 支持文件引用）
        
        使用 Content 和 Part 结构体直接初始化 Chat Session 的历史，
        避免重新生成模型回复，确保历史记录完全一致。
        支持恢复文件引用（File API）。
        
        Args:
            conversation_id: 对话ID
            messages: 历史消息列表，格式为 [{'role': 'user/assistant', 'content': '...', 'files': [...]}, ...]
            model: 使用的模型名称
        """
        # 清除旧的 Session
        if conversation_id in self.chat_sessions:
            self.clear_chat_session(conversation_id)
        
        print(f"🔄 正在恢复对话 {conversation_id} 的历史记录（共 {len(messages)} 条消息）...")
        
        try:
            # 转换历史格式为 Gemini 的 Content 结构
            gemini_history: List[Content] = []
            
            for msg in messages:
                # 角色映射：OpenAI 格式 -> Gemini 格式
                role_map = {'user': 'user', 'assistant': 'model'}
                role = role_map.get(msg['role'], 'user')
                
                parts: List[Part] = []
                
                # 1. 恢复文本 Part
                if msg.get('content'):
                    parts.append(Part(text=msg['content']))
                
                # 2. 恢复文件 Part【核心修复】
                if 'files' in msg and msg['files']:
                    for file_info in msg['files']:
                        # 兼容字符串格式的附件（表示本地路径或说明）
                        if isinstance(file_info, str):
                            attachment_name = os.path.basename(file_info) or file_info
                            parts.append(Part(text=f"[附件：{attachment_name}]"))
                            continue

                        if not isinstance(file_info, dict):
                            # 未知格式，记录占位信息
                            parts.append(Part(text="[附件信息格式不支持]"))
                            continue

                        if file_info.get('type') == 'file_ref' and file_info.get('uri'):
                            # 使用 Part.from_uri 恢复 File API 引用
                            try:
                                # 检查文件是否仍然有效（48小时内）
                                file_uri = file_info['uri']
                                parts.append(Part.from_uri(file_uri))
                                print(f"   → 恢复文件引用: {file_uri}")
                            except Exception as e:
                                print(f"   [WARNING] 恢复文件引用失败: {file_uri}, 错误: {str(e)}")
                                # 文件可能已过期，添加说明文本
                                parts.append(Part(text=f"[文件已过期: {file_info.get('mime_type', 'unknown')}]"))
                        
                        elif file_info.get('type') == 'inline_data':
                            # 内嵌数据无法恢复，添加占位符
                            print(f"   [WARNING] 内嵌数据无法恢复: {file_info.get('mime_type', 'unknown')}")
                            parts.append(Part(text=f"[内嵌数据（无法恢复）: {file_info.get('mime_type', 'unknown')}]"))
                
                if not parts:
                    continue
                
                # 创建 Content 对象
                content = Content(role=role, parts=parts)
                gemini_history.append(content)
            
            # 准备配置
            config = {}
            if self.system_instruction:
                config["system_instruction"] = self.system_instruction
            
            # 【核心改进】通过 history 参数直接初始化 Chat Session
            # 这样可以精确恢复历史，而不会重新生成模型回复
            if config:
                chat = self.client.chats.create(
                    model=model, 
                    history=gemini_history, 
                    config=config
                )
            else:
                chat = self.client.chats.create(
                    model=model, 
                    history=gemini_history
                )
            
            self.chat_sessions[conversation_id] = {
                'chat': chat,
                'model': model,
                'created_at': datetime.now()
            }
            
            print(f"[OK] 历史记录恢复完成（使用 Content 结构体）")
            
        except Exception as e:
            print(f"[ERROR] 恢复历史记录失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 降级：创建空的 Chat Session
            print("[WARNING] 降级：创建新的空 Chat Session")
            self.create_chat_session(conversation_id, model)
    
    def cleanup_expired_files(self):
        """清理过期的文件引用（48小时后过期）"""
        now = datetime.now()
        expired_files = []
        
        for file_id, file_info in self.uploaded_files.items():
            if now - file_info['uploaded_at'] > timedelta(hours=48):
                expired_files.append(file_id)
        
        for file_id in expired_files:
            del self.uploaded_files[file_id]
            print(f"🗑️ 已清理过期文件引用: {file_id}")
    
    def delete_server_file(self, file_id: str) -> bool:
        """
        从 Gemini 服务器删除文件（用于持久文件的手动删除）
        
        Args:
            file_id: 文件ID（格式：files/xxx）
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        try:
            print(f"🗑️ 删除服务器文件: {file_id}")
            # 修复：使用正确的 genai.delete_file 方法
            import google.generativeai as genai
            genai.delete_file(name=file_id)
            
            # 从缓存中移除
            if file_id in self.uploaded_files:
                del self.uploaded_files[file_id]
                print(f"[OK] 文件已从服务器和缓存中删除: {file_id}")
            else:
                print(f"[OK] 文件已从服务器删除: {file_id}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 删除服务器文件失败: {file_id}, 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_session_info(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定对话的会话信息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            会话信息字典，包含模型、创建时间等
        """
        return self.chat_sessions.get(conversation_id)
    
    def _extract_text_from_response(self, response) -> str:
        """
        从 Gemini 响应对象中提取文本内容
        
        Args:
            response: Gemini API 响应对象
            
        Returns:
            提取的文本内容
        """
        try:
            if response and hasattr(response, 'text') and response.text:
                return response.text
            # 兼容其他可能的响应结构
            if response and hasattr(response, 'candidates') and response.candidates:
                if response.candidates[0].content.parts:
                    return response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"[WARNING] 提取响应文本失败: {e}")
        return "AI 助手未返回有效内容。"
    
    def send_text_message(self, conversation_id: str, message: str, model: str = "gemini-2.5-flash") -> str:
        """
        发送纯文本消息
        
        Args:
            conversation_id: 对话ID
            message: 消息内容
            model: 模型名称
            
        Returns:
            模型回复文本
        """
        # 确保 Chat Session 存在
        if conversation_id not in self.chat_sessions:
            self.create_chat_session(conversation_id, model)
        
        chat = self.get_chat_session(conversation_id)
        if not chat:
            raise ValueError(f"无法获取对话 {conversation_id} 的 Chat Session")
        
        try:
            print(f"📤 发送纯文本消息: {message[:50]}...")
            response = chat.send_message(message)
            return self._extract_text_from_response(response)
        except Exception as e:
            print(f"[ERROR] 发送纯文本消息失败: {str(e)}")
            return f"Error: {str(e)}"
    
    def upload_file_for_context(self, conversation_id: str, message: str, 
                                file_paths: List[str], model: str = "gemini-2.5-flash") -> str:
        """
        上传文件到 File API 并使用其引用进行对话（文件引用会保留在聊天历史中）
        
        这是持久化模式，文件上传到 Gemini 服务器，可在多轮对话中引用。
        
        Args:
            conversation_id: 对话ID
            message: 用户消息内容
            file_paths: 要上传的文件路径列表
            model: 使用的模型名称
            
        Returns:
            模型的回复文本
        """
        print(f"[LINK] 持久化模式：上传 {len(file_paths)} 个文件到服务器")
        
        # 使用现有的 send_message_with_files，但只使用 persistent 模式
        file_ids = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"[WARNING] 文件不存在: {file_path}")
                continue
            
            try:
                mime_type = self._get_mime_type(file_path)
                uploaded_file = self._upload_file_to_gemini(file_path, mime_type)
                
                if hasattr(uploaded_file, 'name'):
                    file_ids.append(uploaded_file.name)
                    print(f"[OK] 文件上传成功: {uploaded_file.name}")
            except Exception as e:
                print(f"[ERROR] 文件上传失败: {file_path}, 错误: {str(e)}")
        
        if not file_ids:
            print("[WARNING] 没有成功上传任何文件，发送纯文本消息")
            return self.send_text_message(conversation_id, message, model)
        
        # 使用 persistent_file_ids 发送消息
        return self.send_message_with_files(
            conversation_id=conversation_id,
            message=message,
            file_paths=None,
            persistent_file_ids=file_ids,
            model=model
        )
    
    def attach_file_for_onetime(self, conversation_id: str, message: str, 
                               file_paths: List[str], model: str = "gemini-2.5-flash") -> str:
        """
        将文件内容 Base64 编码后作为内嵌数据发送（内容仅在当前请求中有效）
        
        这是临时模式，文件不上传到服务器，仅在本次对话中使用。适合 <20MB 的文件。
        
        Args:
            conversation_id: 对话ID
            message: 用户消息内容
            file_paths: 要内嵌的文件路径列表
            model: 使用的模型名称
            
        Returns:
            模型的回复文本
        """
        print(f"[DOC] 临时模式：内嵌 {len(file_paths)} 个文件")
        
        # 检查文件大小限制
        valid_files = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"[WARNING] 文件不存在: {file_path}")
                continue
            
            file_size = os.path.getsize(file_path)
            if file_size >= 20 * 1024 * 1024:
                print(f"[WARNING] 文件超过 20MB 限制，跳过: {file_path} ({file_size / (1024*1024):.2f} MB)")
                continue
            
            valid_files.append(file_path)
        
        if not valid_files:
            print("[WARNING] 没有有效的文件，发送纯文本消息")
            return self.send_text_message(conversation_id, message, model)
        
        # 使用 file_paths 发送消息（临时模式）
        return self.send_message_with_files(
            conversation_id=conversation_id,
            message=message,
            file_paths=valid_files,
            persistent_file_ids=None,
            model=model
        )


# 全局单例
_gemini_context_manager: Optional[GeminiContextManager] = None


def get_gemini_context_manager() -> Optional[GeminiContextManager]:
    """
    获取全局 Gemini 上下文管理器实例
    
    Returns:
        GeminiContextManager 实例，如果初始化失败则返回 None
    """
    global _gemini_context_manager
    
    if _gemini_context_manager is None:
        try:
            # 从配置中获取 API 密钥
            api_key = get_gemini_api_key()
            
            if not api_key:
                print("[ERROR] 无法获取 Gemini API 密钥，请检查环境变量或配置文件")
                return None
            
            # 使用密钥初始化上下文管理器
            _gemini_context_manager = GeminiContextManager(api_key=api_key)
            
        except Exception as e:
            print(f"[ERROR] 初始化 Gemini 上下文管理器失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    return _gemini_context_manager
