from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, 
                             QPushButton, QMenu, QFileDialog, QLabel, QFrame, QDialog)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QAction
from dialogs import CustomPromptDialog, FileModeDialog
from api_config import get_available_providers, get_current_provider_name, switch_provider
import os

class FileChip(QWidget):
    """文件标签组件 - 显示上传的文件，支持临时/持久两种模式"""
    remove_clicked = pyqtSignal(str, str)  # 文件路径, 文件ID（用于持久文件）
    preview_clicked = pyqtSignal(str)  # 文件路径（预览文件）
    
    def __init__(self, file_path, display_name, file_mode='temporary', file_id=None, parent=None):
        """
        Args:
            file_path: 文件路径
            display_name: 显示名称
            file_mode: 'temporary'(临时分析) 或 'persistent'(后续引用)
            file_id: Gemini服务器文件ID（仅持久文件需要）
        """
        super().__init__(parent)
        self.file_path = file_path
        self.display_name = display_name
        self.file_mode = file_mode
        self.file_id = file_id
        self.is_dark_mode = False
        self.init_ui()
        # 设置鼠标指针为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def init_ui(self):
        """初始化文件标签UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 4)
        layout.setSpacing(6)
        
        # 模式图标 - 放大
        mode_icon = "📄" if self.file_mode == 'temporary' else "🔗"
        self.mode_label = QLabel(mode_icon)
        self.mode_label.setStyleSheet("color: white; font-size: 14px;")
        
        # 文件名标签 - 放大
        self.name_label = QLabel(self.display_name)
        self.name_label.setStyleSheet("color: white; font-size: 14px; font-weight: 500;")
        
        # 删除按钮 - 放大
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ff6666;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path, self.file_id or ''))
        
        layout.addWidget(self.mode_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.remove_btn)
        
        self.update_style()
    
    def mousePressEvent(self, event):
        """鼠标点击事件 - 点击chip预览文件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击是否在删除按钮上
            if not self.remove_btn.geometry().contains(event.pos()):
                self.preview_clicked.emit(self.file_path)
        super().mousePressEvent(event)
    
    def update_style(self):
        """更新样式 - 临时文件蓝色，持久文件绿色，未上传灰色"""
        if self.file_mode == 'temporary':
            color = "rgba(74, 144, 226, 0.8)"  # 蓝色
        elif self.file_mode == 'persistent' and not self.file_id:
            color = "rgba(180, 180, 180, 0.7)"  # 灰色，未上传
        else:
            color = "rgba(80, 200, 120, 0.8)"  # 绿色
        self.setStyleSheet(f"""
            QWidget {{
                background: {color};
                border-radius: 12px;
                padding: 4px;
                min-height: 28px;
            }}
        """)
    
    def set_dark_mode(self, enabled):
        """设置深色模式"""
        self.is_dark_mode = enabled
        if enabled:
            if self.file_mode == 'temporary':
                color = "rgba(50, 100, 180, 0.9)"  # 深蓝色
            elif self.file_mode == 'persistent' and not self.file_id:
                color = "rgba(100, 100, 100, 0.8)"  # 深灰色
            else:
                color = "rgba(50, 150, 90, 0.9)"  # 深绿色
            self.setStyleSheet(f"""
                QWidget {{
                    background: {color};
                    border-radius: 12px;
                    padding: 4px;
                    min-height: 28px;
                }}
            """)
        else:
            self.update_style()


