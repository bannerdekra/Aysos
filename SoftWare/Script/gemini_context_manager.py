"""
Gemini 上下文管理器
实现 Chat Session 和文件上下文管理，为 Gemini 模型提供连贯的多轮对话能力
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# 检查 Google GenAI SDK 是否可用
GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai.types import Content, Part
    GENAI_AVAILABLE = True
    print("✅ Gemini 上下文管理器：Google GenAI SDK 已加载")
except ImportError:
    print("❌ Gemini 上下文管理器：Google GenAI SDK 未安装")
    GENAI_AVAILABLE = False


class GeminiContextManager:
    """
    Gemini 上下文管理器
    
    功能：
    1. 管理 Chat Session（聊天会话），实现上下文记忆
    2. 管理文件引用，支持多模态上下文
    3. 支持系统指令设置
    4. 自动处理会话历史
    """
    
    def __init__(self):
        """初始化上下文管理器"""
        if not GENAI_AVAILABLE:
            raise ImportError("Google GenAI SDK 未安装，无法使用上下文管理器")
        
        # 检查环境变量
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY 环境变量未设置")
        
        # 创建客户端
        self.client = genai.Client()
        
        # 会话管理：conversation_id -> chat_session
        self.chat_sessions: Dict[str, Any] = {}
        
        # 文件管理：file_id -> file_reference
        self.uploaded_files: Dict[str, Any] = {}
        
        # 系统指令（可选）
        self.system_instruction: Optional[str] = None
        
        print("✅ Gemini 上下文管理器初始化成功")
    
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
            print(f"⚠️ 对话 {conversation_id} 的 Chat Session 已存在")
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
            print(f"✅ 为对话 {conversation_id} 创建了 Chat Session (模型: {model})")
        except Exception as e:
            print(f"❌ 创建 Chat Session 失败: {str(e)}")
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
                print(f"✅ 收到回复: {response.text[:50]}...")
                return response.text
            else:
                return "Error: Empty response from Gemini."
        
        except Exception as e:
            print(f"❌ 发送消息失败: {str(e)}")
            return f"Error: {str(e)}"
    
    ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

    def send_message_with_files(self, conversation_id: str, message: str, 
                                file_paths: List[str], model: str = "gemini-2.5-flash") -> str:
        """
        发送包含文件的消息（多模态上下文）
        
        智能处理文件上传：
        - 小于20MB：使用 Part.from_bytes 内嵌上传
        - 大于等于20MB：使用 File API 上传
        
        Args:
            conversation_id: 对话ID
            message: 用户消息内容
            file_paths: 要上传的文件路径列表
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
            # 处理文件：统一使用 File API 上传，并限制允许的文件类型
            content_parts = []

            for file_path in file_paths:
                if not os.path.exists(file_path):
                    print(f"⚠️ 文件不存在: {file_path}")
                    continue

                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in self.ALLOWED_EXTENSIONS:
                    print(f"⚠️ 不支持的文件类型: {file_path}，仅支持 PDF、JPG、PNG")
                    continue

                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)

                print(f"📁 上传文件: {file_name} ({file_size / (1024*1024):.2f} MB)")

                mime_type = self._get_mime_type(file_path)

                try:
                    uploaded_file = self._upload_file_to_gemini(file_path, mime_type)
                    content_parts.append(uploaded_file)
                except Exception as upload_error:
                    print(f"❌ 文件上传失败: {file_path}, 错误: {upload_error}")
            
            if not content_parts:
                print("⚠️ 没有成功处理任何文件，按普通消息发送")
                return self.send_message(conversation_id, message, model)
            
            # 构建完整的内容（文件 + 文本提示）
            # 注意：根据官方示例，文件应该在前面，文本提示在后面
            contents = content_parts + [message]
            
            print(f"📤 发送消息（含 {len(content_parts)} 个文件）到对话 {conversation_id}")
            print(f"📝 内容顺序: [{len(content_parts)} 个文件] + [文本提示]")
            
            # 发送消息（直接传递列表，不使用命名参数）
            response = chat.send_message(contents)
            
            if response and response.text:
                print(f"✅ 收到回复: {response.text[:50]}...")
                return response.text
            else:
                return "Error: Empty response from Gemini."
        
        except Exception as e:
            print(f"❌ 发送包含文件的消息失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"

    def _upload_file_to_gemini(self, file_path: str, mime_type: str):
        """使用 Gemini File API 上传文件，并缓存返回的文件引用。"""
        uploaded_file = self.client.files.upload(file=file_path, mime_type=mime_type)

        file_id = uploaded_file.name if hasattr(uploaded_file, 'name') else str(len(self.uploaded_files))
        self.uploaded_files[file_id] = {
            'file': uploaded_file,
            'path': file_path,
            'uploaded_at': datetime.now()
        }
        print(f"  → 文件已上传至 Gemini，ID: {file_id}")
        return uploaded_file
    
    def _get_mime_type(self, file_path: str) -> str:
        """
        根据文件扩展名获取 MIME 类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME 类型字符串
        """
        import mimetypes
        
        # 尝试自动检测
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type:
            return mime_type
        
        # 常见文件类型的手动映射
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.java': 'text/x-java',
            '.cpp': 'text/x-c++',
            '.c': 'text/x-c',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.wav': 'audio/wav',
            '.avi': 'video/x-msvideo',
        }
        
        return mime_map.get(ext, 'application/octet-stream')
    
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
            print(f"⚠️ 对话 {conversation_id} 的 Chat Session 不存在")
            return []
        
        chat = session_info['chat']
        if not chat:
            return []
        
        try:
            # 使用 get_history() 方法获取历史记录
            if not hasattr(chat, 'get_history'):
                print(f"⚠️ Chat Session 没有 get_history 方法")
                return []
            
            chat_history = chat.get_history()
            print(f"📚 Chat Session 历史记录数量: {len(chat_history) if chat_history else 0}")
            
            if not chat_history:
                print(f"⚠️ Chat Session 历史记录为空")
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
            
            print(f"✅ 成功提取 {len(history_data)} 条历史记录")
            return history_data
            
        except Exception as e:
            print(f"⚠️ 获取历史记录失败: {str(e)}")
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
                        if file_info.get('type') == 'file_ref' and file_info.get('uri'):
                            # 使用 Part.from_uri 恢复 File API 引用
                            try:
                                # 检查文件是否仍然有效（48小时内）
                                file_uri = file_info['uri']
                                parts.append(Part.from_uri(file_uri))
                                print(f"   → 恢复文件引用: {file_uri}")
                            except Exception as e:
                                print(f"   ⚠️ 恢复文件引用失败: {file_uri}, 错误: {str(e)}")
                                # 文件可能已过期，添加说明文本
                                parts.append(Part(text=f"[文件已过期: {file_info.get('mime_type', 'unknown')}]"))
                        
                        elif file_info.get('type') == 'inline_data':
                            # 内嵌数据无法恢复，添加占位符
                            print(f"   ⚠️ 内嵌数据无法恢复: {file_info.get('mime_type', 'unknown')}")
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
            
            print(f"✅ 历史记录恢复完成（使用 Content 结构体）")
            
        except Exception as e:
            print(f"❌ 恢复历史记录失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 降级：创建空的 Chat Session
            print("⚠️ 降级：创建新的空 Chat Session")
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
    
    def get_session_info(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定对话的会话信息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            会话信息字典，包含模型、创建时间等
        """
        return self.chat_sessions.get(conversation_id)


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
            _gemini_context_manager = GeminiContextManager()
        except Exception as e:
            print(f"❌ 初始化 Gemini 上下文管理器失败: {str(e)}")
            return None
    
    return _gemini_context_manager
