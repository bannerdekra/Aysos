from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

class ConversationListItem(QWidget):
    """对话列表项组件，支持悬停删除按钮和长标题滚动播放"""
    item_clicked = pyqtSignal(str)  # conversation_id
    delete_requested = pyqtSignal(str, str)  # conversation_id, title
    rename_requested = pyqtSignal(str, str)  # conversation_id, title
    
    def __init__(self, conv_id, title, is_current=False, parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self.title = title
        self.original_title = title  # 保存原始标题
        self.is_current = is_current
        self.is_hovered = False
        self.setObjectName("conversationItem")
        
        # 滚动播放相关属性
        self.max_display_length = 10  # 最大显示字符数（降低到10，确保更容易触发滚动）
        self.scroll_position = 0
        self.scroll_direction = 1
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.update_scroll)
        self.scroll_timer.setInterval(200)  # 200毫秒滚动一次（更快）
        
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 设置初始样式
        self.update_style()
        
        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # 对话标题标签 - 设置固定宽度确保按钮不被挤压
        self.title_label = QLabel()
        self.title_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
        self.title_label.setFixedWidth(160)  # 增加到160像素，给更多显示空间
        self.update_title_display()
        layout.addWidget(self.title_label)
        
        # 按钮容器 - 固定宽度确保始终可见
        button_container = QWidget()
        button_container.setFixedWidth(56)  # 两个按钮的宽度 + 间距
        button_container.setFixedHeight(24)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # 重命名按钮
        self.rename_btn = QPushButton("✏️")
        self.rename_btn.setFixedSize(20, 20)
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background: #2E7D32;
                color: white;
                border-radius: 10px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #1B5E20;
            }
            QToolTip {
                background-color: white;
                color: black;
                border: 1px solid #bdbdbd;
                padding: 4px 6px;
                font-size: 11px;
            }
        """)
        self.rename_btn.setToolTip("重命名")
        self.rename_btn.clicked.connect(self.on_rename_clicked)
        self.rename_btn.hide()
        button_layout.addWidget(self.rename_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: #C62828;
                color: white;
                border-radius: 10px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #8E0000;
            }
            QToolTip {
                background-color: white;
                color: black;
                border: 1px solid #bdbdbd;
                padding: 4px 6px;
                font-size: 11px;
            }
        """)
        self.delete_btn.setToolTip("删除")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        self.delete_btn.hide()
        button_layout.addWidget(self.delete_btn)
        
        layout.addWidget(button_container)

        # 初始化完成后刷新样式，确保标签样式同步
        self.update_style()
        
    def update_title_display(self):
        """更新标题显示，处理长标题的滚动播放"""
        if len(self.title) <= self.max_display_length:
            # 标题不长，直接显示
            self.title_label.setText(self.title)
            if self.scroll_timer.isActive():
                self.scroll_timer.stop()
        else:
            # 标题过长，需要滚动播放
            if self.is_hovered:
                # 鼠标悬停时启动滚动
                if not self.scroll_timer.isActive():
                    self.scroll_timer.start()
                    self.scroll_position = 0
                # 显示滚动后的文本
                display_text = self.get_scrolled_text()
                self.title_label.setText(display_text)
            else:
                # 非悬停状态，显示截断的标题
                truncated_title = self.title[:self.max_display_length] + "..."
                self.title_label.setText(truncated_title)
                if self.scroll_timer.isActive():
                    self.scroll_timer.stop()
    
    def get_scrolled_text(self):
        """获取滚动后的文本"""
        if len(self.title) <= self.max_display_length:
            return self.title
        
        # 创建滚动效果：在标题前后添加空格，形成循环滚动
        extended_title = self.title + "    "  # 添加间隔空格
        total_length = len(extended_title)
        
        # 计算显示的起始位置
        start_pos = self.scroll_position % total_length
        
        # 构造显示文本
        if start_pos + self.max_display_length <= total_length:
            display_text = extended_title[start_pos:start_pos + self.max_display_length]
        else:
            # 需要循环到开头
            part1 = extended_title[start_pos:]
            part2 = extended_title[:self.max_display_length - len(part1)]
            display_text = part1 + part2
        
        return display_text
    
    def update_scroll(self):
        """更新滚动位置"""
        self.scroll_position += 1
        self.update_title_display()
    
    def update_title(self, new_title):
        """更新标题显示"""
        self.title = new_title
        self.original_title = new_title
        self.scroll_position = 0  # 重置滚动位置
        self.update_title_display()
        
    def update_style(self):
        """更新样式"""
        label_style = "color: rgba(255, 255, 255, 0.9); font-size: 14px; background: transparent;"
        if self.is_current:
            # 当前对话样式（高亮显示）
            self.setStyleSheet("""
                #conversationItem {
                    background: #4CAF50;
                    border-radius: 6px;
                    margin: 2px 4px;
                    padding: 6px;
                    border: none;
                }
            """)
            label_style = "color: white; font-size: 14px; font-weight: bold; background: transparent;"
        elif self.is_hovered:
            # 悬停时的预选中样式
            self.setStyleSheet("""
                #conversationItem {
                    background: rgba(76, 175, 80, 0.25);
                    border-radius: 6px;
                    margin: 2px 4px;
                    padding: 6px;
                    border: 1px solid rgba(76, 175, 80, 0.3);
                }
            """)
            label_style = "color: #F0FFF0; font-size: 14px; background: transparent;"
        else:
            # 默认样式
            self.setStyleSheet("""
                #conversationItem {
                    background: transparent;
                    border-radius: 6px;
                    margin: 2px 4px;
                    padding: 6px;
                    border: 1px solid transparent;
                }
            """)
            label_style = "color: rgba(255, 255, 255, 0.85); font-size: 14px; background: transparent;"

        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(label_style)
    
    def set_current(self, is_current):
        """设置是否为当前对话"""
        self.is_current = is_current
        if self.is_current:
            self.rename_btn.show()
            self.delete_btn.show()
        elif not self.is_hovered:
            self.rename_btn.hide()
            self.delete_btn.hide()
        self.update_style()
        
    def on_delete_clicked(self):
        """删除按钮点击"""
        self.delete_requested.emit(self.conv_id, self.title)
        
    def on_rename_clicked(self):
        """重命名按钮点击"""
        self.rename_requested.emit(self.conv_id, self.title)
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.item_clicked.emit(self.conv_id)
        super().mousePressEvent(event)
        
    def enterEvent(self, event):
        """鼠标进入显示按钮和预选中效果，启动长标题滚动"""
        self.is_hovered = True
        if not self.is_current:  # 只有非当前对话才显示悬停效果
            self.update_style()
        self.rename_btn.show()
        self.delete_btn.show()
        
        # 启动标题滚动（如果标题过长）
        self.update_title_display()
        
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开隐藏按钮和预选中效果，停止长标题滚动"""
        self.is_hovered = False
        if not self.is_current:  # 只有非当前对话才取消悬停效果
            self.update_style()
            self.rename_btn.hide()
            self.delete_btn.hide()
        
        # 停止标题滚动
        self.update_title_display()
        
        super().leaveEvent(event)


class Sidebar(QWidget):
    """侧边栏组件"""
    new_conversation_signal = pyqtSignal()
    conversation_clicked = pyqtSignal(str)  # conversation_id
    delete_conversation_signal = pyqtSignal(str, str)  # conversation_id, title
    rename_conversation_signal = pyqtSignal(str, str)  # conversation_id, title
    settings_signal = pyqtSignal()  # 新增：设置信号
    refresh_conversations_signal = pyqtSignal()  # 新增：刷新对话列表信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_conversation_items = []
        self.current_active_id = None
        self.init_ui()
        
    def init_ui(self):
        """初始化侧边栏UI"""
        self.setFixedWidth(250)
        self.setStyleSheet("background: rgba(0, 0, 0, 0.4); border-radius: 10px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 新建对话按钮
        self.new_chat_button = QPushButton("➕ 新建对话", self)
        self.new_chat_button.setStyleSheet("""
            QPushButton { 
                background: rgba(0, 150, 0, 0.7); 
                color: white; 
                font-size: 14px; 
                border-radius: 8px; 
                padding: 8px; 
            }
            QPushButton:pressed { 
                background: rgba(0, 100, 0, 0.9); 
            }
        """)
        self.new_chat_button.clicked.connect(self.new_conversation_signal.emit)
        layout.addWidget(self.new_chat_button)

        # 对话列表滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.conversation_container = QWidget()
        self.conversation_layout = QVBoxLayout(self.conversation_container)
        self.conversation_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.conversation_layout.setSpacing(2)
        
        scroll_area.setWidget(self.conversation_container)
        layout.addWidget(scroll_area)
        
        # 刷新对话列表按钮
        self.refresh_button = QPushButton("🔄 刷新对话列表", self)
        self.refresh_button.setStyleSheet("""
            QPushButton { 
                background: rgba(255, 165, 0, 0.7); 
                color: white; 
                font-size: 14px; 
                border-radius: 8px; 
                padding: 8px; 
            }
            QPushButton:pressed { 
                background: rgba(255, 140, 0, 0.9); 
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_conversations_signal.emit)
        layout.addWidget(self.refresh_button)
        
        # 设置按钮
        self.settings_button = QPushButton("⚙️ 设置", self)
        self.settings_button.setStyleSheet("""
            QPushButton { 
                background: rgba(100, 149, 237, 0.7); 
                color: white; 
                font-size: 14px; 
                border-radius: 8px; 
                padding: 8px; 
            }
            QPushButton:pressed { 
                background: rgba(72, 118, 255, 0.9); 
            }
        """)
        self.settings_button.clicked.connect(self.settings_signal.emit)
        layout.addWidget(self.settings_button)
        
    def update_conversation_list(self, conversations):
        """更新对话列表"""
        # 清空现有项目 - 先断开信号连接
        for item in self.current_conversation_items:
            try:
                item.item_clicked.disconnect()
                item.delete_requested.disconnect()
                item.rename_requested.disconnect()
            except Exception:
                pass
            item.setParent(None)
            item.deleteLater()
        self.current_conversation_items.clear()

        # 添加新项目（只连接一次信号）
        for conv in conversations:
            if isinstance(conv, dict):
                conv_id = conv['id']
                title = conv['title']
            else:
                conv_id, title, _ = conv

            item_widget = ConversationListItem(conv_id, title, is_current=False)
            item_widget.item_clicked.connect(self.conversation_clicked.emit)
            item_widget.delete_requested.connect(self.delete_conversation_signal.emit)
            item_widget.rename_requested.connect(self.rename_conversation_signal.emit)

            self.conversation_layout.addWidget(item_widget)
            self.current_conversation_items.append(item_widget)

            if self.current_active_id is not None and conv_id == self.current_active_id:
                item_widget.set_current(True)
            else:
                item_widget.set_current(False)
    
    def set_current_conversation(self, conversation_id):
        """设置当前对话高亮"""
        self.current_active_id = conversation_id
        for item in self.current_conversation_items:
            is_current = (item.conv_id == conversation_id)
            item.set_current(is_current)
            
    def update_conversation_title_in_list(self, conv_id, new_title):
        """更新列表中特定对话的标题显示"""
        for item in self.current_conversation_items:
            if item.conv_id == conv_id:
                item.update_title(new_title)
                break
