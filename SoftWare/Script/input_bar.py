from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, 
                             QPushButton, QMenu, QFileDialog, QLabel, QFrame)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QAction
from dialogs import CustomPromptDialog
from api_config import get_available_providers, get_current_provider_name, switch_provider
import os

class FileChip(QWidget):
    """文件标签组件 - 显示上传的文件"""
    remove_clicked = pyqtSignal(str)  # 文件路径
    
    def __init__(self, file_path, display_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.display_name = display_name
        self.is_dark_mode = False
        self.init_ui()
    
    def init_ui(self):
        """初始化文件标签UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(5)
        
        # 文件名标签
        self.name_label = QLabel(self.display_name)
        self.name_label.setStyleSheet("color: white; font-size: 12px;")
        
        # 删除按钮
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(16, 16)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ff6666;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path))
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.remove_btn)
        
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        self.setStyleSheet("""
            QWidget {
                background: rgba(100, 149, 237, 0.6);
                border-radius: 10px;
                padding: 2px;
            }
        """)
    
    def set_dark_mode(self, enabled):
        """设置深色模式"""
        self.is_dark_mode = enabled
        if enabled:
            self.setStyleSheet("""
                QWidget {
                    background: rgba(70, 100, 180, 0.7);
                    border-radius: 10px;
                    padding: 2px;
                }
            """)
        else:
            self.update_style()


class FileContainer(QWidget):
    """文件容器 - 存放上传的文件标签"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_chips = []  # 存储 FileChip 组件
        self.is_dark_mode = False
        self.init_ui()
    
    def init_ui(self):
        """初始化文件容器UI"""
        self.setFixedHeight(20)
        self.setStyleSheet("background: transparent;")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    
    def add_file(self, file_path):
        """添加文件"""
        # 获取文件名（前10个字符）
        file_name = os.path.basename(file_path)
        if len(file_name) > 10:
            display_name = file_name[:10] + "..."
        else:
            display_name = file_name
        
        # 创建文件标签
        chip = FileChip(file_path, display_name)
        chip.set_dark_mode(self.is_dark_mode)
        chip.remove_clicked.connect(self.remove_file)
        
        self.file_chips.append(chip)
        self.layout.addWidget(chip)
    
    def remove_file(self, file_path):
        """移除文件"""
        for chip in self.file_chips:
            if chip.file_path == file_path:
                self.file_chips.remove(chip)
                chip.deleteLater()
                break
    
    def get_files(self):
        """获取所有文件路径"""
        return [chip.file_path for chip in self.file_chips]
    
    def clear_files(self):
        """清空所有文件"""
        for chip in self.file_chips:
            chip.deleteLater()
        self.file_chips.clear()
    
    def set_dark_mode(self, enabled):
        """设置深色模式"""
        self.is_dark_mode = enabled
        for chip in self.file_chips:
            chip.set_dark_mode(enabled)


class InputBar(QWidget):
    """输入栏组件 - 支持主题感知和文件上传"""
    send_message_signal = pyqtSignal(str, list)  # 消息内容, 文件列表
    prompt_signal = pyqtSignal(str)
    clear_history_signal = pyqtSignal()
    cancel_request_signal = pyqtSignal()
    model_changed_signal = pyqtSignal(str)
    search_text_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_prompt_action = None
        self.is_waiting_response = False
        self.is_dark_mode = False
        self.init_ui()
        
    def init_ui(self):
        """初始化输入栏UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 文件容器（20px高）
        self.file_container = FileContainer()
        main_layout.addWidget(self.file_container)
        
        # 输入栏容器
        input_widget = QWidget()
        input_widget.setFixedHeight(80)
        input_widget.setStyleSheet("""
            background: rgba(255,255,255,0.25); 
            border-radius: 20px; 
            border: 2px solid rgba(255,255,255,0.3);
        """)
        
        layout = QHBoxLayout(input_widget)
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
        
        # 模型选择按钮
        self.model_btn = QPushButton('模型')
        self.model_btn.setFixedSize(70, 50)
        self.update_model_button_text()
        self.update_model_button_style()
        self.model_btn.clicked.connect(self.show_model_menu)
        
        # 输入框
        self.input_line = QLineEdit()
        self.input_line.setFixedHeight(50)
        self.update_input_style()
        self.input_line.setPlaceholderText("请输入您的问题...")
        self.input_line.returnPressed.connect(self.on_send_clicked)

        # 上传附件按钮
        self.upload_btn = QPushButton('+')
        self.upload_btn.setFixedSize(50, 50)
        self.upload_btn.setToolTip("上传附件")
        self.upload_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(255, 165, 0, 0.8); 
                color: white; 
                font-size: 24px; 
                font-weight: bold;
                border-radius: 10px; 
                border: none;
            }
            QPushButton:hover { 
                background: rgba(255, 140, 0, 0.9); 
            }
            QPushButton:pressed { 
                background: rgba(255, 120, 0, 1.0); 
            }
        """)
        self.upload_btn.clicked.connect(self.on_upload_clicked)

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
        layout.addWidget(self.model_btn)
        layout.addWidget(self.input_line, 1)
        layout.addWidget(self.upload_btn)
        layout.addWidget(self.send_btn)
        
        main_layout.addWidget(input_widget)
    
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
    

    
    def on_upload_clicked(self):
        """上传附件按钮点击事件"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("所有文件 (*.*)")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.file_container.add_file(file_path)
                print(f"📎 已添加文件: {file_path}")
        
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
                # 获取所有上传的文件
                files = self.file_container.get_files()
                self.send_message_signal.emit(user_input, files)
                self.input_line.clear()
                # 清空文件容器
                self.file_container.clear_files()
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
        
        # 新增：搜索文本功能
        search_text_action = QAction("搜索文本", self)
        search_text_action.triggered.connect(self.show_search_dialog)

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
        menu.addAction(search_text_action)  # 添加搜索文本菜单项
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
    
    def show_search_dialog(self):
        """显示搜索对话框"""
        self.search_text_signal.emit()

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

    def update_model_button_text(self):
        """更新模型按钮显示的文本"""
        try:
            current_provider = get_current_provider_name()
            providers = get_available_providers()
            
            if current_provider in providers:
                display_name = providers[current_provider].get('display_name', current_provider)
                # 简化显示名称以适应按钮宽度
                if len(display_name) > 6:
                    display_name = display_name[:6]
                self.model_btn.setText(display_name)
            else:
                self.model_btn.setText('模型')
        except Exception as e:
            print(f"更新模型按钮文本失败: {e}")
            self.model_btn.setText('模型')

    def update_model_button_style(self):
        """根据主题更新模型按钮样式"""
        if self.is_dark_mode:
            # 深色模式
            style = """
                QPushButton { 
                    background: rgba(255, 165, 0, 0.8); 
                    color: white; 
                    font-size: 13px; 
                    font-weight: bold;
                    border-radius: 10px; 
                    border: none;
                }
                QPushButton:pressed { 
                    background: rgba(255, 140, 0, 0.9); 
                }
            """
        else:
            # 浅色模式
            style = """
                QPushButton { 
                    background: rgba(255, 165, 0, 0.8); 
                    color: white; 
                    font-size: 13px; 
                    font-weight: bold;
                    border-radius: 10px; 
                    border: none;
                }
                QPushButton:pressed { 
                    background: rgba(255, 140, 0, 0.9); 
                }
            """
        self.model_btn.setStyleSheet(style)

    def show_model_menu(self):
        """显示模型选择菜单"""
        try:
            current_provider = get_current_provider_name()
            providers = get_available_providers()
            
            menu = QMenu(self)
            
            # 应用深色模式样式
            if self.is_dark_mode:
                menu.setStyleSheet("""
                    QMenu {
                        background-color: rgba(40, 40, 40, 0.95);
                        color: white;
                        border: 1px solid rgba(255, 255, 255, 0.3);
                        border-radius: 8px;
                        padding: 4px;
                    }
                    QMenu::item {
                        background-color: transparent;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(100, 149, 237, 0.8);
                    }
                    QMenu::item:checked {
                        background-color: rgba(34, 139, 34, 0.8);
                        color: white;
                    }
                """)
            else:
                menu.setStyleSheet("""
                    QMenu {
                        background-color: rgba(255, 255, 255, 0.95);
                        color: black;
                        border: 1px solid rgba(0, 0, 0, 0.2);
                        border-radius: 8px;
                        padding: 4px;
                    }
                    QMenu::item {
                        background-color: transparent;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(100, 149, 237, 0.8);
                        color: white;
                    }
                    QMenu::item:checked {
                        background-color: rgba(34, 139, 34, 0.8);
                        color: white;
                    }
                """)
            
            # 为每个可用的提供商创建菜单项
            for provider_id, provider_info in providers.items():
                if provider_id != current_provider:  # 不显示当前正在使用的模型
                    display_name = provider_info.get('display_name', provider_id)
                    action = QAction(display_name, self)
                    action.setCheckable(False)
                    action.triggered.connect(lambda checked, pid=provider_id: self.switch_to_model(pid))
                    menu.addAction(action)
            
            if menu.actions():  # 只有当有其他模型可选时才显示菜单
                # 计算菜单显示位置（按钮上方）
                button_pos = self.model_btn.mapToGlobal(self.model_btn.rect().topLeft())
                menu_x = button_pos.x()
                menu_y = button_pos.y() - menu.sizeHint().height() - 5
                
                menu.exec(QPoint(menu_x, menu_y))
            else:
                print("没有其他可用的模型")
                
        except Exception as e:
            print(f"显示模型菜单失败: {e}")

    def switch_to_model(self, provider_id):
        """切换到指定的模型"""
        try:
            if switch_provider(provider_id):
                self.update_model_button_text()
                self.model_changed_signal.emit(provider_id)
                print(f"已切换到模型: {provider_id}")
            else:
                print(f"切换到模型失败: {provider_id}")
        except Exception as e:
            print(f"切换模型时发生错误: {e}")

    def set_dark_mode(self, enabled):
        """设置深色模式 - 更新所有按钮样式"""
        self.is_dark_mode = enabled
        self.update_input_style()
        self.update_model_button_style()
        self.file_container.set_dark_mode(enabled)
        print(f"🎨 输入栏主题更新: {'深色模式' if enabled else '浅色模式'}")