class FileContainer(QWidget):
    """文件容器 - 存放上传的文件标签"""
    file_deleted_signal = pyqtSignal(str)  # 当持久文件被删除时发出信号（file_id）
    file_preview_signal = pyqtSignal(str)  # 当点击文件chip时发出预览信号（file_path）
    
    def update_file_chip_id(self, file_path, file_id):
        """上传成功后补全chip的file_id并变色"""
        for chip in self.file_chips:
            if chip.file_path == file_path and chip.file_mode == 'persistent' and not chip.file_id:
                chip.file_id = file_id
                chip.update_style()
                break
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_chips = []  # 存储 FileChip 组件
        self.is_dark_mode = False
        self.init_ui()
    
    def init_ui(self):
        """初始化文件容器UI"""
        # 【样式说明】保持容器透明，让标签清晰可见
        self.setStyleSheet("background: transparent;")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)  # 标签间距
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    
    def add_file(self, file_path, file_mode='temporary', file_id=None):
        """
        添加文件
        
        Args:
            file_path: 文件路径
            file_mode: 'temporary' 或 'persistent'
            file_id: Gemini服务器文件ID（仅持久文件需要）
        """
        # 获取文件名（前10个字符）
        file_name = os.path.basename(file_path)
        if len(file_name) > 10:
            display_name = file_name[:10] + "..."
        else:
            display_name = file_name
        
        # 创建文件标签
        chip = FileChip(file_path, display_name, file_mode, file_id)
        chip.set_dark_mode(self.is_dark_mode)
        chip.remove_clicked.connect(self.remove_file)
        chip.preview_clicked.connect(self.file_preview_signal.emit)  # 连接预览信号
        
        self.file_chips.append(chip)
        self.layout.addWidget(chip)
    
    def remove_file(self, file_path, file_id):
        """移除文件"""
        for chip in self.file_chips:
            if chip.file_path == file_path:
                # 如果是持久文件，发出删除信号
                if chip.file_mode == 'persistent' and file_id:
                    self.file_deleted_signal.emit(file_id)
                
                self.file_chips.remove(chip)
                chip.deleteLater()
                break
    
    def get_files(self):
        """获取所有文件信息"""
        return [{
            'path': chip.file_path,
            'mode': chip.file_mode,
            'file_id': chip.file_id
        } for chip in self.file_chips]
    
    def get_temporary_files(self):
        """仅获取临时文件路径"""
        return [chip.file_path for chip in self.file_chips if chip.file_mode == 'temporary']
    
    def get_persistent_files(self):
        """仅获取持久文件信息"""
        return [{
            'path': chip.file_path,
            'file_id': chip.file_id
        } for chip in self.file_chips if chip.file_mode == 'persistent']
    
    def clear_temporary_files(self):
        """清空临时文件（发送成功后调用）"""
        temp_chips = [chip for chip in self.file_chips if chip.file_mode == 'temporary']
        for chip in temp_chips:
            self.file_chips.remove(chip)
            chip.deleteLater()
    
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
    def on_file_upload(self, file_path, file_id):
        """外部调用：持久文件上传成功后更新chip"""
        self.file_container.update_file_chip_id(file_path, file_id)
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
        main_layout.setSpacing(5)  # 【位置调整】增加间距让文件容器上移（数值越大，文件栏距离输入栏越远）
        
        # ========== 文件容器（附件栏）==========
        # 【位置调整说明】
        # 1. main_layout.setSpacing(5) - 控制文件栏与输入栏的距离（数值越大距离越远）
        # 2. setFixedHeight(30) - 控制文件栏高度（建议20-40之间）
        # 3. main_layout.addWidget() - 在输入栏之前添加，确保显示在上方
        self.file_container = FileContainer()
        self.file_container.setFixedHeight(40)  # 【位置调整】高度从20改为30，避免被遮挡
        # 连接文件删除信号，删除服务器上的持久文件
        self.file_container.file_deleted_signal.connect(self.on_server_file_deleted)
        # 连接文件预览信号
        self.file_container.file_preview_signal.connect(self.on_file_preview)
        main_layout.addWidget(self.file_container)
        
        # ========== 输入栏容器 ==========
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
        
        # 初始化时检查并设置上传按钮状态
        self.update_upload_button_state()
    
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
        """上传附件按钮点击事件 - 支持文件模式选择"""
        # 1. 选择文件
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        
        # 限制支持的文件类型（根据 Gemini API 文档）
        # 扩展支持视频格式: mp4, mov, mpeg, avi, webm
        file_dialog.setNameFilter(
            "支持的文件 (*.jpg *.jpeg *.png *.pdf *.webp *.heic *.heif *.mp4 *.mov *.mpeg *.avi *.webm);;"
            "图片文件 (*.jpg *.jpeg *.png *.webp *.heic *.heif);;"
            "文档文件 (*.pdf);;"
            "视频文件 (*.mp4 *.mov *.mpeg *.avi *.webm);;"
            "所有文件 (*.*)"
        )
        
        if not file_dialog.exec():
            return
        
        file_paths = file_dialog.selectedFiles()
        if not file_paths:
            return
        
        # 2. 为每个文件选择模式（临时分析 vs 后续引用）
        for file_path in file_paths:
            # 显示文件模式选择对话框
            mode_dialog = FileModeDialog(self)
            if mode_dialog.exec() == QDialog.DialogCode.Accepted:
                selected_mode = mode_dialog.get_selected_mode()
            else:
                selected_mode = None
            
            if not selected_mode:
                print(f"[WARNING] 用户取消选择文件模式: {file_path}")
                continue
            
            # 根据模式处理文件
            if selected_mode == 'temporary':
                # 临时分析：直接添加到容器，不上传到服务器
                self.file_container.add_file(file_path, file_mode='temporary')
                print(f"� 已添加临时文件: {file_path}")
            elif selected_mode == 'persistent':
                # 后续引用：先添加灰色chip，异步上传，成功后变绿色
                self.file_container.add_file(file_path, file_mode='persistent', file_id=None)
                print(f"[LINK] 持久文件chip已添加（灰色），开始上传: {file_path}")
                def upload_and_update():
                    try:
                        file_id = self._upload_file_to_gemini(file_path)
                        if file_id:
                            self.on_file_upload(file_path, file_id)
                            print(f"[OK] 持久文件已上传，ID: {file_id}")
                        else:
                            print(f"[ERROR] 文件上传失败: {file_path}")
                    except Exception as e:
                        print(f"[ERROR] 文件上传失败: {file_path}, 错误: {str(e)}")
                import threading
                threading.Thread(target=upload_and_update, daemon=True).start()
    
    def _upload_file_to_gemini(self, file_path: str) -> str:
        """
        上传文件到 Gemini 服务器（用于持久引用）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件ID（用于后续引用），失败返回空字符串
        """
        from gemini_context_manager import get_gemini_context_manager
        
        manager = get_gemini_context_manager()
        if not manager:
            print("[ERROR] 无法获取 Gemini 上下文管理器")
            return ""
        
        try:
            # 获取 MIME 类型
            mime_type = manager._get_mime_type(file_path)
            
            # 上传文件
            uploaded_file = manager._upload_file_to_gemini(file_path, mime_type)
            
            # 返回文件 ID（用于后续删除和引用）
            if hasattr(uploaded_file, 'name'):
                return uploaded_file.name
            else:
                print("[WARNING] 上传的文件没有 name 属性")
                return ""
                
        except Exception as e:
            print(f"[ERROR] 上传文件到 Gemini 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""
    
    def on_server_file_deleted(self, file_id: str):
        """
        处理持久文件删除事件 - 从服务器删除文件
        
        Args:
            file_id: Gemini服务器文件ID
        """
        from gemini_context_manager import get_gemini_context_manager
        
        manager = get_gemini_context_manager()
        if not manager:
            print("[ERROR] 无法获取 Gemini 上下文管理器")
            return
        
        # 从服务器删除文件
        manager.delete_server_file(file_id)
    
    def on_file_preview(self, file_path: str):
        """处理文件预览事件"""
        from dialogs import FilePreviewDialog
        
        if not os.path.exists(file_path):
            print(f"[WARNING] 文件不存在: {file_path}")
            return
        
        try:
            # 创建预览对话框
            preview_dialog = FilePreviewDialog(file_path, self)
            preview_dialog.exec()
        except Exception as e:
            print(f"[ERROR] 打开文件预览失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
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
                # 不立即清空文件容器，等待发送成功后再清除临时文件
                # 持久文件保留，临时文件在 on_send_success 中清除
                self.set_waiting_state()
    
    def on_send_success(self):
        """发送成功后的处理 - 不自动清除任何文件，让用户手动管理"""
        print("📤 消息发送成功")
        # 【用户需求】不自动清除任何文件，用户需要手动删除
        # self.file_container.clear_temporary_files()  # 已禁用自动清理
        self.set_normal_state()
    
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
                # 根据提供商启用/禁用附件上传
                self.update_upload_button_state(provider_id)
                print(f"已切换到模型: {provider_id}")
            else:
                print(f"切换到模型失败: {provider_id}")
        except Exception as e:
            print(f"切换模型时发生错误: {e}")
    
    def update_upload_button_state(self, provider_id=None):
        """根据提供商更新上传按钮状态"""
        if provider_id is None:
            provider_id = get_current_provider_name()
        
        # deepseek不支持附件上传，禁用按钮
        if provider_id == 'deepseek':
            self.upload_btn.setEnabled(False)
            self.upload_btn.setToolTip("DeepSeek模型不支持附件上传")
            self.upload_btn.setStyleSheet("""
                QPushButton { 
                    background: rgba(150, 150, 150, 0.5); 
                    color: rgba(255, 255, 255, 0.5); 
                    font-size: 24px; 
                    font-weight: bold;
                    border-radius: 10px; 
                    border: none;
                }
            """)
        else:
            self.upload_btn.setEnabled(True)
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

    def set_dark_mode(self, enabled):
        """设置深色模式 - 更新所有按钮样式"""
        self.is_dark_mode = enabled
        self.update_input_style()
        self.update_model_button_style()
        self.file_container.set_dark_mode(enabled)
        print(f"🎨 输入栏主题更新: {'深色模式' if enabled else '浅色模式'}")
