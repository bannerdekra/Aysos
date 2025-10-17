import sys
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDialog
from PyQt6.QtGui import QPixmap, QPainter, QColor, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
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
        
        # 视频背景相关
        self.video_widget = None
        self.media_player = None
        self.audio_output = None
        self.is_video_background = False
        
        # 聊天管理器引用（稍后设置）
        self.chat_manager = None
        
        # 初始化增强的主题管理器
        try:
            from enhanced_theme_manager import EnhancedThemeManager
            self.theme_manager = EnhancedThemeManager(self)
            print("[OK] 使用增强主题管理器")
        except ImportError:
            from theme_manager import ThemeManager
            self.theme_manager = ThemeManager(self)
            print("[WARNING] 使用标准主题管理器")
        
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
        """加载背景图片或视频"""
        try:
            # 检查是否为视频文件
            if BACKGROUND_PATH.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.load_video_background(BACKGROUND_PATH)
            else:
                self.load_image_background(BACKGROUND_PATH)
        except Exception as e:
            print(f"加载背景失败: {e}")
            self.load_image_background(None)
    
    def load_image_background(self, path):
        """加载图片背景（只处理图片文件，视频文件自动跳过）"""
        self.is_video_background = False
        try:
            if path and os.path.exists(path):
                # 【关键修复】检查是否为视频文件，如果是则跳过
                video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
                if path.lower().endswith(video_extensions):
                    print(f"[背景] 跳过视频文件，不作为图片处理: {os.path.basename(path)}")
                    # 不设置背景，保持当前状态
                    return
                
                # 只处理图片文件
                self.bg_pixmap = QPixmap(path)
                if self.bg_pixmap.isNull():
                    print(f"无法加载背景图片: {path}")
                    self.bg_pixmap = QPixmap(1920, 1080)
                    self.bg_pixmap.fill(Qt.GlobalColor.white)
                else:
                    print(f"[背景] 图片背景加载成功: {os.path.basename(path)}")
            else:
                self.bg_pixmap = QPixmap(1920, 1080)
                self.bg_pixmap.fill(Qt.GlobalColor.white)
        except Exception as e:
            print(f"加载图片背景失败: {e}")
            self.bg_pixmap = QPixmap(1920, 1080)
            self.bg_pixmap.fill(Qt.GlobalColor.white)
    
    def load_video_background(self, path):
        """加载视频背景（入口方法，向后兼容）"""
        if not os.path.exists(path):
            print(f"[视频层] ❌ 视频文件不存在: {path}")
            self.load_image_background(None)
            return
        
        # 直接调用新的播放方法
        self.play_video_background(path)

    def play_video_background(self, video_path):
        """设置并开始播放视频背景（独立视频层架构）"""
        try:
            print(f"[视频层] 🎬 开始初始化视频播放层: {video_path}")
            
            # 【步骤1】初始化视频播放器组件（如果未创建）
            if not self.media_player:
                print("[视频层] 创建 QMediaPlayer")
                self.media_player = QMediaPlayer(self)
                self.audio_output = QAudioOutput(self)
                self.media_player.setAudioOutput(self.audio_output)
                self.media_player.setLoops(QMediaPlayer.Loops.Infinite)  # 循环播放
                
                # 连接状态信号用于调试
                self.media_player.playbackStateChanged.connect(
                    lambda state: print(f"[视频层] 播放状态: {state}")
                )
                self.media_player.errorOccurred.connect(
                    lambda error, errorString: print(f"[视频层] ❌ 播放错误: {error} - {errorString}")
                )
            
            # 【步骤2】初始化视频显示组件（如果未创建）
            if not self.video_widget:
                print("[视频层] 创建 QVideoWidget")
                self.video_widget = QVideoWidget(self)
                self.video_widget.setAccessibleName("VideoBackgroundLayer")
                self.video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 鼠标穿透
                self.media_player.setVideoOutput(self.video_widget)
            
            # 【步骤3】停止当前播放（如果有）
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                print("[视频层] 停止当前播放")
                self.media_player.stop()
            
            # 【步骤4】设置静音
            self.audio_output.setVolume(0)
            print("[视频层] 音频已静音")
            
            # 【步骤5】设置新的视频源
            video_url = QUrl.fromLocalFile(video_path)
            self.media_player.setSource(video_url)
            print(f"[视频层] 视频源已设置: {video_url.toString()}")
            
            # 【核心修复点A】立即清除主窗口的静态背景样式表，否则它会盖在视频上
            self.setStyleSheet("")
            print("[视频层] 🔧 主窗口样式表已清除（避免覆盖视频）")
            
            # 【步骤6】调整视频层的大小和位置（铺满整个窗口）
            self.video_widget.setGeometry(0, 0, self.width(), self.height())
            print(f"[视频层] 视频区域大小: {self.width()}x{self.height()}")
            
            # 【核心修复点B】确保视频组件在层级上低于所有前景 UI 组件
            self.video_widget.lower()
            self.video_widget.setVisible(True)
            self.video_widget.show()
            print("[视频层] 视频组件已显示并置于底层")
            
            # 【步骤8】清除静态背景（避免干扰）
            self.bg_pixmap = None
            print("[视频层] 静态背景已清除")
            
            # 【步骤9】开始播放
            self.media_player.play()
            print("[视频层] ✅ 播放命令已发送")
            
            # 【步骤10】标记为视频背景模式
            self.is_video_background = True
            
            print(f"[视频层] ✅ 视频背景播放初始化完成")
            print(f"[UI] 🎬 动态壁纸尝试播放: {video_path}")
            
        except Exception as e:
            print(f"[视频层] ❌ 播放视频背景失败: {e}")
            print(f"[UI] ❌ 播放动态壁纸失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 失败后清理
            if self.video_widget:
                self.video_widget.setVisible(False)
            self.is_video_background = False

    def stop_video_background(self):
        """停止播放视频背景并隐藏视频组件"""
        try:
            if self.media_player and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.stop()
                
            if self.video_widget:
                self.video_widget.setVisible(False)
                
            # 清理媒体源，释放资源
            if self.media_player:
                self.media_player.setSource(QUrl())
            
            self.is_video_background = False
            print("[UI] 🛑 动态壁纸已停止")
            
        except Exception as e:
            print(f"[UI] ⚠️ 停止动态壁纸时出错: {e}")

    def set_background_static(self, path):
        """设置静态图片背景（自动停止视频）"""
        # 【核心修复点C】确保设置静态背景时，视频组件被隐藏
        if self.is_video_background:
            print("[视频层] 切换到静态背景，停止视频播放")
            self.stop_video_background()
        
        if path and os.path.exists(path):
            print(f"[背景层] 加载静态图片: {path}")
            self.load_image_background(path)
            
            # 设置静态背景的样式表，注意路径转义
            image_path_escaped = path.replace(os.sep, '/')
            self.setStyleSheet(f"background-image: url('{image_path_escaped}');" + 
                             " background-repeat: no-repeat; background-position: center; border-radius: 10px;")
            print(f"[背景层] 静态背景样式已设置: {image_path_escaped}")
            
            self.update()
        else:
            # 【核心修复点C】清除所有背景样式
            print("[背景层] 清除所有背景样式")
            self.setStyleSheet("")
            self.bg_pixmap = QPixmap(1920, 1080)
            self.bg_pixmap.fill(Qt.GlobalColor.white)
            self.update()

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
        # 如果是视频背景，只绘制蒙版（如果需要）
        if self.is_video_background:
            if self.theme_manager.dark_mode_enabled:
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(0, 0, 0, 150))  # 深色模式蒙版
            return
        
        # 绘制图片背景
        painter = QPainter(self)
        scaled_pixmap = self.bg_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(self.rect(), scaled_pixmap)
        
        # 如果启用深色模式，绘制蒙版
        if self.theme_manager.dark_mode_enabled:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
    
    def resizeEvent(self, event):
        """窗口大小改变时调整视频背景和更新显示"""
        super().resizeEvent(event)
        
        # 【关键】调整视频层大小以铺满整个窗口
        if self.is_video_background and self.video_widget:
            new_size = self.size()
            self.video_widget.setGeometry(0, 0, new_size.width(), new_size.height())
            self.video_widget.lower()  # 确保在最底层
            print(f"[视频层] 窗口大小调整: {new_size.width()}x{new_size.height()}")
        
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