import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QApplication, QSpacerItem
from PyQt6.QtGui import QMovie, QFont, QFontMetrics, QTextDocument
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
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
        
        # 主内容容器 - 水平布局分为两列
        self.chat_content = QWidget()
        main_chat_layout = QHBoxLayout(self.chat_content)
        main_chat_layout.setContentsMargins(0, 0, 0, 0)
        main_chat_layout.setSpacing(0)
        
        # 左列：Agent区域
        self.agent_column = QWidget()
        self.agent_column.setMinimumWidth(50)
        self.agent_layout = QVBoxLayout(self.agent_column)
        self.agent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # 移除spacing设置，我们会在每个气泡后添加垂直间距
        self.agent_layout.setSpacing(0)
        self.agent_layout.setContentsMargins(0, 0, 5, 0)
        
        # 右列：用户区域
        self.user_column = QWidget()
        self.user_column.setMinimumWidth(50)
        self.user_layout = QVBoxLayout(self.user_column)
        self.user_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        # 移除spacing设置，我们会在每个气泡后添加垂直间距
        self.user_layout.setSpacing(0)
        self.user_layout.setContentsMargins(0, 0, 0, 0)
        
        # 等宽分配
        main_chat_layout.addWidget(self.agent_column, 1)
        main_chat_layout.addWidget(self.user_column, 1)
        
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
        self.scroll.enterEvent = self._on_scroll_area_enter
        self.scroll.leaveEvent = self._on_scroll_area_leave
        
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
        """添加用户气泡到右列，并确保其始终右对齐"""
        # 创建用户气泡
        user_bubble = CopyableBubbleLabel(user_text, side='right', parent=self.user_column)
        
        # 判断单行文本居中显示，多行文本保持右对齐
        if self._is_single_line_text(user_text):
            user_bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            user_bubble.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            
        bubble_width = self._calculate_bubble_width(user_text, 'user')
        
        # 使用setFixedWidth来完全固定气泡的宽度
        user_bubble.setFixedWidth(bubble_width)
        
        # 设置气泡索引和存储
        bubble_index = len(self.message_bubbles)
        user_bubble.set_bubble_index(bubble_index)
        self.message_bubbles.append({
            'bubble': user_bubble,
            'role': 'user',
            'content': user_text,
            'column': 'user'
        })
        
        # 用户气泡样式
        user_bubble.setStyleSheet("""
            QLabel {
                background: rgb(50,205,50); 
                border-radius: 20px; 
                color: #222; 
                font-size: 18px; 
                padding: 10px 15px;
                min-height: 20px;
            }
        """)
        
        # 创建一个水平布局来包裹气泡，并用弹簧将其推到右侧
        bubble_container_layout = QHBoxLayout()
        bubble_container_layout.addStretch(1)  # 添加弹簧
        bubble_container_layout.addWidget(user_bubble)
        bubble_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.user_layout.addLayout(bubble_container_layout)
        
        # 在气泡下方添加固定高度的间距 (43px)
        spacer_item = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.user_layout.addSpacerItem(spacer_item)
        
        # 在左列添加占位符保持同步 - 使用气泡本身的高度
        spacer = QLabel()
        spacer.setFixedHeight(user_bubble.sizeHint().height())
        spacer.setStyleSheet("background: transparent;")
        self.agent_layout.addWidget(spacer)
        
        # 在左列占位符下方也添加同样的间距
        spacer_item2 = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.agent_layout.addSpacerItem(spacer_item2)
        
        self._scroll_to_bottom_precisely()

    def add_thinking_bubble(self):
        """添加思考动画到左列"""
        thinking_gif_label = QLabel(self.agent_column)
        thinking_gif_label.setFixedSize(60, 60)
        gif_path = resource_path(SPINNER_GIF_URL)
        movie = QMovie(gif_path)
        movie.setScaledSize(thinking_gif_label.size())
        thinking_gif_label.setMovie(movie)
        movie.start()
        
        thinking_gif_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.agent_layout.addWidget(thinking_gif_label)
        
        # 在思考动画下方添加固定高度的间距
        spacer_item = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.agent_layout.addSpacerItem(spacer_item)
        
        # 在右列添加占位符
        spacer = QLabel()
        spacer.setMinimumHeight(60)
        spacer.setStyleSheet("background: transparent;")
        self.user_layout.addWidget(spacer)
        
        # 在右列占位符下方也添加同样的间距
        spacer_item2 = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.user_layout.addSpacerItem(spacer_item2)
        
        self._scroll_to_bottom_precisely()
        
        self.current_thinking_bubble = thinking_gif_label
        return thinking_gif_label

    def remove_thinking_bubble(self):
        """手动移除thinking bubble及其相关spacers"""
        if hasattr(self, 'current_thinking_bubble') and self.current_thinking_bubble:
            # 找到并移除左侧的 thinking 动画及其后面的spacer
            thinking_index = -1
            for i in range(self.agent_layout.count()):
                item = self.agent_layout.itemAt(i)
                if item and item.widget() == self.current_thinking_bubble:
                    thinking_index = i
                    item.widget().deleteLater()
                    self.agent_layout.takeAt(i)
                    break
            
            # 移除thinking动画后面的spacer
            if thinking_index >= 0 and thinking_index < self.agent_layout.count():
                spacer_item = self.agent_layout.itemAt(thinking_index)
                if spacer_item and spacer_item.spacerItem():
                    self.agent_layout.takeAt(thinking_index)
            
            # 找到并移除右侧对应的占位符及其spacer
            user_spacer_index = -1
            for i in range(self.user_layout.count()):
                item = self.user_layout.itemAt(i)
                if item and item.widget() and item.widget().minimumHeight() == 60:
                    user_spacer_index = i
                    item.widget().deleteLater()
                    self.user_layout.takeAt(i)
                    break
            
            # 移除右侧占位符后面的spacer
            if user_spacer_index >= 0 and user_spacer_index < self.user_layout.count():
                spacer_item = self.user_layout.itemAt(user_spacer_index)
                if spacer_item and spacer_item.spacerItem():
                    self.user_layout.takeAt(user_spacer_index)
            
            self.current_thinking_bubble = None

    def update_chat_display(self, reply_text):
        """更新Agent回复到左列"""        
        # 移除thinking动画及其对应的spacer
        if hasattr(self, 'current_thinking_bubble') and self.current_thinking_bubble:
            # 找到并移除左侧的 thinking 动画及其后面的spacer
            thinking_index = -1
            for i in range(self.agent_layout.count()):
                item = self.agent_layout.itemAt(i)
                if item and item.widget() == self.current_thinking_bubble:
                    thinking_index = i
                    item.widget().deleteLater()
                    self.agent_layout.takeAt(i)
                    break
            
            # 移除thinking动画后面的spacer
            if thinking_index >= 0 and thinking_index < self.agent_layout.count():
                spacer_item = self.agent_layout.itemAt(thinking_index)
                if spacer_item and spacer_item.spacerItem():
                    self.agent_layout.takeAt(thinking_index)
            
            # 找到并移除右侧对应的占位符及其spacer
            user_spacer_index = -1
            for i in range(self.user_layout.count()):
                item = self.user_layout.itemAt(i)
                if item and item.widget() and item.widget().minimumHeight() == 60:
                    user_spacer_index = i
                    item.widget().deleteLater()
                    self.user_layout.takeAt(i)
                    break
            
            # 移除右侧占位符后面的spacer
            if user_spacer_index >= 0 and user_spacer_index < self.user_layout.count():
                spacer_item = self.user_layout.itemAt(user_spacer_index)
                if spacer_item and spacer_item.spacerItem():
                    self.user_layout.takeAt(user_spacer_index)

        # 创建Agent气泡
        agent_bubble = CopyableBubbleLabel(reply_text, side='left', parent=self.agent_column)
        
        # 判断单行文本居中显示，多行文本保持左对齐
        if self._is_single_line_text(reply_text):
            agent_bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            agent_bubble.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            
        bubble_width = self._calculate_bubble_width(reply_text, 'agent')
        
        agent_bubble.setFixedWidth(bubble_width)
        
        # 设置气泡索引和存储
        bubble_index = len(self.message_bubbles)
        agent_bubble.set_bubble_index(bubble_index)
        self.message_bubbles.append({
            'bubble': agent_bubble,
            'role': 'assistant',
            'content': reply_text,
            'column': 'agent'
        })
        
        # Agent气泡样式
        agent_bubble.setStyleSheet("""
            QLabel {
                background: rgb(30,144,255); 
                border-radius: 15px; 
                color: #222; 
                font-size: 18px; 
                padding: 8px 12px;
                min-height: 20px;
                white-space: pre-wrap;
            }
        """)
        
        self.agent_layout.addWidget(agent_bubble)
        
        # 在气泡下方添加固定高度的间距
        spacer_item = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.agent_layout.addSpacerItem(spacer_item)
        
        # 在右列添加占位符保持同步
        spacer = QLabel()
        spacer.setFixedHeight(agent_bubble.sizeHint().height())
        spacer.setStyleSheet("background: transparent;")
        self.user_layout.addWidget(spacer)
        
        # 在右列占位符下方也添加同样的间距
        spacer_item2 = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.user_layout.addSpacerItem(spacer_item2)
        
        self._scroll_to_bottom_precisely()
        self.current_thinking_bubble = None

    def add_history_bubble(self, role, content):
        """添加历史记录气泡到对应列，并确保用户气泡始终右对齐"""
        bubble_index = len(self.message_bubbles)
        
        if role == 'user':
            # 用户历史气泡到右列
            bubble = CopyableBubbleLabel(content, side='right', parent=self.user_column)
            
            # 判断单行文本居中显示，多行文本保持右对齐
            if self._is_single_line_text(content):
                bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                bubble.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
                
            bubble_width = self._calculate_bubble_width(content, 'user')
            
            bubble.setStyleSheet("""
                QLabel {
                    background: rgb(50,205,50); 
                    border-radius: 20px; 
                    color: #222; 
                    font-size: 18px; 
                    padding: 10px 15px;
                    min-height: 20px;
                }
            """)
            
            bubble.setFixedWidth(bubble_width)
            bubble.set_bubble_index(bubble_index)
            
            # 创建一个水平布局来包裹气泡，并用弹簧将其推到右侧
            bubble_container_layout = QHBoxLayout()
            bubble_container_layout.addStretch(1)
            bubble_container_layout.addWidget(bubble)
            bubble_container_layout.setContentsMargins(0, 0, 0, 0)
            
            self.user_layout.addLayout(bubble_container_layout)
            
            # 在用户气泡下方添加固定高度的间距
            spacer_item = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.user_layout.addSpacerItem(spacer_item)
            
            # 左列占位符 - 直接使用气泡的高度
            spacer = QLabel()
            spacer.setFixedHeight(bubble.sizeHint().height())
            spacer.setStyleSheet("background: transparent;")
            self.agent_layout.addWidget(spacer)
            
            # 在左列占位符下方也添加同样的间距
            spacer_item2 = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.agent_layout.addSpacerItem(spacer_item2)
            
        else:
            # Agent历史气泡到左列
            bubble = CopyableBubbleLabel(content, side='left', parent=self.agent_column)
            
            # 判断单行文本居中显示，多行文本保持左对齐
            if self._is_single_line_text(content):
                bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                bubble.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                
            bubble_width = self._calculate_bubble_width(content, 'agent')
            
            bubble.setStyleSheet("""
                QLabel {
                    background: rgb(30,144,255); 
                    border-radius: 15px; 
                    color: #222; 
                    font-size: 18px; 
                    padding: 8px 12px;
                    min-height: 20px;
                    white-space: pre-wrap;
                }
            """)
            
            bubble.setFixedWidth(bubble_width)
            bubble.set_bubble_index(bubble_index)
            
            self.agent_layout.addWidget(bubble)
            
            # 在AI气泡下方添加固定高度的间距
            spacer_item = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.agent_layout.addSpacerItem(spacer_item)
            
            # 右列占位符
            spacer = QLabel()
            spacer.setFixedHeight(bubble.sizeHint().height())
            spacer.setStyleSheet("background: transparent;")
            self.user_layout.addWidget(spacer)
            
            # 在右列占位符下方也添加同样的间距
            spacer_item2 = QSpacerItem(1, 43, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.user_layout.addSpacerItem(spacer_item2)
        
        self.message_bubbles.append({
            'bubble': bubble,
            'role': role,
            'content': content,
            'column': 'user' if role == 'user' else 'agent'
        })
        
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
        """窗口大小改变时的处理 - 保持气泡固定宽度"""
        super().resizeEvent(event)
        print(f"Chat area resized: {self.width()}x{self.height()}")

        # 注释掉重新计算气泡宽度的代码，确保气泡一旦创建就保持固定宽度
        # 这样可以防止第一句话的气泡在添加长文本后发生位置变化
        # if hasattr(self, 'message_bubbles'):
        #     for bubble_info in self.message_bubbles:
        #         if 'bubble' in bubble_info and 'content' in bubble_info:
        #             bubble = bubble_info['bubble']
        #             content = bubble_info['content']
        #             role = bubble_info.get('role', None)
        #
        #             try:
        #                 if role == 'user':
        #                     bubble_width = self._measure_user_text_size(content)
        #                 else:
        #                     bubble_width = self._measure_agent_text_size(content)
        #
        #                 bubble.setMaximumWidth(bubble_width)
        #                 bubble.updateGeometry()
        #             except Exception as e:
        #                 print(f"重新计算气泡宽度失败: {e}")

        # 只进行基本的重新布局，不改变气泡宽度
        try:
            self.chat_content.updateGeometry()
            QApplication.processEvents()
        except Exception as e:
            print(f"强制重绘聊天区域失败: {e}")

    # 下面是新增的对话删除及辅助方法
    def delete_dialog_by_index(self, bubble_index: int):
        """
        删除一轮对话（用户+Agent）。如果传入的是Agent气泡索引，则一并删除其前一个用户气泡。
        如果Agent尚未回复，仅删除用户气泡所在行。
        同步删除左右两列对应的项，更新内部索引。
        """
        print(f"删除气泡索引: {bubble_index}, 当前气泡总数: {len(self.message_bubbles)}")
        total = len(self.message_bubbles)
        if total == 0 or bubble_index < 0 or bubble_index >= total:
            return

        # 计算该轮对话的起始索引（用户在前，Agent在后）
        role = self.message_bubbles[bubble_index]['role']
        base = bubble_index if role == 'user' else max(0, bubble_index - 1)

        # 安全性：若base无效则返回
        if base < 0 or base >= len(self.message_bubbles):
            return

        # 判断是否存在成对的Agent应答
        has_pair = False
        if base + 1 < len(self.message_bubbles):
            r0 = self.message_bubbles[base]['role']
            r1 = self.message_bubbles[base + 1]['role']
            has_pair = (r0 == 'user' and r1 == 'assistant')

        # 记录要删除的消息对象，以便在UI和数据模型中都删除它们
        bubbles_to_delete = [self.message_bubbles[base]['bubble']]
        if has_pair and base + 1 < len(self.message_bubbles):
            bubbles_to_delete.append(self.message_bubbles[base + 1]['bubble'])
            
        # 从列表中删除这些对象
        self.message_bubbles.pop(base)
        if has_pair and base < len(self.message_bubbles):
            self.message_bubbles.pop(base)  # 因为已经删除了一个，所以索引不变
            
        # 从布局中删除对应项
        self._remove_bubbles_from_ui(bubbles_to_delete)

        # 重新编号剩余气泡
        self._reindex_bubbles()
        QApplication.processEvents()
        
    def _remove_bubbles_from_ui(self, bubbles):
        """从布局中删除指定的气泡"""
        print(f"开始删除气泡，总数: {len(bubbles)}")
        
        # 处理左列（Agent列）
        i = 0
        while i < self.agent_layout.count():
            item = self.agent_layout.itemAt(i)
            if not item:
                i += 1
                continue
                
            # 检查是否是要删除的气泡
            if item.widget() in bubbles:
                print(f"在Agent列找到要删除的气泡")
                item.widget().deleteLater()
                self.agent_layout.takeAt(i)
                if i < self.agent_layout.count():  # 确保还有项可以删除
                    self.agent_layout.takeAt(i)  # 删除间距项
                continue  # 不增加i，因为我们刚刚删除了项
            elif isinstance(item.widget(), QLabel) and "background: transparent" in item.widget().styleSheet():
                # 这是一个占位符，检查右侧对应的气泡是否在要删除列表中
                for j in range(self.user_layout.count()):
                    user_item = self.user_layout.itemAt(j)
                    if not user_item:
                        continue
                        
                    # 检查用户布局中的项
                    if user_item.layout():
                        for k in range(user_item.layout().count()):
                            layout_item = user_item.layout().itemAt(k)
                            if layout_item and layout_item.widget() in bubbles:
                                print(f"删除Agent列的占位符 (对应用户气泡)")
                                item.widget().deleteLater()
                                self.agent_layout.takeAt(i)
                                if i < self.agent_layout.count():
                                    self.agent_layout.takeAt(i)
                                break
                        else:
                            continue
                        break
                    elif user_item.widget() in bubbles:
                        print(f"删除Agent列的占位符 (对应用户气泡)")
                        item.widget().deleteLater()
                        self.agent_layout.takeAt(i)
                        if i < self.agent_layout.count():
                            self.agent_layout.takeAt(i)
                        break
                else:
                    i += 1
                    continue
                # 如果找到并删除了，不增加i
                continue
            i += 1
            
        # 处理右列（User列）- 完全重写这部分以确保可靠删除
        i = 0
        while i < self.user_layout.count():
            item = self.user_layout.itemAt(i)
            if not item:
                i += 1
                continue
                
            deleted = False
                
            # 处理布局（用户气泡通常包含在布局中）
            if item.layout():
                # 检查布局中的每个组件
                for j in range(item.layout().count()):
                    layout_item = item.layout().itemAt(j)
                    if not layout_item or not layout_item.widget():
                        continue
                        
                    if layout_item.widget() in bubbles:
                        print(f"在用户列布局中找到要删除的气泡")
                        # 找到了要删除的气泡，清理整个布局
                        self._clear_layout_recursive(item.layout())
                        self.user_layout.takeAt(i)
                        if i < self.user_layout.count():
                            self.user_layout.takeAt(i)  # 删除间距项
                        deleted = True
                        break
                
                if deleted:
                    continue  # 继续检查下一项
            
            # 处理直接的小部件（可能是占位符或其他）
            if item.widget():
                # 检查是否是要删除的气泡
                if item.widget() in bubbles:
                    print(f"在用户列中直接找到要删除的气泡")
                    item.widget().deleteLater()
                    self.user_layout.takeAt(i)
                    if i < self.user_layout.count():
                        self.user_layout.takeAt(i)  # 删除间距项
                    continue
                    
                # 检查是否是透明占位符（对应Agent气泡的占位符）
                if isinstance(item.widget(), QLabel) and "background: transparent" in item.widget().styleSheet():
                    # 这是占位符，检查左侧列是否有对应的要删除气泡
                    for j in range(self.agent_layout.count()):
                        agent_item = self.agent_layout.itemAt(j)
                        if agent_item and agent_item.widget() in bubbles:
                            print(f"删除用户列的占位符 (对应Agent气泡)")
                            item.widget().deleteLater()
                            self.user_layout.takeAt(i)
                            if i < self.user_layout.count():
                                self.user_layout.takeAt(i)
                            deleted = True
                            break
                            
                    if deleted:
                        continue
            
            # 如果没有删除任何东西，移到下一项
            i += 1
        
        print(f"气泡删除完成")

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
