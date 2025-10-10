import sys
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDialog
from PyQt6.QtGui import QPixmap, QPainter, QColor, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from sidebar import Sidebar
from input_bar import InputBar
from chat_area import ChatArea
from dialogs import RenameDialog, show_delete_confirmation
from theme_manager import ThemeManager, DarkModeOverlay

def resource_path(relative_path):
    """用于获取正确的文件路径，兼容PyInstaller打包后的相对路径问题。"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        current_file = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(os.path.dirname(current_file))
    
    full_path = os.path.join(base_path, relative_path)
    return full_path

# --- USER CONFIGURATION ---
BACKGROUND_PATH = resource_path(os.path.join("SoftWare", "Image", "Backgroud", "【哲风壁纸】动漫女孩-可爱.png"))
# --- END USER CONFIGURATION ---

class ChatWindow(QWidget):
    """主聊天窗口"""
    send_message_signal = pyqtSignal(str, list)  # 修复：消息内容, 文件列表
    prompt_signal = pyqtSignal(str)
    clear_history_signal = pyqtSignal()
    cancel_request_signal = pyqtSignal()  # 新增：取消请求信号
    
    # 对话管理信号
    new_conversation_signal = pyqtSignal()
    switch_conversation_signal = pyqtSignal(str)
    delete_conversation_signal = pyqtSignal(str)
    rename_conversation_signal = pyqtSignal(str, str)  # conversation_id, new_title
    
    # 消息编辑和删除信号
    edit_message_signal = pyqtSignal(int, str)  # bubble_index, new_content
    delete_message_signal = pyqtSignal(int)  # bubble_index
    
    # 设置信号
    settings_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Agent')
        
        # 设置窗口可以调整大小和最大化
        self.setMinimumSize(1200, 800)
        self.resize(1920, 1080)
        
        # 启用窗口最大化按钮并启动时最大化
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        
        # 使用QTimer延迟最大化，确保窗口完全初始化后再最大化
        QTimer.singleShot(100, self.showMaximized)
        
        # 聊天管理器引用（稍后设置）
        self.chat_manager = None
        
        # 初始化增强的主题管理器
        try:
            from enhanced_theme_manager import EnhancedThemeManager
            self.theme_manager = EnhancedThemeManager(self)
            print("✅ 使用增强主题管理器")
        except ImportError:
            from theme_manager import ThemeManager
            self.theme_manager = ThemeManager(self)
            print("⚠️ 使用标准主题管理器")
        
        self.theme_manager.set_main_window(self)
        
        # 深色模式蒙版（初始不可见）
        self.dark_overlay = None
        
        # 加载背景图片
        self.load_background()
        
        # 设置初始样式
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QPushButton { background: rgba(255,255,255,0.5); color: #222; font-size: 18px; border-radius: 10px; padding: 5px 10px; }
            QPushButton:pressed { background: rgba(255,255,255,0.7); border: 2px solid #555; }
        """)

        self.init_ui()
        self.connect_signals()
        
        # 应用保存的主题设置
        QTimer.singleShot(200, self.apply_saved_theme)

    def load_background(self):
        """加载背景图片"""
        try:
            self.bg_pixmap = QPixmap(BACKGROUND_PATH)
            if self.bg_pixmap.isNull():
                self.bg_pixmap = QPixmap(1920, 1080)
                self.bg_pixmap.fill(Qt.GlobalColor.white)
        except Exception as e:
            self.bg_pixmap = QPixmap(1920, 1080)
            self.bg_pixmap.fill(Qt.GlobalColor.white)

    def set_chat_manager(self, chat_manager):
        """设置聊天管理器引用"""
        self.chat_manager = chat_manager

    def init_ui(self):
        """初始化UI"""
        # 整体布局：水平分割
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 15)
        main_layout.setSpacing(10)

        # 创建侧边栏
        self.sidebar = Sidebar(self)
        main_layout.addWidget(self.sidebar)

        # 创建右侧容器（聊天区域 + 输入栏）
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)  # 改为垂直布局
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # 创建聊天区域
        self.chat_area = ChatArea(right_container)
        
        # 创建输入栏
        self.input_bar = InputBar(right_container)
        
        # 垂直布局：聊天区域在上，输入栏在下
        right_layout.addWidget(self.chat_area, 1)  # 聊天区域占据剩余空间
        right_layout.addWidget(self.input_bar)      # 输入栏固定在底部
        
        main_layout.addWidget(right_container, 1)

    def connect_signals(self):
        """连接信号"""
        # 侧边栏信号
        self.sidebar.new_conversation_signal.connect(self.new_conversation_signal.emit)
        self.sidebar.conversation_clicked.connect(self.switch_conversation_signal.emit)
        self.sidebar.delete_conversation_signal.connect(self.confirm_delete_conversation)
        self.sidebar.rename_conversation_signal.connect(self.show_rename_dialog)
        self.sidebar.settings_signal.connect(self.settings_signal.emit)
        
        # 输入栏信号
        self.input_bar.send_message_signal.connect(self.send_message_signal.emit)
        self.input_bar.prompt_signal.connect(self.prompt_signal.emit)
        self.input_bar.clear_history_signal.connect(self.clear_history_signal.emit)
        self.input_bar.cancel_request_signal.connect(self.cancel_request_signal.emit)  # 新增
        self.input_bar.search_text_signal.connect(self.show_search_dialog)  # 新增：搜索文本信号
        
        # 聊天区域信号
        self.chat_area.edit_message_signal.connect(self.edit_message_signal.emit)
        self.chat_area.delete_message_signal.connect(self.delete_message_signal.emit)
        
        # 主题管理器信号
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def confirm_delete_conversation(self, conv_id, conv_title):
        """删除对话确认"""
        if show_delete_confirmation(self, conv_title):
            print(f"用户确认删除对话: {conv_title} (ID: {conv_id})")
            self.delete_conversation_signal.emit(conv_id)

    def show_rename_dialog(self, conv_id, current_title):
        """显示重命名对话框"""
        dialog = RenameDialog(current_title, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.new_title:
            if dialog.new_title != current_title:
                self.rename_conversation_signal.emit(conv_id, dialog.new_title)
    
    def show_search_dialog(self):
        """显示搜索对话框"""
        from dialogs import SearchDialog
        
        # 检查是否有气泡和对话
        has_bubbles = len(self.chat_area.message_bubbles) > 0
        has_conversations = len(self.sidebar.current_conversation_items) > 0
        
        # 创建搜索对话框
        self.search_dialog = SearchDialog(self, has_bubbles, has_conversations)
        
        # 保存搜索相关状态
        self.search_matches = []
        self.search_text = ""
        
        # 连接搜索信号
        self.search_dialog.search_in_current_signal.connect(self.on_search_in_current)
        self.search_dialog.search_globally_signal.connect(self.on_search_globally)
        self.search_dialog.navigate_signal.connect(self.on_navigate_to_match)
        
        self.search_dialog.exec()
    
    def on_search_in_current(self, search_text):
        """在当前对话中搜索"""
        self.search_text = search_text
        self.search_matches = self.chat_area.search_text_in_current(search_text)
        
        if self.search_matches:
            # 找到匹配，更新对话框显示
            self.search_dialog.set_search_results(self.search_matches, 0)
            # 滚动到第一个匹配
            self.chat_area.scroll_to_bubble(self.search_matches[0], search_text)
        else:
            # 没有找到匹配
            self.search_dialog.set_search_results([], 0)
    
    def on_search_globally(self, search_text):
        """全局搜索（在所有对话中搜索）"""
        from PyQt6.QtWidgets import QMessageBox
        
        print(f"全局搜索: {search_text}")
        self.search_text = search_text
        
        # 检查是否有聊天管理器引用
        if not self.chat_manager:
            QMessageBox.warning(self, "错误", "无法访问聊天管理器")
            return
        
        # 调用聊天管理器的全局搜索方法
        found = self.chat_manager.search_text_globally(search_text)
        
        if found:
            # 找到匹配，获取当前对话的所有匹配结果
            self.search_matches = self.chat_area.search_text_in_current(search_text)
            if self.search_matches:
                self.search_dialog.set_search_results(self.search_matches, 0)
        else:
            # 没有找到匹配
            self.search_dialog.set_search_results([], 0)
    
    def on_navigate_to_match(self, index):
        """导航到指定索引的匹配结果"""
        if 0 <= index < len(self.search_matches):
            self.chat_area.scroll_to_bubble(self.search_matches[index], self.search_text)

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 检查是否按下了 Ctrl+F
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_search_dialog()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """绘制背景"""
        painter = QPainter(self)
        scaled_pixmap = self.bg_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(self.rect(), scaled_pixmap)
        
        # 如果启用深色模式，绘制灰色降亮度蒙版
        if self.theme_manager.dark_mode_enabled:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))  # 增强的半透明黑灰色蒙版，降低屏幕亮度

    def resizeEvent(self, event):
        """窗口大小改变时的处理"""
        super().resizeEvent(event)
        self.update()

    # 以下方法委托给相应的组件
    def add_user_bubble(self, user_text):
        self.chat_area.add_user_bubble(user_text)

    def add_thinking_bubble(self):
        return self.chat_area.add_thinking_bubble()

    def update_chat_display(self, reply_text):
        self.chat_area.update_chat_display(reply_text)
        
    def add_history_bubble(self, role, content):
        self.chat_area.add_history_bubble(role, content)

    def clear_chat_history_display(self):
        self.chat_area.clear_chat_history_display()
        # 强制更新整个窗口
        self.update()
        self.repaint()  # 强制重绘

    def update_conversation_list(self, conversations):
        self.sidebar.update_conversation_list(conversations)

    def set_current_conversation(self, conversation_id):
        self.sidebar.set_current_conversation(conversation_id)

    def update_conversation_title_in_list(self, conv_id, new_title):
        self.sidebar.update_conversation_title_in_list(conv_id, new_title)

    def closeEvent(self, event):
        """窗口关闭时的清理工作"""
        self.clear_chat_history_display()
        super().closeEvent(event)

    # 新增：输入栏状态控制方法
    def set_input_waiting_state(self):
        """设置输入栏为等待状态"""
        self.input_bar.set_waiting_state()
        
    def set_input_normal_state(self):
        """设置输入栏为正常状态"""
        self.input_bar.set_normal_state()
    
    def apply_saved_theme(self):
        """应用保存的主题设置"""
        if self.theme_manager:
            # 应用保存的主题
            if self.theme_manager.dark_mode_enabled:
                self.theme_manager.apply_theme()
            
            # 应用保存的背景
            if self.theme_manager.custom_background_path:
                self.theme_manager.apply_background()
    
    def on_theme_changed(self, dark_mode):
        """主题变化回调"""
        # 更新输入栏主题
        if hasattr(self, 'input_bar') and hasattr(self.input_bar, 'set_dark_mode'):
            self.input_bar.set_dark_mode(dark_mode)
        
        # 强制重绘以显示/隐藏蒙版
        self.update()
    
    def get_theme_manager(self):
        """获取主题管理器（供设置对话框使用）"""
        return self.theme_manager