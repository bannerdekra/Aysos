from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QMenu
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QAction
from dialogs import CustomPromptDialog

class InputBar(QWidget):
    """输入栏组件 - 支持主题感知"""
    send_message_signal = pyqtSignal(str)
    prompt_signal = pyqtSignal(str)
    clear_history_signal = pyqtSignal()
    cancel_request_signal = pyqtSignal()  # 新增：取消请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_prompt_action = None
        self.is_waiting_response = False  # 新增：是否在等待回复状态
        self.is_dark_mode = False  # 新增：深色模式状态
        self.init_ui()
        
    def init_ui(self):
        """初始化输入栏UI"""
        self.setFixedHeight(80)
        self.setStyleSheet("""
            background: rgba(255,255,255,0.25); 
            border-radius: 20px; 
            border: 2px solid rgba(255,255,255,0.3);
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 功能按钮
        self.features_btn = QPushButton('功能')
        self.features_btn.setFixedSize(70, 50)
        self.features_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(100, 149, 237, 0.8); 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 10px; 
                border: none;
            }
            QPushButton:pressed { 
                background: rgba(72, 118, 255, 0.9); 
            }
        """)
        self.features_btn.clicked.connect(self.show_features_menu)
        
        # 输入框
        self.input_line = QLineEdit()
        self.input_line.setFixedHeight(50)
        self.update_input_style()  # 使用主题感知的样式设置
        self.input_line.setPlaceholderText("请输入您的问题...")
        self.input_line.returnPressed.connect(self.on_send_clicked)

        # 发送按钮
        self.send_btn = QPushButton('发送')
        self.send_btn.setFixedSize(70, 50)
        self.send_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(34, 139, 34, 0.8); 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 10px; 
                border: none;
            }
            QPushButton:pressed { 
                background: rgba(0, 128, 0, 0.9); 
            }
        """)
        self.send_btn.clicked.connect(self.on_send_clicked)
        
        layout.addWidget(self.features_btn)
        layout.addWidget(self.input_line, 1)
        layout.addWidget(self.send_btn)
    
    def update_input_style(self):
        """根据主题模式更新输入框样式"""
        if self.is_dark_mode:
            # 深色模式：黑底白字
            self.input_line.setStyleSheet("""
                background: rgba(40, 40, 40, 0.95); 
                border: 2px solid rgba(100, 149, 237, 0.5); 
                color: white; 
                font-size: 16px; 
                border-radius: 12px; 
                padding: 8px 12px;
            """)
        else:
            # 浅色模式：白底黑字
            self.input_line.setStyleSheet("""
                background: rgba(255,255,255,0.9); 
                border: 2px solid rgba(100, 149, 237, 0.3); 
                color: #222; 
                font-size: 16px; 
                border-radius: 12px; 
                padding: 8px 12px;
            """)
    
    def set_dark_mode(self, enabled):
        """设置深色模式"""
        self.is_dark_mode = enabled
        self.update_input_style()
        print(f"🎨 输入栏主题更新: {'深色模式' if enabled else '浅色模式'}")
        
    def on_send_clicked(self):
        """发送按钮点击事件 - 增加状态处理"""
        if self.is_waiting_response:
            # 如果正在等待回复，点击则取消请求
            self.cancel_request_signal.emit()
            self.set_normal_state()
        else:
            # 正常发送消息
            user_input = self.input_line.text().strip()
            if user_input:
                self.send_message_signal.emit(user_input)
                self.input_line.clear()
                self.set_waiting_state()
    
    def set_waiting_state(self):
        """设置等待状态 - 按钮变蓝色，显示实心圆"""
        self.is_waiting_response = True
        self.send_btn.setText('●')  # 实心圆
        self.send_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(30, 144, 255, 0.8); 
                color: white; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 10px; 
                border: none;
            }
            QPushButton:hover { 
                background: rgba(30, 144, 255, 1.0); 
            }
            QPushButton:pressed { 
                background: rgba(0, 100, 200, 0.9); 
            }
        """)
        
    def set_normal_state(self):
        """设置正常状态 - 按钮变绿色，显示发送"""
        self.is_waiting_response = False
        self.send_btn.setText('发送')
        self.send_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(34, 139, 34, 0.8); 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 10px; 
                border: none;
            }
            QPushButton:pressed { 
                background: rgba(0, 128, 0, 0.9); 
            }
        """)

    def show_features_menu(self):
        """显示功能菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #ccc; border-radius: 5px; padding: 5px; }
            QMenu::item { padding: 8px 20px; color: black; }
            QMenu::item:selected { background-color: #e0e0e0; color: black; }
        """)
        
        prompt_menu = QMenu("提示词", self) 
        prompt_menu.setStyleSheet(menu.styleSheet())
        
        clear_history_action = QAction("清空聊天记录", self)
        clear_history_action.triggered.connect(self.clear_history_signal.emit)

        clear_action = QAction("清除提示词", self)
        clear_action.triggered.connect(lambda: self.on_prompt_action_triggered(None, "", False))

        concise_action = QAction("简洁", self)
        concise_action.setCheckable(True)
        concise_action.triggered.connect(lambda checked: self.on_prompt_action_triggered(concise_action, "请简洁地回答", checked))

        detailed_action = QAction("详细", self)
        detailed_action.setCheckable(True)
        detailed_action.triggered.connect(lambda checked: self.on_prompt_action_triggered(detailed_action, "请详细叙述", checked))

        custom_action = QAction("自定义", self)
        custom_action.triggered.connect(self.show_custom_prompt_dialog)
        
        if self.current_prompt_action and self.current_prompt_action.text() == "简洁":
            concise_action.setChecked(True)
        elif self.current_prompt_action and self.current_prompt_action.text() == "详细":
            detailed_action.setChecked(True)

        prompt_menu.addAction(concise_action)
        prompt_menu.addAction(detailed_action)
        prompt_menu.addAction(custom_action)
        prompt_menu.addAction(clear_action)
        
        menu.addMenu(prompt_menu)
        menu.addAction(clear_history_action)
        
        
        button_pos = self.features_btn.mapToGlobal(self.features_btn.rect().topLeft())
        menu_x = button_pos.x()
        menu_y = button_pos.y() - menu.sizeHint().height() - 5
        
        menu.exec(QPoint(menu_x, menu_y))

    def on_prompt_action_triggered(self, action, prompt_text, checked):
        """提示词动作触发"""
        if checked:
            if self.current_prompt_action and self.current_prompt_action != action:
                self.current_prompt_action.setChecked(False)
            self.prompt_signal.emit(f"({prompt_text})")
            self.current_prompt_action = action
        else:
            self.clear_prompt_selection()
            self.prompt_signal.emit("")

    def clear_prompt_selection(self):
        """清除提示词选择"""
        if self.current_prompt_action:
            self.current_prompt_action.setChecked(False)
        self.current_prompt_action = None
        print("提示词已清除。")

    def show_custom_prompt_dialog(self):
        """显示自定义提示词对话框"""
        self.clear_prompt_selection()
        dialog = CustomPromptDialog(self)
        if dialog.exec() == dialog.Accepted and dialog.prompt:
            self.prompt_signal.emit(f"({dialog.prompt})")

    def show_settings_dialog(self):
        """显示设置对话框"""
        from dialogs import SettingsDialog
        # 获取主窗口引用 - 遍历父级控件找到ChatWindow
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'theme_manager'):
            parent_widget = parent_widget.parent()
        
        if parent_widget and hasattr(parent_widget, 'theme_manager'):
            dialog = SettingsDialog(parent_widget)
        else:
            # 备用方案：使用window()方法
            main_window = self.window()
            dialog = SettingsDialog(main_window)
        dialog.exec()
