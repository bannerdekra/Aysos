import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer
from chat_ui import ChatWindow
from api_client import get_deepseek_reply, get_topic_from_reply
from storage_config import StorageConfig
from dialogs import ChatConfigDialog, DSNConfigDialog, show_connection_result

class WorkerSignals(QObject):
    result = pyqtSignal(str)
    topic_result = pyqtSignal(str)

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
        self.is_first_message = True  # 标记是否为当前对话的第一条消息
        self.first_user_message = None  # 保存第一条用户消息，用于生成标题
        
        # 连接信号
        self.chat_window.send_message_signal.connect(self.handle_send_message)
        self.chat_window.sidebar.conversation_clicked.connect(self.load_conversation_messages)
        self.chat_window.sidebar.new_conversation_signal.connect(self.start_new_conversation)
        self.chat_window.sidebar.delete_conversation_signal.connect(self.delete_conversation)
        self.chat_window.sidebar.rename_conversation_signal.connect(self.rename_conversation)
        self.chat_window.sidebar.refresh_conversations_signal.connect(self.refresh_conversations)
        
        # 连接设置信号
        self.chat_window.settings_signal.connect(self.handle_settings)
        
        # API 相关信号
        self.chat_window.input_bar.cancel_request_signal.connect(self.handle_cancel_request)
        
        # 消息编辑信号
        self.chat_window.chat_area.edit_message_signal.connect(self.handle_edit_message)
        
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
        
        # 根据消息数量判断是否为第一条消息
        self.is_first_message = len(messages) == 0
        
        # 清空当前显示
        self.chat_window.chat_area.clear_chat_history_display()
        
        # 添加历史消息
        for message in messages:
            self.chat_window.chat_area.add_history_bubble(
                message['role'], 
                message['content']
            )

    def start_new_conversation(self):
        """开始新对话"""
        self.current_conversation_id = self.storage.create_new_conversation()
        self.is_first_message = True
        self.first_user_message = None
        
        # 清空聊天区域
        self.chat_window.chat_area.clear_chat_history_display()
        
        # 重新加载对话列表
        self.load_conversations()

    def clear_current_conversation(self): 
        if self.current_conversation_id:
            self.storage.delete_conversation(self.current_conversation_id)
            self.load_conversations()
            self.start_new_conversation()
        else:
            print("没有当前对话ID，无法清除对话记录")

    def delete_conversation(self, conv_id):
        """删除指定的对话"""
        print(f"准备删除对话: {conv_id}")
        
        # 先从存储删除
        self.storage.delete_conversation(conv_id)
        print(f"对话已从存储删除: {conv_id}")
        
        # 重新加载对话列表
        self.load_conversations()
        
        # 处理当前对话的逻辑
        if conv_id == self.current_conversation_id:
            # 如果删除的是当前对话，开始新对话
            self.start_new_conversation()

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

    def handle_send_message(self, user_input):
        """处理发送消息"""
        print(f"用户输入: {user_input}")
        
        if not self.current_conversation_id:
            print("没有当前对话，创建新对话")
            self.start_new_conversation()
        
        # 如果是第一条消息，保存用户输入用于生成标题
        if self.is_first_message:
            self.first_user_message = user_input
        
        # 保存用户消息到存储
        self.storage.add_message(self.current_conversation_id, 'user', user_input)
        
        # 添加用户消息到界面
        self.chat_window.chat_area.add_history_bubble('user', user_input)
        
        # 添加思考气泡
        thinking_bubble = self.chat_window.chat_area.add_thinking_bubble()
        
        # 获取对话历史
        messages = self.storage.get_history(self.current_conversation_id)
        
        # 创建工作线程来获取回复
        worker = Worker(get_deepseek_reply, messages)
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
            
        print(f"收到API回复: {response[:100]}...")
        
        # 移除thinking动画并添加回复
        self.chat_window.chat_area.update_chat_display(response)
        
        # 保存AI回复到存储
        self.storage.add_message(self.current_conversation_id, 'assistant', response)
        
        # 如果这是对话的第一条消息，生成标题
        if self.is_first_message:
            self.is_first_message = False
            self.generate_conversation_title(self.first_user_message)
        
        # 重置输入框按钮状态为正常状态
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
    
    print("🎯 Agent Chat 启动完成")
    print("✅ 已集成增强主题管理器和响应式UI组件")
    print("⚡ 按钮响应已优化，支持预渲染和异步更新")
    print("🔧 支持快速切换深色/浅色模式")
    
    # 显示窗口
    chat_window.show()
    
    # 启动应用程序
    sys.exit(app.exec())