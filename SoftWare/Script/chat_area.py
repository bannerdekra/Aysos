import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
                              QSizePolicy, QApplication, QSpacerItem, QPushButton, QMessageBox)
from PyQt6.QtGui import QMovie, QFont, QFontMetrics, QTextDocument
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QTimer
from bubble_copy_handler import create_copyable_bubble_class, CopyButtonManager
from api_client import SPINNER_GIF_URL

def resource_path(relative_path):
    """获取正确的文件路径"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        current_file = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(os.path.dirname(current_file))
    
    full_path = os.path.join(base_path, relative_path)
    return full_path

class BubbleLabel(QLabel):
    def __init__(self, text, side='left', parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setText(text)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.side = side

# 创建带复制功能的气泡类
CopyableBubbleLabel = create_copyable_bubble_class(BubbleLabel)

class ClickableFileChip(QPushButton):
    """可点击的文件引用标签，显示在用户气泡下方"""
    def __init__(self, file_name, file_path, parent=None):
        super().__init__(f"📎 {file_name}", parent)
        self.file_name = file_name
        self.file_path = file_path
        self.setToolTip(f"点击预览文件\n路径: {file_path}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.on_click)
    
    def on_click(self):
        """点击文件标签时的处理"""
        # 检查文件是否存在
        if not os.path.exists(self.file_path):
            QMessageBox.warning(
                self,
                "文件不存在",
                f"文件已不在原路径:\n{self.file_path}\n\n文件可能已被移动或删除。",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # 文件存在，打开预览
        try:
            from dialogs import FilePreviewDialog
            preview = FilePreviewDialog(self.file_path, self.file_name, parent=self.window())
            preview.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "预览失败",
                f"无法预览文件:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

class ChatArea(QWidget):
    """聊天区域组件 - 双列布局"""
    edit_message_signal = pyqtSignal(int, str)  # bubble_index, new_content
    delete_message_signal = pyqtSignal(int)  # bubble_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.message_bubbles = []
        self.current_thinking_bubble_layout = None
        self.standard_font = QFont("Arial", 18)
        self.font_metrics = QFontMetrics(self.standard_font)
        self.char_width = self.font_metrics.averageCharWidth()
        
        # 高亮相关状态
        self.current_highlighted_bubble = None
        self.highlight_timer = None
        
        self.init_ui()
        # 绑定删除信号，确保一轮对话（用户+Agent）会一起删除
        self.delete_message_signal.connect(self.delete_dialog_by_index)
        
    def init_ui(self):
        """初始化双列聊天区域UI"""
        self.setStyleSheet("background: transparent; border-radius: 15px;")  # 改为全透明
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 主滚动区域 - 隐藏滚动条，滚动时显示
        self.scroll = QScrollArea(self)
        self.scroll.setStyleSheet('''
            QScrollArea { 
                background: transparent; 
                border: none; 
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        ''')
        
        self.scroll.setWidgetResizable(True)
        # 默认隐藏滚动条
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 主内容容器 - 单列垂直布局
        self.chat_content = QWidget()
        self.chat_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # 使用单个垂直布局管理所有消息行
        self.agent_layout = QVBoxLayout(self.chat_content)
        self.agent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.agent_layout.setSpacing(0)
        self.agent_layout.setContentsMargins(8, 8, 8, 8)
        
        # 保持向后兼容的引用
        self.agent_column = self.chat_content
        self.user_column = self.chat_content
        self.user_layout = self.agent_layout
        
        self.scroll.setWidget(self.chat_content)
        layout.addWidget(self.scroll, 1)
        
        # 添加滚动条显示/隐藏逻辑
        self._setup_scrollbar_behavior()
        
    def _setup_scrollbar_behavior(self):
        """设置滚动条行为：滚动时显示，停止后隐藏"""
        from PyQt6.QtCore import QTimer
        
        # 创建隐藏滚动条的定时器
        self.scrollbar_hide_timer = QTimer()
        self.scrollbar_hide_timer.timeout.connect(self._hide_scrollbars)
        self.scrollbar_hide_timer.setSingleShot(True)
        
        # 监听滚动事件
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        # 鼠标进入滚动区域时显示滚动条
        self.scroll.enterEvent = lambda event: self._on_scroll_area_enter(event)
        self.scroll.leaveEvent = lambda event: self._on_scroll_area_leave(event)
        
    def _on_scroll(self):
        """滚动时显示滚动条"""
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 重置隐藏定时器
        self.scrollbar_hide_timer.stop()
        self.scrollbar_hide_timer.start(1500)  # 1.5秒后隐藏
        
    def _on_scroll_area_enter(self, event):
        """鼠标进入滚动区域"""
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollbar_hide_timer.stop()
        
    def _on_scroll_area_leave(self, event):
        """鼠标离开滚动区域"""
        self.scrollbar_hide_timer.start(800)  # 0.8秒后隐藏
        
    def _scroll_to_bottom_precisely(self):
        """精确滚动到最后一个气泡底部，不超出内容范围"""
        QApplication.processEvents()  # 确保布局更新完成
        
        # 获取滚动区域的可见高度
        viewport_height = self.scroll.viewport().height()
        
        # 获取聊天内容的实际高度
        self.chat_content.adjustSize()  # 确保尺寸计算准确
        content_height = self.chat_content.height()
        
        # 如果内容高度小于或等于可见区域高度，不需要滚动
        if content_height <= viewport_height:
            self.scroll.verticalScrollBar().setValue(0)
            return
        
        # 计算理想滚动位置：内容高度减去可见高度
        ideal_scroll_pos = content_height - viewport_height
        
        # 获取滚动条的最大值，确保不超出
        max_scroll = self.scroll.verticalScrollBar().maximum()
        
        # 取两者的最小值，防止过度滚动
        final_scroll_pos = min(ideal_scroll_pos, max_scroll)
        final_scroll_pos = max(0, final_scroll_pos)  # 确保不为负数
        
        self.scroll.verticalScrollBar().setValue(final_scroll_pos)
        
    def _hide_scrollbars(self):
        """隐藏滚动条"""
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _preprocess_user_text(self, text):
        """预处理用户文本，约30个字符自动换行"""
        lines = []
        current_line = ""
        for char in text:
            current_line += char
            if len(current_line) >= 30 or char in ['\n', '\r']:
                lines.append(current_line.rstrip())
                current_line = ""
        
        if current_line:  # 添加最后一行
            lines.append(current_line)
            
        return '\n'.join(lines)
        
    def _calculate_bubble_width(self, text, side):
        """
        统一计算气泡宽度 - 修正单行文本计算
        """
        # 获取列宽并计算最大宽度
        available_width = max(100, (self.width() - 60) // 2)  # 单列可用宽度
        max_width = int(available_width * 0.85)
        
        # 适应短文本：计算单行文本宽度
        # 使用兼容性更好的方法测量文本宽度
        text_width = 0
        if hasattr(self.font_metrics, 'horizontalAdvance'):
            # 计算文本中最长一行的宽度
            lines = text.split('\n')
            for line in lines:
                line_width = self.font_metrics.horizontalAdvance(line)
                text_width = max(text_width, line_width)
        else:
            # 旧版本PyQt的fallback
            lines = text.split('\n')
            for line in lines:
                line_width = self.font_metrics.width(line)
                text_width = max(text_width, line_width)
        
        # 计算气泡所需宽度（文本宽度 + 内边距）
        padding = 40  # 增大内边距，确保文本不会太贴近边缘
        bubble_width = text_width + padding
        
        # 限制最大宽度
        if bubble_width > max_width:
            bubble_width = max_width
            
        # 确保最小宽度
        min_bubble_width = 100 if side == 'user' else 80
        return max(bubble_width, min_bubble_width)
    
    def _is_single_line_text(self, text):
        """判断文本是否为单行（不包含换行符）"""
        return '\n' not in text and '\r' not in text and len(text) < 50
    
    def add_user_bubble(self, user_text):
        """添加用户气泡 - 使用优化的布局系统：内容包裹优先，最大宽度限制"""
        # 创建消息行容器
        message_row = QWidget()
        message_row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row_layout = QHBoxLayout(message_row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(0)
        
        # 创建用户气泡标签
        user_bubble = CopyableBubbleLabel(user_text, side='right', parent=message_row)
        user_bubble.setWordWrap(True)
        max_width = int((self.width() - 32) * 0.6)
        user_bubble.setMaximumWidth(max_width)
        user_bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        if '\n' in user_text:
            user_bubble.setMinimumWidth(int(max_width * 0.95))
        bubble_index = len(self.message_bubbles)
        user_bubble.set_bubble_index(bubble_index)
        self.message_bubbles.append({
            'bubble': user_bubble,
            'role': 'user',
            'content': user_text,
            'container': message_row
        })
        user_bubble.setStyleSheet("""
            QLabel {
                background: rgb(50,205,50); 
                border-radius: 20px; 
                color: #222; 
                font-size: 18px; 
                padding: 12px 16px;
                margin: 4px;
            }
        """)
        left_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row_layout.addItem(left_spacer)
        row_layout.addWidget(user_bubble)

        self.agent_layout.addWidget(message_row)
        
        # 新增：在气泡下方显示临时文件引用
        temp_files = []
        try:
            # 获取父窗口的 input_bar
            parent_widget = self.parent()
            if parent_widget and hasattr(parent_widget, 'input_bar'):
                input_bar = parent_widget.input_bar
                if hasattr(input_bar, 'get_temporary_files'):
                    temp_files = input_bar.get_temporary_files()
                    print(f"[DEBUG] 获取到临时文件: {temp_files}")  # 调试信息
        except Exception as e:
            print(f"[ERROR] 获取临时文件失败: {e}")
        
        if temp_files:
            # 创建文件引用容器
            file_ref_container = QWidget()
            file_ref_layout = QHBoxLayout(file_ref_container)
            file_ref_layout.setContentsMargins(0, 2, 8, 4)  # 紧贴气泡
            file_ref_layout.setSpacing(6)
            
            # 左侧弹簧，使文件标签右对齐（与用户气泡对齐）
            file_ref_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            
            for file_path in temp_files:
                file_name = os.path.basename(file_path)
                # 截断长文件名
                if len(file_name) > 15:
                    display_name = file_name[:12] + "..."
                else:
                    display_name = file_name
                    
                # 创建可点击的文件标签（小标签，紧贴气泡）
                file_chip = ClickableFileChip(display_name, file_path, parent=file_ref_container)
                file_chip.setStyleSheet("""
                    QPushButton {
                        background: rgba(100, 100, 100, 0.2);
                        border: 1px solid rgba(100, 100, 100, 0.35);
                        border-radius: 8px;
                        color: #777;
                        font-size: 11px;
                        padding: 2px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: rgba(100, 100, 100, 0.3);
                        border-color: rgba(100, 100, 100, 0.5);
                        color: #555;
                    }
                """)
                file_ref_layout.addWidget(file_chip)
            
            self.agent_layout.addWidget(file_ref_container)

        spacer_item = QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.agent_layout.addItem(spacer_item)
        message_row.adjustSize()
        user_bubble.adjustSize()
        self.chat_content.update()
        self._scroll_to_bottom_precisely()

    def add_thinking_bubble(self):
        """添加思考动画 - 使用新的自适应布局系统"""
        # 创建思考动画行容器
        thinking_row = QWidget()
        thinking_row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row_layout = QHBoxLayout(thinking_row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(0)
        
        # 创建思考动画标签
        thinking_gif_label = QLabel(thinking_row)
        thinking_gif_label.setFixedSize(60, 60)
        gif_path = resource_path(SPINNER_GIF_URL)
        movie = QMovie(gif_path)
        movie.setScaledSize(thinking_gif_label.size())
        thinking_gif_label.setMovie(movie)
        movie.start()
        
        # 设置动画样式
        thinking_gif_label.setStyleSheet("""
            QLabel {
                background: rgba(30,144,255, 0.1);
                border-radius: 30px;
                margin: 4px;
            }
        """)
        
        # 左对齐思考动画
        row_layout.addWidget(thinking_gif_label)
        right_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row_layout.addItem(right_spacer)
        
        # 添加到主布局
        self.agent_layout.addWidget(thinking_row)
        
        # 添加间距
        spacer_item = QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.agent_layout.addItem(spacer_item)
        
        self._scroll_to_bottom_precisely()
        
        self.current_thinking_bubble = thinking_gif_label
        self.current_thinking_container = thinking_row
        return thinking_gif_label

    def remove_thinking_bubble(self):
        """移除思考动画及其容器"""
        if hasattr(self, 'current_thinking_container') and self.current_thinking_container:
            # 找到并移除思考动画容器及其后面的spacer
            for i in range(self.agent_layout.count()):
                item = self.agent_layout.itemAt(i)
                if item and item.widget() == self.current_thinking_container:
                    # 移除容器
                    item.widget().deleteLater()
                    self.agent_layout.takeAt(i)
                    
                    # 移除后面的spacer（如果存在）
                    if i < self.agent_layout.count():
                        next_item = self.agent_layout.itemAt(i)
                        if next_item and next_item.spacerItem():
                            self.agent_layout.takeAt(i)
                    break
            
            self.current_thinking_bubble = None
            self.current_thinking_container = None

    def update_chat_display(self, reply_text):
        """更新Agent回复 - 使用优化的布局系统：内容包裹优先，最大宽度限制"""        
        # 移除thinking动画
        self.remove_thinking_bubble()

        # 创建消息行容器
        message_row = QWidget()
        message_row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row_layout = QHBoxLayout(message_row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(0)
        agent_bubble = CopyableBubbleLabel(reply_text, side='left', parent=message_row)
        agent_bubble.setWordWrap(True)
        max_width = int((self.width() - 32) * 0.6)
        agent_bubble.setMaximumWidth(max_width)
        agent_bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        if '\n' in reply_text:
            agent_bubble.setMinimumWidth(int(max_width * 0.95))
        bubble_index = len(self.message_bubbles)
        agent_bubble.set_bubble_index(bubble_index)
        self.message_bubbles.append({
            'bubble': agent_bubble,
            'role': 'assistant',
            'content': reply_text,
            'container': message_row
        })
        agent_bubble.setStyleSheet("""
            QLabel {
                background: rgb(30,144,255); 
                border-radius: 20px; 
                color: #222; 
                font-size: 18px; 
                padding: 12px 16px;
                margin: 4px;
            }
        """)
        row_layout.addWidget(agent_bubble)
        # 新增：显示Agent引用的文件名（如有）
        if hasattr(self.parent(), 'input_bar'):
            persistent_files = self.parent().input_bar.get_persistent_files() if hasattr(self.parent().input_bar, 'get_persistent_files') else []
            if persistent_files:
                for file_info in persistent_files:
                    file_name = os.path.basename(file_info['path'])
                    file_label = QLabel(f"🔗 {file_name}", parent=message_row)
                    file_label.setStyleSheet("color: #555; font-size: 13px; margin-left: 24px; margin-bottom: 2px;")
                    row_layout.addWidget(file_label)
        right_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row_layout.addItem(right_spacer)
        self.agent_layout.addWidget(message_row)
        spacer_item = QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.agent_layout.addItem(spacer_item)
        message_row.adjustSize()
        agent_bubble.adjustSize()
        self.chat_content.update()
        self._scroll_to_bottom_precisely()
        self.current_thinking_bubble = None

    def add_history_bubble(self, role, content, file_paths=None):
        """添加历史记录气泡 - 使用优化的布局系统：内容包裹优先，最大宽度限制
        
        Args:
            role: 消息角色 ('user' 或 'assistant')
            content: 消息内容
            file_paths: 附件文件路径列表（可选）
        """
        # 标准化附件路径列表，兼容字符串或字典结构
        normalized_paths = []
        if file_paths:
            for file_entry in file_paths:
                if isinstance(file_entry, dict):
                    candidate = file_entry.get('path') or file_entry.get('local_path') or file_entry.get('uri')
                else:
                    candidate = str(file_entry)

                if candidate:
                    normalized_paths.append(candidate)

        file_paths = normalized_paths

        bubble_index = len(self.message_bubbles)
        
        # 创建消息行容器
        message_row = QWidget()
        message_row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row_layout = QHBoxLayout(message_row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(0)
        
        # 创建气泡标签
        bubble = CopyableBubbleLabel(content, side='right' if role == 'user' else 'left', parent=message_row)
        bubble.setWordWrap(True)
        
        # 设置气泡最大宽度为聊天区域宽度的60%
        max_width = int((self.width() - 32) * 0.6)  # 减去边距
        bubble.setMaximumWidth(max_width)
        
        # 关键：设置为Preferred策略以实现动态收缩
        bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        # 手动换行特殊处理
        if '\n' in content:
            # 包含换行符的文本，强制接近最大宽度
            bubble.setMinimumWidth(int(max_width * 0.95))
        
        bubble.set_bubble_index(bubble_index)
        
        if role == 'user':
            # 用户气泡样式和右对齐
            bubble.setStyleSheet("""
                QLabel {
                    background: rgb(50,205,50); 
                    border-radius: 20px; 
                    color: #222; 
                    font-size: 18px; 
                    padding: 12px 16px;
                    margin: 4px;
                }
            """)
            
            # 左侧弹簧 + 气泡 = 右对齐
            left_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            row_layout.addItem(left_spacer)
            row_layout.addWidget(bubble)
            
        else:
            # Agent气泡样式和左对齐
            bubble.setStyleSheet("""
                QLabel {
                    background: rgb(30,144,255); 
                    border-radius: 20px; 
                    color: #222; 
                    font-size: 18px; 
                    padding: 12px 16px;
                    margin: 4px;
                }
            """)
            
            # 气泡 + 右侧弹簧 = 左对齐
            row_layout.addWidget(bubble)
            right_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            row_layout.addItem(right_spacer)
        
        # 存储气泡信息
        self.message_bubbles.append({
            'bubble': bubble,
            'role': role,
            'content': content,
            'container': message_row,
            'files': file_paths
        })
        
        # 添加消息行到主布局
        self.agent_layout.addWidget(message_row)
        
        # 【修复Bug2】如果是用户消息且有附件，在气泡下方添加文件引用标签
        if role == 'user' and file_paths:
            # 创建文件引用容器
            file_ref_container = QWidget()
            file_ref_layout = QHBoxLayout(file_ref_container)
            file_ref_layout.setContentsMargins(0, 2, 8, 4)  # 紧贴气泡
            file_ref_layout.setSpacing(6)
            
            # 左侧弹簧，使文件标签右对齐（与用户气泡对齐）
            file_ref_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                # 截断长文件名
                if len(file_name) > 15:
                    display_name = file_name[:12] + "..."
                else:
                    display_name = file_name
                    
                # 创建可点击的文件标签（小标签，紧贴气泡）
                file_chip = ClickableFileChip(display_name, file_path, parent=file_ref_container)
                file_chip.setStyleSheet("""
                    QPushButton {
                        background: rgba(100, 100, 100, 0.2);
                        border: 1px solid rgba(100, 100, 100, 0.35);
                        border-radius: 8px;
                        color: #777;
                        font-size: 11px;
                        padding: 2px 8px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: rgba(100, 100, 100, 0.3);
                        border-color: rgba(100, 100, 100, 0.5);
                        color: #555;
                    }
                """)
                file_ref_layout.addWidget(file_chip)
            
            self.agent_layout.addWidget(file_ref_container)
        
        # 添加消息间间距
        spacer_item = QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.agent_layout.addItem(spacer_item)
        
        # 触发重新计算和重绘
        message_row.adjustSize()
        bubble.adjustSize()
        self.chat_content.update()
        
        self._scroll_to_bottom_precisely()

    def clear_chat_history_display(self):
        """清除聊天历史显示"""
        CopyButtonManager.get_instance().clear_all_buttons()
        self.message_bubbles.clear()
        
        # 重置思考气泡相关属性
        self.current_thinking_bubble = None
        self.current_thinking_bubble_layout = None
        
        # 停止滚动条隐藏定时器
        if hasattr(self, 'scrollbar_hide_timer'):
            self.scrollbar_hide_timer.stop()
        
        # 清空两列 - 使用更彻底的清理方法
        self._clear_layout_recursive(self.agent_layout)
        self._clear_layout_recursive(self.user_layout)
        
        # 强制更新布局
        self.agent_column.update()
        self.user_column.update()
        self.chat_content.update()
        
        # 重置滚动位置和滚动条状态
        self.scroll.verticalScrollBar().setValue(0)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 强制处理所有待处理的事件，确保UI完全更新
        QApplication.processEvents()
        
        print("聊天历史显示已清空")

    def resizeEvent(self, event):
        """窗口大小改变时重新计算气泡最大宽度"""
        super().resizeEvent(event)
        print(f"Chat area resized: {self.width()}x{self.height()}")

        # 重新计算所有气泡的最大宽度（60%规则）
        new_max_width = int((self.width() - 32) * 0.6)  # 减去边距
        
        if hasattr(self, 'message_bubbles'):
            for bubble_info in self.message_bubbles:
                if 'bubble' in bubble_info:
                    bubble = bubble_info['bubble']
                    content = bubble_info.get('content', '')
                    try:
                        bubble.setMaximumWidth(new_max_width)
                        
                        # 重新应用换行特殊处理
                        if '\n' in content:
                            bubble.setMinimumWidth(int(new_max_width * 0.95))
                        else:
                            bubble.setMinimumWidth(0)  # 重置最小宽度，允许收缩
                        
                        bubble.adjustSize()
                        
                        # 更新容器
                        if 'container' in bubble_info:
                            bubble_info['container'].adjustSize()
                            
                    except Exception as e:
                        print(f"重新计算气泡宽度失败: {e}")

        # 强制重新布局和重绘
        try:
            self.chat_content.adjustSize()
            self.chat_content.update()
            QApplication.processEvents()
        except Exception as e:
            print(f"强制重绘聊天区域失败: {e}")

    # 下面是新增的对话删除及辅助方法
    def delete_dialog_by_index(self, bubble_index: int):
        """移除指定气泡及其成对回复的UI显示。"""
        total = len(self.message_bubbles)
        if total == 0 or bubble_index < 0 or bubble_index >= total:
            print(f"删除信号索引无效: {bubble_index}")
            return

        indices_to_remove = []
        role = self.message_bubbles[bubble_index]['role']

        if role == 'user':
            indices_to_remove.append(bubble_index)
            if bubble_index + 1 < total and self.message_bubbles[bubble_index + 1]['role'] == 'assistant':
                indices_to_remove.append(bubble_index + 1)
        else:
            indices_to_remove.append(bubble_index)
            if bubble_index - 1 >= 0 and self.message_bubbles[bubble_index - 1]['role'] == 'user':
                indices_to_remove.insert(0, bubble_index - 1)

        # 从最大索引开始删除，避免下标偏移
        for idx in sorted(indices_to_remove, reverse=True):
            if 0 <= idx < len(self.message_bubbles):
                bubble_info = self.message_bubbles.pop(idx)
                container = bubble_info.get('container')
                if container:
                    self._remove_container_from_layout(container)

        self._reindex_bubbles()
        QApplication.processEvents()

    def _remove_container_from_layout(self, container):
        """从布局中移除指定的气泡容器及其后续间距。"""
        for i in range(self.agent_layout.count()):
            item = self.agent_layout.itemAt(i)
            if item and item.widget() == container:
                self.agent_layout.takeAt(i)
                container.deleteLater()

                # 移除后续的间距项
                if i < self.agent_layout.count():
                    next_item = self.agent_layout.itemAt(i)
                    if next_item and next_item.spacerItem():
                        self.agent_layout.takeAt(i)
                break

    # 原有的_remove_row_at和_delete_layout_item方法可以保留，
    # 但现在主要使用_remove_bubbles_from_ui进行更精确的删除
    def _remove_row_at(self, index: int):
        """从左右两列同时删除指定行（一条消息对应的两列项：气泡+间距和占位符+间距）"""
        # 每行实际上是两个项目：气泡/占位符 + 间距
        real_index = index * 2
        
        # 左列（Agent）- 删除气泡和间距
        if 0 <= real_index + 1 < self.agent_layout.count():
            # 删除气泡/占位符
            item = self.agent_layout.takeAt(real_index)
            self._delete_layout_item(item)
            # 删除间距
            item = self.agent_layout.takeAt(real_index)
            # 间距项无需特殊处理，直接丢弃
        
        # 右列（User）- 删除气泡和间距
        if 0 <= real_index + 1 < self.user_layout.count():
            # 删除气泡/占位符
            item = self.user_layout.takeAt(real_index)
            self._delete_layout_item(item)
            # 删除间距
            item = self.user_layout.takeAt(real_index)
            # 间距项无需特殊处理，直接丢弃

    def _delete_layout_item(self, item):
        """删除一个QLayoutItem（可能是widget或layout）"""
        if not item:
            return
        w = item.widget()
        if w is not None:
            w.deleteLater()
            return
        lay = item.layout()
        if lay is not None:
            self._clear_layout_recursive(lay)
            # Qt会接管内存，显式删除子项后由父布局管理释放
            return

    def _clear_layout_recursive(self, layout):
        """递归清空一个布局内的所有子项与子布局"""
        # 立即删除所有widget，避免异步删除导致的残留
        widgets_to_delete = []
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                widgets_to_delete.append(child.widget())
                child.widget().setParent(None)  # 立即从父级移除
            elif child.layout():
                self._clear_layout_recursive(child.layout())
        
        # 批量删除widgets
        for widget in widgets_to_delete:
            widget.deleteLater()
        
        # 强制处理事件，确保删除完成
        QApplication.processEvents()

    def _reindex_bubbles(self):
        """重新分配每个气泡的索引，保持与message_bubbles一致"""
        for i, info in enumerate(self.message_bubbles):
            bubble = info.get('bubble')
            if bubble and hasattr(bubble, 'set_bubble_index'):
                try:
                    bubble.set_bubble_index(i)
                except Exception:
                    pass
    
    def search_text_in_current(self, search_text):
        """在当前对话中搜索文本，返回所有匹配的气泡信息列表"""
        if not search_text or not self.message_bubbles:
            return []
        
        search_text_lower = search_text.lower()
        matches = []
        
        # 遍历所有气泡查找匹配的文本
        for bubble_info in self.message_bubbles:
            content = bubble_info.get('content', '')
            if search_text_lower in content.lower():
                # 找到匹配，添加到结果列表
                matches.append(bubble_info)
        
        return matches
    
    def scroll_to_bubble(self, bubble_info, search_text=None):
        """滚动到指定气泡并居中显示"""
        if not bubble_info or 'container' not in bubble_info:
            return False
        
        container = bubble_info['container']
        bubble = bubble_info['bubble']
        
        try:
            # 获取容器在聊天内容中的位置
            container_pos = container.pos()
            container_height = container.height()
            
            # 获取滚动区域的可见高度
            viewport_height = self.scroll.viewport().height()
            
            # 计算目标滚动位置（让气泡居中）
            target_scroll = container_pos.y() - (viewport_height - container_height) // 2
            
            # 确保滚动位置在有效范围内
            max_scroll = self.scroll.verticalScrollBar().maximum()
            target_scroll = max(0, min(target_scroll, max_scroll))
            
            # 平滑滚动到目标位置
            self.scroll.verticalScrollBar().setValue(target_scroll)
            
            # 高亮显示找到的气泡（临时改变背景色和文本高亮）
            self.highlight_bubble(bubble, search_text)
            
            return True
            
        except Exception as e:
            print(f"滚动到气泡失败: {e}")
            return False
    
    def highlight_bubble(self, bubble, search_text=None):
        """高亮显示气泡（临时改变背景色），并可选高亮匹配的文本"""
        try:
            # 如果有之前的高亮，立即清除
            if self.current_highlighted_bubble is not None:
                self.clear_current_highlight()
            
            # 如果有未完成的定时器，取消它
            if self.highlight_timer is not None:
                self.highlight_timer.stop()
                self.highlight_timer = None
            
            # 保存原始样式和文本
            original_style = bubble.styleSheet()
            original_text = bubble.text()
            
            # 保存当前高亮信息
            self.current_highlighted_bubble = {
                'bubble': bubble,
                'original_style': original_style,
                'original_text': original_text
            }
            
            # 如果提供了搜索文本，高亮显示匹配的文本
            if search_text:
                # 使用HTML高亮匹配的文本
                highlighted_text = self._highlight_text_in_html(original_text, search_text)
                bubble.setText(highlighted_text)
            
            # 应用高亮样式
            role = getattr(bubble, 'side', 'left')
            if role == 'right':  # 用户消息
                highlight_style = """
                    QLabel {
                        background: rgb(100, 255, 100); 
                        border-radius: 20px; 
                        color: #222; 
                        font-size: 18px; 
                        padding: 12px 16px;
                        margin: 4px;
                        border: 3px solid #FFA500;
                    }
                """
            else:  # Agent消息
                highlight_style = """
                    QLabel {
                        background: rgb(100, 200, 255); 
                        border-radius: 20px; 
                        color: #222; 
                        font-size: 18px; 
                        padding: 12px 16px;
                        margin: 4px;
                        border: 3px solid #FFA500;
                    }
                """
            
            bubble.setStyleSheet(highlight_style)
            
            # 创建新的定时器，3秒后恢复原始样式和文本
            self.highlight_timer = QTimer()
            self.highlight_timer.setSingleShot(True)
            self.highlight_timer.timeout.connect(self.clear_current_highlight)
            self.highlight_timer.start(3000)
            
        except Exception as e:
            print(f"高亮气泡失败: {e}")
    
    def clear_current_highlight(self):
        """清除当前的高亮显示"""
        if self.current_highlighted_bubble is not None:
            try:
                bubble = self.current_highlighted_bubble['bubble']
                original_style = self.current_highlighted_bubble['original_style']
                original_text = self.current_highlighted_bubble['original_text']
                
                bubble.setStyleSheet(original_style)
                bubble.setText(original_text)
            except Exception as e:
                print(f"清除高亮失败: {e}")
            finally:
                self.current_highlighted_bubble = None
    
    def _highlight_text_in_html(self, text, search_text):
        """在文本中高亮显示搜索关键词"""
        if not search_text:
            return text
        
        # 使用不区分大小写的替换
        import re
        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
        highlighted = pattern.sub(
            lambda m: f'<span style="background-color: yellow; color: black; font-weight: bold;">{m.group(0)}</span>',
            text
        )
        return highlighted
