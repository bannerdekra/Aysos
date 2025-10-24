import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer
from chat_ui import ChatWindow
from api_client import get_ai_reply, get_topic_from_reply
from storage_config import StorageConfig
from dialogs import ChatConfigDialog, DSNConfigDialog, show_connection_result, show_delete_confirmation


class WorkerSignals(QObject):
    result = pyqtSignal(object)  # 改为 object 类型以支持 str 和 dict
    topic_result = pyqtSignal(str)
    progress = pyqtSignal(float, str)  # 进度信号：(进度值, 状态描述)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.result.emit(f"Error: {str(e)}")

class TopicWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(TopicWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.topic_result.emit(result)
        except Exception as e:
            self.signals.topic_result.emit(f"Error: {str(e)}")

class ChatManager:
    def __init__(self, chat_window):
        self.chat_window = chat_window
        self.threadpool = QThreadPool()
        
        # 使用新的存储配置管理器
        self.storage = StorageConfig()
        
        # 初始化变量
        self.current_conversation_id = None
        self.current_worker = None
        self.topic_worker = None
        self.conversation_round_count = 0  # 对话轮数计数器（一问一答为一轮）
        self.first_user_message = None  # 保存第一条用户消息，用于生成标题
        self._deleting_conversation = False  # 防止删除时重复触发
        
        # 连接信号
        self.chat_window.send_message_signal.connect(self.handle_send_message)
        self.chat_window.sidebar.conversation_clicked.connect(self.load_conversation_messages)
        self.chat_window.sidebar.new_conversation_signal.connect(self.start_new_conversation)
        self.chat_window.delete_conversation_signal.connect(self.delete_conversation)
        self.chat_window.rename_conversation_signal.connect(self.rename_conversation)
        self.chat_window.sidebar.refresh_conversations_signal.connect(self.refresh_conversations)
        
        # 连接设置信号
        self.chat_window.settings_signal.connect(self.handle_settings)
        
        # API 相关信号
        self.chat_window.input_bar.cancel_request_signal.connect(self.handle_cancel_request)
        
        # 【新增】图片生成信号
        self.chat_window.input_bar.generate_image_signal.connect(self.handle_generate_image)
        self.chat_window.input_bar.generate_with_params_signal.connect(self.handle_generate_with_params)
        
        # 消息编辑和删除信号
        self.chat_window.chat_area.edit_message_signal.connect(self.handle_edit_message)
        self.chat_window.delete_message_signal.connect(self.handle_delete_message)
        
        # 加载历史对话
        self.load_conversations()

    def handle_settings(self):
        """处理设置按钮点击"""
        from dialogs import SettingsDialog
        
        # 创建设置对话框
        settings_dialog = SettingsDialog(self.chat_window)
        
        # 连接聊天记录配置信号
        settings_dialog.chat_config_dsn_signal.connect(self.configure_dsn_storage)
        settings_dialog.chat_config_file_signal.connect(self.configure_file_storage)
        
        # 显示设置对话框
        settings_dialog.exec()
    
    def configure_dsn_storage(self):
        """配置DSN存储"""
        dsn_dialog = DSNConfigDialog(self.chat_window)
        
        if dsn_dialog.exec():
            dsn_name = dsn_dialog.get_dsn_name()
            
            # 测试DSN连接
            if self.storage.test_dsn_connection(dsn_name):
                # 连接成功，切换到数据库存储
                old_storage_type = self.storage.get_current_storage_type()
                self.storage.switch_to_dsn_storage(dsn_name)
                
                # 显示成功消息
                show_connection_result(self.chat_window, True, "DSN连接成功！已切换到数据库存储。")
                
                # 如果之前使用文件存储，询问是否迁移数据
                if old_storage_type == 'file':
                    reply = QMessageBox.question(
                        self.chat_window, 
                        "数据迁移", 
                        "检测到文件存储中有数据，是否迁移到数据库？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        if self.storage.migrate_data():
                            QMessageBox.information(self.chat_window, "迁移成功", "数据已成功迁移到数据库！")
                        else:
                            QMessageBox.warning(self.chat_window, "迁移失败", "数据迁移失败，请检查数据库连接。")
                
                # 重新加载对话列表
                self.load_conversations()
                
            else:
                # 连接失败
                show_connection_result(self.chat_window, False, "DSN连接失败！请检查DSN配置。")
    
    def configure_file_storage(self):
        """配置文件存储"""
        old_storage_type = self.storage.get_current_storage_type()
        
        # 切换到文件存储
        self.storage.switch_to_file_storage()
        
        QMessageBox.information(self.chat_window, "配置成功", "已切换到文件存储模式！")
        
        # 如果之前使用数据库存储，询问是否迁移数据
        if old_storage_type == 'database':
            reply = QMessageBox.question(
                self.chat_window, 
                "数据迁移", 
                "检测到数据库中有数据，是否迁移到文件？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.storage.migrate_data():
                    QMessageBox.information(self.chat_window, "迁移成功", "数据已成功迁移到文件！")
                else:
                    QMessageBox.warning(self.chat_window, "迁移失败", "数据迁移失败，请检查文件权限。")
        
        # 重新加载对话列表
        self.load_conversations()

    def load_conversations(self):
        """加载所有对话到侧边栏"""
        # 如果使用文件存储，先执行扫描以确保包含所有文件
        if hasattr(self.storage, 'file_manager') and self.storage.config["storage_type"] == "file":
            self.storage.file_manager.scan_and_rebuild_metadata()
        
        conversations_data = self.storage.get_all_conversations()
        
        # 转换数据格式以适配UI
        conversations = []
        for conv_data in conversations_data:
            if isinstance(conv_data, tuple):
                # FileManager返回元组格式 (id, title, updated_at)
                conversations.append({
                    'id': conv_data[0],
                    'title': conv_data[1],
                    'updated_at': conv_data[2]
                })
            else:
                # DatabaseManager返回字典格式
                conversations.append(conv_data)
        
        self.chat_window.sidebar.update_conversation_list(conversations)

        # 同步侧边栏高亮状态
        self.chat_window.set_current_conversation(self.current_conversation_id)
        
        # 不自动选择对话，保持当前对话ID为None，直到用户主动选择或发送消息
        if conversations and self.current_conversation_id is not None:
            # 只有在当前对话ID存在于对话列表中时才保持选择
            conversation_ids = [conv['id'] for conv in conversations]
            if self.current_conversation_id in conversation_ids:
                self.load_conversation_messages(self.current_conversation_id)
            else:
                self.current_conversation_id = None
                print("历史对话已加载，请选择一个对话或发送新消息开始聊天")
        else:
            self.current_conversation_id = None
            if conversations:
                print("历史对话已加载，请选择一个对话或发送新消息开始聊天")
            else:
                print("没有历史对话，请发送消息开始新的对话")

    def load_conversation_messages(self, conversation_id):
        """加载指定对话的消息"""
        self.current_conversation_id = conversation_id
        # 更新侧边栏当前对话高亮
        self.chat_window.set_current_conversation(conversation_id)
        messages = self.storage.get_history(conversation_id)
        
        # 根据消息数量计算对话轮数（一问一答为一轮）
        self.conversation_round_count = len(messages) // 2
        
        # 【新增】同步 Gemini 上下文历史
        # 如果使用 Gemini 且有历史记录，需要恢复 Chat Session
        self._sync_gemini_context(conversation_id, messages)
        
        # 清空当前显示
        self.chat_window.chat_area.clear_chat_history_display()
        
        # 【调试日志】检查加载的消息内容
        print(f"\n[DEBUG] 加载对话 {conversation_id} 的消息:")
        
        # 添加历史消息（包含附件信息）
        for i, message in enumerate(messages):
            content = message['content']
            role = message['role']
            content_length = len(content)
            content_preview = content[:80] if content else "(空)"
            
            print(f"  消息{i+1} [{role}]: 长度={content_length}, 预览={content_preview}...")
            
            file_paths = message.get('files', None)  # 获取附件路径（如果有）
            self.chat_window.chat_area.add_history_bubble(
                role, 
                content,
                file_paths  # 传递附件路径
            )
        
        print(f"[DEBUG] 加载完成，共 {len(messages)} 条消息\n")
    
    def _sync_gemini_context(self, conversation_id, messages):
        """同步 Gemini 上下文历史"""
        try:
            from api_config import get_current_provider_name
            from gemini_context_manager import get_gemini_context_manager
            
            # 只在使用 Gemini 时同步
            if get_current_provider_name() != 'gemini':
                return
            
            # 如果没有历史记录，无需同步
            if not messages:
                return
            
            # 获取上下文管理器
            context_manager = get_gemini_context_manager()
            if not context_manager:
                print("[WARNING] Gemini 上下文管理器不可用，跳过历史同步")
                return
            
            # 恢复历史记录到 Chat Session
            print(f"🔄 同步 Gemini 上下文历史到对话 {conversation_id}")
            context_manager.restore_chat_history(conversation_id, messages)
            print(f"[OK] Gemini 上下文历史同步完成")
            
        except ImportError:
            # Gemini 上下文管理器未安装
            pass
        except Exception as e:
            print(f"[WARNING] Gemini 上下文历史同步失败: {str(e)}")

    def search_text_globally(self, search_text):
        """全局搜索所有对话中的文本"""
        # 获取所有对话
        conversations_data = self.storage.get_all_conversations()
        
        if not conversations_data:
            return None  # 没有对话
        
        # 遍历所有对话
        for conv_data in conversations_data:
            # 获取对话ID
            if isinstance(conv_data, tuple):
                conv_id = conv_data[0]
            else:
                conv_id = conv_data['id']
            
            # 获取该对话的所有消息
            messages = self.storage.get_history(conv_id)
            
            # 在消息中查找匹配项
            for message in messages:
                if search_text.lower() in message['content'].lower():
                    # 找到匹配项，切换到该对话
                    self.load_conversation_messages(conv_id)
                    
                    # 使用 QTimer 延迟执行搜索，确保UI已经加载完成
                    # 传递 search_text 参数用于文本高亮
                    QTimer.singleShot(100, lambda st=search_text: self._perform_search_after_load(st))
                    
                    return True  # 找到匹配项
        
        return False  # 没有找到匹配项
    
    def _perform_search_after_load(self, search_text):
        """在加载对话后执行搜索"""
        matches = self.chat_window.chat_area.search_text_in_current(search_text)
        if matches:
            self.chat_window.chat_area.scroll_to_bubble(matches[0], search_text)

    def start_new_conversation(self):
        """开始新对话"""
        self.current_conversation_id = self.storage.create_new_conversation()
        self.conversation_round_count = 0
        self.first_user_message = None
        
        # 清空聊天区域
        self.chat_window.chat_area.clear_chat_history_display()
        
        # 重新加载对话列表
        self.load_conversations()

    def clear_current_conversation(self): 
        """清除当前对话"""
        if self.current_conversation_id:
            # 获取当前对话标题（如果有的话）
            conv_title = "当前对话"
            conversations = self.storage.get_all_conversations()
            for conv in conversations:
                if isinstance(conv, tuple):
                    if conv[0] == self.current_conversation_id:
                        conv_title = conv[1]
                        break
                elif conv.get('id') == self.current_conversation_id:
                    conv_title = conv.get('title', '当前对话')
                    break
            
            # 显示确认对话框
            if not show_delete_confirmation(self.chat_window, conv_title):
                print(f"用户取消清除对话")
                return  # 用户点击取消，不执行删除
            
            print(f"用户确认清除对话: {self.current_conversation_id}")
            self.storage.delete_conversation(self.current_conversation_id)
            self.load_conversations()
            self.start_new_conversation()
        else:
            print("没有当前对话ID，无法清除对话记录")

    def delete_conversation(self, conv_id, conv_title="对话"):
        """删除指定的对话"""
        # 防止重复删除
        if self._deleting_conversation:
            return
        
        self._deleting_conversation = True
        
        try:
            print(f"准备删除对话: {conv_id}")

            # 先从存储删除（已在 UI 中确认，避免重复弹窗）
            self.storage.delete_conversation(conv_id)
            print(f"对话已从存储删除: {conv_id}")
            
            # 处理当前对话的逻辑
            if conv_id == self.current_conversation_id:
                # 清空聊天区域
                self.chat_window.chat_area.clear_chat_history_display()
                self.current_conversation_id = None
                
                # 获取删除后的对话列表
                conversations_data = self.storage.get_all_conversations()
                
                if conversations_data:
                    # 如果还有其他对话，切换到第一个
                    first_conv = conversations_data[0]
                    if isinstance(first_conv, tuple):
                        first_conv_id = first_conv[0]
                    else:
                        first_conv_id = first_conv['id']
                    
                    print(f"切换到第一个对话: {first_conv_id}")
                    self.load_conversation_messages(first_conv_id)
                else:
                    # 如果没有其他对话，保持空白状态
                    print("没有其他对话，保持空白状态")
                    self.current_conversation_id = None
                    self.conversation_round_count = 0
                    self.first_user_message = None
            
            # 重新加载对话列表（确保UI同步）
            self.load_conversations()
        finally:
            self._deleting_conversation = False

    def rename_conversation(self, conv_id, new_title):
        """重命名对话"""
        try:
            self.storage.update_conversation_title(conv_id, new_title)
            print(f"对话重命名成功: {new_title}")
            # 更新UI中的标题
            self.chat_window.update_conversation_title_in_list(conv_id, new_title)
            print(f"对话重命名成功: {new_title}")
        except Exception as e:
            print(f"重命名对话失败: {e}")

    def refresh_conversations(self):
        """刷新对话列表，重新扫描文件夹（仅文件存储模式）"""
        print("刷新对话列表...")
        
        # 检查当前存储类型
        if hasattr(self.storage, 'file_manager') and self.storage.config["storage_type"] == "file":
            # 使用文件管理器刷新
            conversations = self.storage.file_manager.refresh_conversations()
            self.chat_window.sidebar.update_conversation_list(conversations)
            print(f"已刷新对话列表，共 {len(conversations)} 个对话")
        else:
            # 对于数据库存储，直接重新加载
            self.load_conversations()
            print("已重新加载对话列表")

    def handle_send_message(self, user_input, files=None):
        """处理发送消息（支持文件上传）"""
        print(f"用户输入: {user_input}")
        
        # 【调试日志】详细检查文件参数
        if files is None:
            print("📎 main.py: files 参数为 None")
        elif len(files) == 0:
            print("📎 main.py: files 参数为空列表 []")
        else:
            print(f"📎 main.py: 接收到 {len(files)} 个文件")
            for i, f in enumerate(files, 1):
                print(f"   [{i}] 类型: {type(f)}, 内容: {f}")
                if isinstance(f, dict):
                    for key, value in f.items():
                        print(f"       {key}: {value}")
        
        if not self.current_conversation_id:
            print("没有当前对话，创建新对话")
            self.start_new_conversation()
        
        # 如果是第一条消息，保存用户输入（用于之后可能的标题生成）
        if self.conversation_round_count == 0:
            self.first_user_message = user_input
        
        # 【修复Bug2】保存用户消息到存储时，将附件信息一起保存
        # 提取文件路径列表（用于持久化）
        file_paths = []
        if files:
            for file_info in files:
                if isinstance(file_info, dict) and 'path' in file_info:
                    file_paths.append(file_info['path'])
                elif isinstance(file_info, str):
                    file_paths.append(file_info)
        
        # 保存消息（包含附件路径信息）
        self.storage.add_message(self.current_conversation_id, 'user', user_input, file_paths)
        
        # 添加用户消息到界面（附带附件标签）
        self.chat_window.chat_area.add_history_bubble('user', user_input, file_paths)
        
        # 添加思考气泡
        thinking_bubble = self.chat_window.chat_area.add_thinking_bubble()
        
        # 获取对话历史
        messages = self.storage.get_history(self.current_conversation_id)
        
        # 创建工作线程来获取回复（传递 conversation_id 和 files 以支持 Gemini 上下文和文件）
        worker = Worker(get_ai_reply, messages, self.current_conversation_id, files)
        worker.signals.result.connect(
            lambda result: self.handle_api_response(result, thinking_bubble)
        )
        
        # 保存当前工作线程引用，用于取消请求
        self.current_worker = worker
        
        # 启动线程
        self.threadpool.start(worker)

    def handle_cancel_request(self):
        """处理取消API请求"""
        print("用户取消了API请求")
        
        # 清空当前工作线程引用（注意：无法真正停止已启动的线程）
        self.current_worker = None
        
        # 移除thinking动画
        if hasattr(self.chat_window.chat_area, 'remove_thinking_bubble'):
            self.chat_window.chat_area.remove_thinking_bubble()
        
        # 确保输入框按钮状态重置为正常状态
        self.chat_window.input_bar.set_normal_state()

    def handle_api_response(self, response, thinking_bubble):
        """处理API响应"""
        # 如果请求已被取消，忽略响应
        if self.current_worker is None:
            print("请求已取消，忽略API响应")
            return
        
        # 🔧 修复：检查 response 是否为 None
        if response is None:
            print("⚠️ API 返回 None，使用默认错误消息")
            response = "Error: API 调用失败，未返回有效响应。请检查网络连接或搜索引擎配置。"
            
        print(f"收到API回复: {response[:100] if response else '(空响应)'}...")
        
        # 移除thinking动画并添加回复
        self.chat_window.chat_area.update_chat_display(response)
        
        # 【调试】保存前检查内容长度
        print(f"[DEBUG] 准备保存 assistant 消息，长度={len(response)}, 预览={response[:80]}...")
        
        # 保存AI回复到存储
        self.storage.add_message(self.current_conversation_id, 'assistant', response)
        
        # 【调试】验证保存后的内容
        saved_messages = self.storage.get_history(self.current_conversation_id)
        if saved_messages:
            last_msg = saved_messages[-1]
            print(f"[DEBUG] 保存后验证: 长度={len(last_msg['content'])}, 预览={last_msg['content'][:80]}...")
        
        # 增加对话轮数
        self.conversation_round_count += 1
        
        # 如果达到3轮对话，生成标题
        if self.conversation_round_count == 3:
            # 【修复】使用 AI 回复内容生成标题，特别是包含附件分析的情况
            self.generate_conversation_title(response)
        
        # 检查响应是否为错误消息
        if not response.startswith("Error"):
            # 发送成功，清除临时文件（保留持久文件）
            self.chat_window.input_bar.on_send_success()
        else:
            # 发送失败，保留所有文件
            self.chat_window.input_bar.set_normal_state()
        
        # 清空当前工作线程引用
        self.current_worker = None

    def generate_conversation_title(self, first_user_message):
        """根据第一个用户消息生成对话标题"""
        print("生成对话标题...")
        
        # 创建主题生成工作线程
        topic_worker = TopicWorker(get_topic_from_reply, first_user_message)
        topic_worker.signals.topic_result.connect(
            lambda topic: self.update_conversation_title(topic)
        )
        
        self.topic_worker = topic_worker
        self.threadpool.start(topic_worker)

    def update_conversation_title(self, title):
        """更新对话标题"""
        if self.current_conversation_id and title.strip():
            clean_title = title.strip().replace('"', '').replace("'", '')
            print(f"更新对话标题: {clean_title}")
            
            # 更新存储中的标题
            self.storage.update_conversation_title(self.current_conversation_id, clean_title)
            
            # 只更新UI中的标题显示，不重新加载整个对话列表
            self.chat_window.sidebar.update_conversation_title_in_list(self.current_conversation_id, clean_title)

    def handle_edit_message(self, bubble_index, new_content):
        """处理消息编辑 - 自动删除后续消息并重新请求"""
        print(f"编辑消息: 索引={bubble_index}, 新内容={new_content[:50]}...")
        
        if not self.current_conversation_id:
            print("没有活动对话，无法编辑消息")
            return
        
        # 获取当前对话的所有消息
        messages = self.storage.get_history(self.current_conversation_id)
        
        if bubble_index >= len(messages):
            print(f"消息索引超出范围: {bubble_index} >= {len(messages)}")
            return
        
        # 要编辑的消息
        target_message = messages[bubble_index]
        
        # 只允许编辑用户消息
        if target_message['role'] != 'user':
            print("只能编辑用户消息")
            return
        
        print(f"编辑第{bubble_index}条消息，删除索引{bubble_index}及之后的所有消息")
        
        # 删除从编辑位置开始的所有消息（包括要编辑的消息）
        self.storage.delete_messages_from_index(self.current_conversation_id, bubble_index - 1)
        
        # 重新加载消息到界面
        self.load_conversation_messages(self.current_conversation_id)
        
        # 发送新的用户消息（这会触发API请求）
        self.handle_send_message(new_content)

    def handle_delete_message(self, bubble_index):
        """处理消息删除 - 删除指定索引的消息"""
        print(f"删除消息: 索引={bubble_index}")
        
        if not self.current_conversation_id:
            print("没有活动对话，无法删除消息")
            return
        
        # 获取当前对话的所有消息
        messages = self.storage.get_history(self.current_conversation_id)
        
        if bubble_index >= len(messages):
            print(f"消息索引超出范围: {bubble_index} >= {len(messages)}")
            return
        
        # 计算要删除的索引范围（用户消息 + 可能的 AI 回复）
        target_message = messages[bubble_index]
        
        # 判断删除策略
        if target_message['role'] == 'user':
            # 如果删除用户消息，检查是否有对应的 AI 回复
            base_index = bubble_index
            has_pair = False
            if base_index + 1 < len(messages) and messages[base_index + 1]['role'] == 'assistant':
                has_pair = True
        else:
            # 如果删除 AI 回复，也删除对应的用户消息
            if bubble_index > 0 and messages[bubble_index - 1]['role'] == 'user':
                base_index = bubble_index - 1
                has_pair = True
            else:
                base_index = bubble_index
                has_pair = False
        
        print(f"删除基础索引: {base_index}, 成对删除: {has_pair}")
        
        # 从数据库删除消息
        if has_pair:
            # 删除两条消息（用户 + AI）
            self.storage.delete_message_by_index(self.current_conversation_id, base_index)
            self.storage.delete_message_by_index(self.current_conversation_id, base_index)  # 删除后索引会自动调整
        else:
            # 只删除一条消息
            self.storage.delete_message_by_index(self.current_conversation_id, base_index)
        
        # 重新加载消息到界面
        self.load_conversation_messages(self.current_conversation_id)
        print("消息删除完成并刷新界面")
    
    def handle_generate_image(self, user_description: str):
        """
        处理图片生成请求
        
        Args:
            user_description: 用户的绘画描述
        """
        print(f"🎨 收到绘画请求: {user_description}")
        
        # 检查是否有当前对话
        if not self.current_conversation_id:
            print("没有当前对话，创建新对话")
            self.start_new_conversation()
        
        # 保存用户的绘画请求
        self.storage.add_message(self.current_conversation_id, 'user', f"[绘画请求] {user_description}", [])
        self.chat_window.chat_area.add_history_bubble('user', f"🎨 {user_description}")
        
        # 添加思考气泡
        thinking_bubble = self.chat_window.chat_area.add_thinking_bubble()
        
        # 创建图片生成工作线程
        image_worker = ImageGenerationWorker(user_description)
        
        # 连接结果信号
        image_worker.signals.result.connect(
            lambda result: self.handle_image_generation_result(result, thinking_bubble)
        )
        
        # 连接进度信号
        image_worker.signals.progress.connect(
            lambda progress, status: self.chat_window.chat_area.update_generation_progress(progress, status)
        )
        
        # 启动线程
        self.threadpool.start(image_worker)
    
    def handle_image_generation_result(self, result, thinking_bubble):
        """
        处理图片生成结果
        
        Args:
            result: {'success': bool, 'image_path': str, 'error': str}
            thinking_bubble: 思考气泡引用
        """
        # 确保 result 是字典类型
        if not isinstance(result, dict):
            print(f"[ERROR] 图片生成结果类型错误: {type(result)}")
            self.chat_window.chat_area.update_chat_display(
                "❌ 图片生成失败: 内部错误（结果类型不正确）"
            )
            self.chat_window.input_bar.set_normal_state()
            self.chat_window.input_bar.exit_image_generation_mode()
            return
        
        # 移除思考气泡（由display_generated_image内部处理）
        
        if result.get('success'):
            image_path = result.get('image_path')
            print(f"[OK] 图片生成成功: {image_path}")
            
            # 保存AI回复（图片路径）
            self.storage.add_message(
                self.current_conversation_id, 
                'assistant', 
                f"[生成图片] {os.path.basename(image_path)}",
                []
            )
            
            # 显示生成的图片
            self.chat_window.chat_area.display_generated_image(image_path)
            
            # 重置输入栏状态
            self.chat_window.input_bar.set_normal_state()
            self.chat_window.input_bar.exit_image_generation_mode()
            
        else:
            error_msg = result.get('error', '未知错误')
            print(f"[ERROR] 图片生成失败: {error_msg}")
            
            # 显示错误消息
            self.chat_window.chat_area.update_chat_display(
                f"❌ 图片生成失败: {error_msg}\n\n请检查 Stable Diffusion WebUI 是否已启动。"
            )
            
            # 重置输入栏状态
            self.chat_window.input_bar.set_normal_state()
            self.chat_window.input_bar.exit_image_generation_mode()
    
    def handle_generate_with_params(self, params: dict):
        """
        处理带参数的图片生成请求
        
        Args:
            params: 生成参数字典
        """
        print(f"🎨 收到带参数的绘画请求")
        print(f"  参数: {params}")
        
        # 检查是否有当前对话
        if not self.current_conversation_id:
            print("没有当前对话，创建新对话")
            self.start_new_conversation()
        
        # 保存用户的绘画请求
        prompt = params.get('prompt', '')
        self.storage.add_message(self.current_conversation_id, 'user', f"[绘画请求] {prompt[:50]}...", [])
        self.chat_window.chat_area.add_history_bubble('user', f"🎨 {prompt[:50]}...")
        
        # 添加思考气泡
        thinking_bubble = self.chat_window.chat_area.add_thinking_bubble()
        
        # 创建图片生成工作线程（使用自定义参数）
        image_worker = ImageGenerationWithParamsWorker(params)
        
        # 连接结果信号
        image_worker.signals.result.connect(
            lambda result: self.handle_image_generation_result(result, thinking_bubble)
        )
        
        # 连接进度信号  
        image_worker.signals.progress.connect(
            lambda progress, status: self.chat_window.chat_area.update_generation_progress(progress, status)
        )
        
        # 启动线程
        self.threadpool.start(image_worker)


class ImageGenerationWithParamsWorker(QRunnable):
    """图片生成工作线程 - 使用自定义参数"""
    def __init__(self, params: dict):
        super().__init__()
        self.params = params
        self.signals = WorkerSignals()
    
    def run(self):
        """执行图片生成"""
        try:
            from image_generator import get_image_generator
            
            generator = get_image_generator()
            
            # 步骤1: 检查连接
            def progress_callback(progress: float, status: str):
                self.signals.progress.emit(progress, status)
            
            progress_callback(0.05, "连接 SD WebUI")
            
            # 提取参数
            prompt = self.params.get('prompt', '')
            negative_prompt = self.params.get('negative_prompt', '')
            
            if not prompt:
                self.signals.result.emit({
                    'success': False,
                    'error': '提示词为空'
                })
                return
            
            # 步骤2: 开始生成
            progress_callback(0.15, "正在生成图片")
            
            # 生成图片（直接使用用户提供的英文提示词）
            print(f"[INFO] 使用自定义参数生成图片...")
            print(f"  提示词: {prompt}")
            print(f"  负面提示词: {negative_prompt}")
            print(f"  采样器: {self.params.get('sampler_name')}")
            print(f"  步数: {self.params.get('steps')}")
            
            # 准备kwargs参数
            kwargs = {
                'sampler_name': self.params.get('sampler_name'),
                'scheduler': self.params.get('scheduler'),
                'steps': self.params.get('steps'),
                'cfg_scale': self.params.get('cfg_scale'),
                'seed': self.params.get('seed'),
                'width': self.params.get('width'),
                'height': self.params.get('height')
            }
            
            image_path, error = generator.generate_image_with_progress(
                prompt=prompt,
                negative_prompt=negative_prompt,
                progress_callback=progress_callback,
                **kwargs
            )
            
            if image_path:
                self.signals.result.emit({
                    'success': True,
                    'image_path': image_path
                })
            else:
                self.signals.result.emit({
                    'success': False,
                    'error': error or '未知错误'
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.signals.result.emit({
                'success': False,
                'error': str(e)
            })


class ImageGenerationWorker(QRunnable):
    """图片生成工作线程 - 支持进度回调"""
    def __init__(self, user_description: str):
        super().__init__()
        self.user_description = user_description
        self.signals = WorkerSignals()
    
    def run(self):
        """执行图片生成"""
        try:
            from image_generator import get_image_generator
            
            generator = get_image_generator()
            
            # 步骤1: 检查连接
            self.signals.progress.emit(0.05, "连接 SD WebUI")
            print("[INFO] 检查 SD WebUI 连接...")
            success, message = generator.check_connection()
            if not success:
                self.signals.result.emit({
                    'success': False,
                    'error': message
                })
                return
            
            # 步骤2: 生成提示词
            self.signals.progress.emit(0.1, "正在生成提示词")
            print("[INFO] 正在通过AI优化提示词...")
            try:
                positive_prompt, negative_prompt = generator.translate_prompt_via_ai(self.user_description)
            except Exception as e:
                print(f"[ERROR] 提示词翻译失败: {e}")
                self.signals.result.emit({
                    'success': False,
                    'error': f'❌ AI 提示词生成失败: {str(e)}'
                })
                return
            
            if not positive_prompt or len(positive_prompt.strip()) < 5:
                self.signals.result.emit({
                    'success': False,
                    'error': '❌ AI 提示词生成失败，请重试'
                })
                return
            
            # 步骤3: 开始生成图片
            self.signals.progress.emit(0.2, "正在生成图片")
            
            # 定义进度回调函数
            def on_progress(progress: float, status: str):
                # 将进度映射到 0.2-1.0 区间（前20%用于AI翻译）
                mapped_progress = 0.2 + (progress * 0.8)
                self.signals.progress.emit(mapped_progress, status)
            
            # 生成图片（带进度回调，使用负面提示词）
            print(f"[INFO] 开始生成图像")
            print(f"[INFO] 正面提示词: {positive_prompt[:80]}...")
            print(f"[INFO] 负面提示词: {negative_prompt[:80]}...")
            image_path, error = generator.generate_image_with_progress(
                positive_prompt, 
                progress_callback=on_progress,
                negative_prompt=negative_prompt
            )
            
            if image_path:
                # 最终进度
                self.signals.progress.emit(1.0, "✅ 图像生成完成！")
                
                self.signals.result.emit({
                    'success': True,
                    'image_path': image_path,
                    'error': None
                })
            else:
                self.signals.result.emit({
                    'success': False,
                    'error': error or '生成失败'
                })
                
        except Exception as e:
            print(f"[ERROR] 图片生成异常: {e}")
            import traceback
            traceback.print_exc()
            self.signals.result.emit({
                'success': False,
                'error': str(e)
            })


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序基本信息
    app.setApplicationName("Agent Chat")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Your Organization")
    
    # 创建主窗口
    chat_window = ChatWindow()
    
    # 创建聊天管理器
    chat_manager = ChatManager(chat_window)
    
    # 设置聊天管理器引用到窗口
    chat_window.set_chat_manager(chat_manager)
    
    print("🎯 Agent Chat 启动完成")
    print("[OK] 已集成增强主题管理器和响应式UI组件")
    print("⚡ 按钮响应已优化，支持预渲染和异步更新")
    print("🔧 支持快速切换深色/浅色模式")
    
    # 显示窗口
    chat_window.show()
    
    # 启动应用程序
    sys.exit(app.exec())