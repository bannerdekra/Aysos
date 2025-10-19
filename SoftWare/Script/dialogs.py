from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QMessageBox, QWidget, QListWidget, QListWidgetItem, QCheckBox, 
                            QFileDialog, QFrame, QSizePolicy, QSpacerItem, QScrollArea, QApplication)
from PyQt6.QtCore import Qt, QTimer, QSize, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor
import os
import json
import datetime

from api_config import (
    load_api_config, 
    update_api_config, 
    mask_sensitive_value, 
    get_current_provider_name,
    get_current_provider_config,
    set_gemini_api_key
)

# 可选导入PIL
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class ChatConfigDialog(QDialog):
    """聊天记录配置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('聊天记录配置')
        self.setFixedSize(500, 500)
        self.config_result = None  # 'dsn', 'file', None
        
        self.apply_theme()

    def apply_theme(self):
        # 自动检测父窗口主题
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        self.setStyleSheet("background-color: %s; color: %s;" % ("#222" if is_dark else "white", "white" if is_dark else "black"))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("选择聊天记录存储方式：")
        title_label.setStyleSheet("color: black; font-size: 16px; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)
        
        # 配置DSN按钮
        self.dsn_button = QPushButton('配置DSN', self)
        self.dsn_button.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                border-radius: 6px; 
                # 已移除无效CSS和未闭合花括号
            }
        """)
        self.dsn_button.clicked.connect(self.choose_dsn)
        button_layout.addWidget(self.dsn_button)
        
        # 不使用DSN按钮
        self.file_button = QPushButton('不使用DSN（文件存储）', self)
        self.file_button.setStyleSheet("""
            QPushButton { 
                background-color: #2196F3; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                border-radius: 6px; 
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #1976D2; 
            }
        """)
        self.file_button.clicked.connect(self.choose_file)
        button_layout.addWidget(self.file_button)
        
        layout.addLayout(button_layout)
        
        # 取消按钮
        cancel_button = QPushButton('取消', self)
        cancel_button.setStyleSheet("""
            QPushButton { 
                background-color: #f44336; 
                color: white; 
                border: none; 
                padding: 8px 15px; 
                border-radius: 3px; 
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #da190b; 
            }
        """)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)
        
    def choose_dsn(self):
        self.config_result = 'dsn'
        self.accept()
        
    def choose_file(self):
        self.config_result = 'file'
        self.accept()
    
    def get_choice(self):
        """获取用户选择的结果"""
        return self.config_result

class DSNConfigDialog(QDialog):
    """DSN配置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('配置DSN名称')
        self.setFixedSize(400, 160)
        self.dsn_name = ''
        
        self.apply_theme()

    def apply_theme(self):
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        self.setStyleSheet("background-color: %s; color: %s;" % ("#222" if is_dark else "white", "white" if is_dark else "black"))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("配置DSN名称")
        title_label.setStyleSheet("color: black; font-size: 16px; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 输入框
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("请输入DSN名称...")
        self.line_edit.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; padding: 8px; font-size: 14px;")
        self.line_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.line_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定', self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton('取消', self)
        cancel_button.clicked.connect(self.reject)
        
        ok_button.setStyleSheet("""QPushButton { background-color: #4CAF50; color: white; border: none; padding: 8px 15px; border-radius: 3px; }QPushButton:hover { background-color: #45a049; }""")
        cancel_button.setStyleSheet("""QPushButton { background-color: #f44336; color: white; border: none; padding: 8px 15px; border-radius: 3px; }QPushButton:hover { background-color: #da190b; }""")

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        self.line_edit.setFocus()
        
    def accept(self):
        self.dsn_name = self.line_edit.text().strip()
        if self.dsn_name:
            super().accept()
        else:
            self.line_edit.setFocus()

def show_connection_result(parent, success, message):
    """显示连接结果对话框"""
    msg_box = QMessageBox(parent)
    if success:
        msg_box.setWindowTitle("连接成功")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(f"DSN连接成功！\n{message}")
    else:
        msg_box.setWindowTitle("连接失败")
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(f"DSN连接失败：\n{message}")
    
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    ok_button = msg_box.button(QMessageBox.StandardButton.Ok)
    ok_button.setText("确定")
    
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: white;
            color: black;
        }
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            padding: 5px 15px;
            border-radius: 3px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
    """)
    
    msg_box.exec()

class CustomPromptDialog(QDialog):
    """自定义提示词对话框"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('自定义提示词')
        self.setFixedSize(400, 100)
        self.prompt = ''
        
        self.apply_theme()

    def apply_theme(self):
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        self.setStyleSheet("background-color: %s; color: %s;" % ("#222" if is_dark else "white", "white" if is_dark else "black"))
        
        layout = QVBoxLayout(self)
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("请输入您的提示词...")
        self.line_edit.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc;")
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.line_edit)
        
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定', self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton('取消', self)
        cancel_button.clicked.connect(self.reject)
        
        ok_button.setStyleSheet("""QPushButton { background-color: #f0f0f0; border: 1px solid #bbb; }QPushButton:pressed { background-color: #e0e0e0; }""")
        cancel_button.setStyleSheet("""QPushButton { background-color: #f0f0f0; border: 1px solid #bbb; }QPushButton:pressed { background-color: #e0e0e0; }""")

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def accept(self):
        self.prompt = self.line_edit.text().strip()
        super().accept()

class RenameDialog(QDialog):
    """重命名对话框"""
    def __init__(self, current_title, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('重命名对话')
        self.setFixedSize(400, 150)
        self.new_title = ''
        self.current_title = current_title
        self.theme_manager = None
        if parent and hasattr(parent, 'theme_manager'):
            self.theme_manager = parent.theme_manager
        
        self.apply_theme()

    def apply_theme(self):
        is_dark = bool(self.theme_manager and getattr(self.theme_manager, 'dark_mode_enabled', False))
        dialog_bg = "#181818" if is_dark else "white"
        text_color = "#f0f0f0" if is_dark else "black"
        input_bg = "#222222" if is_dark else "white"
        input_border = "#333333" if is_dark else "#cccccc"
        button_bg_primary = "#2f2f2f" if is_dark else "#4CAF50"
        button_hover_primary = "#3a3a3a" if is_dark else "#45a049"
        button_bg_secondary = "#3a2b2b" if is_dark else "#f44336"
        button_hover_secondary = "#453333" if is_dark else "#da190b"

        self.setStyleSheet(f"background-color: {dialog_bg}; color: {text_color};")
        
        layout = QVBoxLayout(self)
        
        # 提示标签
        label = QLabel("请输入新的对话名称：")
        label.setStyleSheet(f"color: {text_color}; font-size: 14px; margin: 5px;")
        layout.addWidget(label)
        
        # 输入框
        self.line_edit = QLineEdit(self)
        self.line_edit.setText(self.current_title)
        self.line_edit.selectAll()  # 选中所有文本
        self.line_edit.setStyleSheet(
            f"background-color: {input_bg}; color: {text_color}; border: 1px solid {input_border}; padding: 5px; font-size: 14px;"
        )
        self.line_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.line_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定', self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton('取消', self)
        cancel_button.clicked.connect(self.reject)
        
        ok_button.setStyleSheet(
            f"""
            QPushButton {{ background-color: {button_bg_primary}; color: white; border: none; padding: 8px 15px; border-radius: 3px; }}
            QPushButton:hover {{ background-color: {button_hover_primary}; }}
        """
        )
        cancel_button.setStyleSheet(
            f"""
            QPushButton {{ background-color: {button_bg_secondary}; color: white; border: none; padding: 8px 15px; border-radius: 3px; }}
            QPushButton:hover {{ background-color: {button_hover_secondary}; }}
        """
        )

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        self.line_edit.setFocus()
        
    def accept(self):
        self.new_title = self.line_edit.text().strip()
        if self.new_title:
            super().accept()
        else:
            self.line_edit.setFocus()

def show_delete_confirmation(parent, conv_title):
    """显示删除确认对话框"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("确认删除")
    msg_box.setText("所有对话历史都将被清除且无法恢复\n确认删除该对话吗？")
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg_box.setDefaultButton(QMessageBox.StandardButton.No)
    
    # 设置按钮文本为中文
    yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
    yes_button.setText("确认删除")
    no_button = msg_box.button(QMessageBox.StandardButton.No)
    no_button.setText("取消")
    
    # 自动检测父窗口主题
    is_dark = False
    if parent and hasattr(parent, 'theme_manager'):
        is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: %s;
            color: %s;
        }
        QPushButton {
            background-color: %s;
            color: %s;
        }
        QPushButton:hover {
            background-color: %s;
        }
    """ % (
        "#222" if is_dark else "white",
        "white" if is_dark else "black",
        "#444" if is_dark else "#f0f0f0",
        "white" if is_dark else "black",
        "#333" if is_dark else "#e0e0e0"
    ))
    
    return msg_box.exec() == QMessageBox.StandardButton.Yes


class ToggleSwitch(QCheckBox):
    """自绘胶囊切换开关"""

    def __init__(self, parent=None, width=58, height=30, margin=3):
        super().__init__(parent)
        self._width = width
        self._height = height
        self._margin = margin
        self.setFixedSize(self._width, self._height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sizeHint(self):
        return QSize(self._width, self._height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_rect = QRectF(0, (self.height() - self._height) / 2, self._width, self._height)
        painter.setPen(Qt.PenStyle.NoPen)

        if self.isEnabled():
            track_color = QColor("#3DC06C") if self.isChecked() else QColor("#D8D8D8")
        else:
            track_color = QColor("#BEBEBE")

        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, self._height / 2, self._height / 2)

        knob_diameter = self._height - self._margin * 2
        if self.isChecked():
            knob_x = track_rect.right() - knob_diameter - self._margin
        else:
            knob_x = track_rect.left() + self._margin

        knob_rect = QRectF(knob_x, track_rect.top() + self._margin, knob_diameter, knob_diameter)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_rect)

        # 细边框与投影
        painter.setPen(QColor(0, 0, 0, 20))
        painter.drawEllipse(knob_rect)


class SettingsDialog(QDialog):
    """设置对话框 - 700x500大小，左右分区 2:3，包含聊天记录管理"""
    
    # 聊天记录配置信号
    chat_config_dsn_signal = pyqtSignal()
    chat_config_file_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('设置')
        self.setFixedSize(700, 500)
        self.setMinimumSize(700, 500)
        self.setMaximumSize(700, 500)
        # 禁用调整大小
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setObjectName('SettingsDialog')

        # 获取主题管理器
        self.theme_manager = None
        if hasattr(parent, 'get_theme_manager'):
            self.theme_manager = parent.get_theme_manager()
        elif hasattr(parent, 'theme_manager'):
            self.theme_manager = parent.theme_manager

        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self.on_theme_manager_dark_mode_changed)

        self.dark_mode_switch = None
        self.auto_mode_switch = None

        # API 配置状态
        self.api_key_value = ""
        self.api_url_value = ""
        self.api_model_value = ""
        self._suppress_api_events = False
        self._load_api_config()

        # UI 组件引用
        self.left_widget = None
        self.right_container = None

        self.init_ui()
        self.apply_base_theme_styles()

    def _load_api_config(self):
        config = load_api_config()
        self.api_key_value = config.get('api_key', '') or ""
        self.api_url_value = config.get('api_url', '') or ""
        self.api_model_value = config.get('model', '') or ""

    def _refresh_api_inputs(self):
        masked_key = mask_sensitive_value(self.api_key_value)
        masked_url = mask_sensitive_value(self.api_url_value)

        if hasattr(self, 'api_key_input') and self.api_key_input:
            self._suppress_api_events = True
            self.api_key_input.setText(masked_key)
            self.api_key_input.setCursorPosition(len(masked_key))
            self._suppress_api_events = False

        if hasattr(self, 'api_url_input') and self.api_url_input:
            self._suppress_api_events = True
            self.api_url_input.setText(masked_url)
            self.api_url_input.setCursorPosition(len(masked_url))
            self._suppress_api_events = False

    def is_dark_mode_enabled(self):
        if self.theme_manager:
            return bool(getattr(self.theme_manager, 'dark_mode_enabled', False))
        return False

    def get_theme_palette(self):
        if self.is_dark_mode_enabled():
            return {
                "dialog_bg": "#181818",
                "right_bg": "#181818",
                "left_bg": "#1f1f1f",
                "left_border": "#2a2a2a",
                "text_primary": "#f0f0f0",
                "text_secondary": "#b3b3b3",
                "text_muted": "#909090",
                "divider": "#2a2a2a",
                "card_bg": "#1f1f1f",
                "card_alt_bg": "#1d1d1d",
                "card_border": "#2d2d2d",
                "button_bg": "#2b2b2b",
                "button_text": "#f5f5f5",
                "button_border": "#3a3a3a",
                "button_hover": "#343434",
                "highlight": "#3a3a3a",
                "highlight_text": "#ffffff",
                "highlight_hover": "#2e2e2e",
                "input_bg": "#222222",
                "input_border": "#333333",
                "accent_success": {"bg": "#2f2f2f", "hover": "#393939", "text": "#f5f5f5"},
                "accent_info": {"bg": "#2f2f2f", "hover": "#3b3b3b", "text": "#f5f5f5"},
                "accent_warning": {"bg": "#34302a", "hover": "#3f3932", "text": "#f5f5f5"},
            }
        return {
            "dialog_bg": "#ffffff",
            "right_bg": "#ffffff",
            "left_bg": "#f5f5f5",
            "left_border": "#dddddd",
            "text_primary": "#333333",
            "text_secondary": "#666666",
            "text_muted": "#888888",
            "divider": "#dddddd",
            "card_bg": "#fdfdfd",
            "card_alt_bg": "#f9f9f9",
            "card_border": "#e4e4e4",
            "button_bg": "#f7f7f7",
            "button_text": "#333333",
            "button_border": "#cccccc",
            "button_hover": "#e0e0e0",
            "highlight": "#4CAF50",
            "highlight_text": "#ffffff",
            "highlight_hover": "#e0e0e0",
            "input_bg": "#ffffff",
            "input_border": "#cccccc",
            "accent_success": {"bg": "#4CAF50", "hover": "#45a049", "text": "#ffffff"},
            "accent_info": {"bg": "#2196F3", "hover": "#1976D2", "text": "#ffffff"},
            "accent_warning": {"bg": "#FF9800", "hover": "#F57C00", "text": "#ffffff"},
        }

    def build_button_style(self, *, padding="10px 15px", radius=6, font_size="13px", bold=False, accent=None):
        palette = self.get_theme_palette()
        accent_colors = None
        if accent == "success":
            accent_colors = palette["accent_success"]
        elif accent == "info":
            accent_colors = palette["accent_info"]
        elif accent == "warning":
            accent_colors = palette["accent_warning"]

        if accent_colors and not self.is_dark_mode_enabled():
            bg = accent_colors["bg"]
            hover = accent_colors["hover"]
            text_color = accent_colors["text"]
            border = "none"
        else:
            bg = palette["button_bg"]
            hover = palette["button_hover"]
            text_color = palette["button_text"]
            border = f"1px solid {palette['button_border']}"

        font_weight = "font-weight: bold;" if bold else ""

        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: {border};
                padding: {padding};
                border-radius: {radius}px;
                font-size: {font_size};
                {font_weight}
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """

    def apply_base_theme_styles(self):
        palette = self.get_theme_palette()
        self.setStyleSheet(f"""
            QDialog#SettingsDialog {{
                background-color: {palette['dialog_bg']};
                color: {palette['text_primary']};
            }}
            QDialog#SettingsDialog QLabel {{
                color: {palette['text_primary']};
            }}
        """)

        if self.left_widget:
            self.left_widget.setStyleSheet(f"background-color: {palette['left_bg']}; border-right: 1px solid {palette['left_border']};")

        if self.parent_list:
            self.parent_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: transparent;
                    border: none;
                    font-size: 14px;
                }}
                QListWidget::item {{
                    padding: 12px;
                    border-bottom: 1px solid {palette['divider']};
                    color: {palette['text_primary']};
                }}
                QListWidget::item:selected {{
                    background-color: {palette['highlight']};
                    color: {palette['highlight_text']};
                }}
                QListWidget::item:hover {{
                    background-color: {palette['highlight_hover']};
                }}
            """)

        if self.right_widget:
            self.right_widget.setStyleSheet(f"background-color: {palette['right_bg']};")

        if self.right_container:
            self.right_container.setStyleSheet(f"background-color: {palette['right_bg']};")

        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: {palette['right_bg']};
                }}
                QScrollArea > QWidget > QWidget {{
                    background-color: {palette['right_bg']};
                }}
            """)
        
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左区域（父项功能） - 宽度比例 2
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(200)  # 700 * 2/7 = 200
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # 父项列表
        self.parent_list = QListWidget()
        
        # 添加父项 - 确保不重复添加
        self.parent_list.clear()  # 先清空列表防止重复
        general_item = QListWidgetItem("通用设置")
        chat_record_item = QListWidgetItem("聊天记录管理")  # 新增聊天记录管理父项
        api_item = QListWidgetItem("API")
        self.parent_list.addItem(general_item)
        self.parent_list.addItem(chat_record_item)
        self.parent_list.addItem(api_item)
        self.parent_list.currentItemChanged.connect(self.on_parent_item_changed)
        
        left_layout.addWidget(self.parent_list)
        
        # 右区域（子项功能） - 宽度比例 3，添加滚动区域
        self.right_container = QWidget()
        self.right_container.setFixedWidth(500)  # 700 * 3/7 = 300
        
        # 创建滚动区域
        self.scroll_area = QScrollArea(self.right_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 滚动内容容器
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(15, 15, 15, 15)
        
        # 将内容容器放入滚动区域
        self.scroll_area.setWidget(self.right_widget)
        
        # 右侧容器布局
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.scroll_area)
        
        layout.addWidget(self.left_widget)
        layout.addWidget(self.right_container)
        
        # 初始化显示第一个父项的子项 - 在布局完成后进行
        QTimer.singleShot(100, self.init_default_view)
    
    def init_default_view(self):
        """初始化默认视图 - 显示第一个父项的子项"""
        print("初始化默认视图...")
        
        if self.parent_list.count() > 0:
            # 设置第一项为选中状态
            self.parent_list.setCurrentRow(0)

            # 如果信号尚未渲染内容，主动触发一次
            if self.right_layout and self.right_layout.count() == 0:
                current_item = self.parent_list.currentItem()
                if current_item:
                    self.switch_to_parent_content(current_item.text())

            print("默认视图初始化完成")
        else:
            print("警告: 父项列表为空")
    
    def on_parent_item_changed(self, current, previous):
        """父项切换事件 - 改进的切换逻辑"""
        if current is None:
            print("父项切换: current为None，跳过处理")
            return
        
        current_text = current.text()
        previous_text = previous.text() if previous else "None"
        print(f"父项切换: {previous_text} -> {current_text}")
        
        # 防止重复调用
        if previous and current_text == previous_text:
            print("重复调用，跳过处理")
            return
        
        # 立即显示对应的子项内容，无需清空和延迟
        self.switch_to_parent_content(current_text)
        
    def switch_to_parent_content(self, parent_name):
        """切换到指定父项的内容"""
        print(f"立即切换到: {parent_name}")
        
        # 清空当前内容
        self.clear_right_area()
        
        # 立即显示对应内容，不使用延迟
        if parent_name == "通用设置":
            self.show_general_settings()
        elif parent_name == "聊天记录管理":
            self.show_chat_record_settings()
        elif parent_name == "API":
            self.show_api_settings()
        else:
            print(f"未知的父项: {parent_name}")
        
        # 强制更新UI
        if hasattr(self, 'right_widget') and self.right_widget:
            self.right_widget.update()
        if hasattr(self, 'scroll_area') and self.scroll_area:
            self.scroll_area.update()
        QApplication.processEvents()
    
    def clear_right_area(self):
        """清空右区域 - 安全版本"""
        if self.right_layout is None:
            print("警告: right_layout 不存在，跳过清理")
            return
            
        initial_count = self.right_layout.count()
        if initial_count == 0:
            print("右区域已经为空，跳过清理")
            return
            
        print(f"清理右区域，当前有 {initial_count} 个组件")
        
        # 安全地清理所有组件
        try:
            while self.right_layout.count() > 0:
                item = self.right_layout.takeAt(0)
                if item and item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                    widget.deleteLater()
            print("右区域清理完成")
        except Exception as e:
            print(f"清理过程中发生错误: {e}")
            # 如果清理失败，保持当前布局并记录错误
            pass

        if hasattr(self, 'dark_mode_switch'):
            self.dark_mode_switch = None
        if hasattr(self, 'auto_mode_switch'):
            self.auto_mode_switch = None
    
    def show_general_settings(self):
        """显示通用设置子项"""
        print("=== 开始显示通用设置 ===")
        
        # 检查布局是否存在
        if self.right_layout is None:
            print("错误: right_layout 不存在，无法显示通用设置")
            return
        
        # 确保内容区域干净
        if self.right_layout.count() > 0:
            self.clear_right_area()

        # 重置控件引用，避免使用过期组件
        self.dark_mode_switch = None
        self.auto_mode_switch = None

        palette = self.get_theme_palette()

        # 标题
        title_label = QLabel("通用设置")
        title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 10px;"
        )
        self.right_layout.addWidget(title_label)
        print("✓ 已添加通用设置标题")

        # 深色模式与自动模式配置
        dark_mode_frame = QFrame()
        dark_mode_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_bg']};"
        )
        dark_mode_layout = QVBoxLayout(dark_mode_frame)
        dark_mode_layout.setSpacing(12)

        # 深色模式开关行
        dark_toggle_row = QHBoxLayout()
        dark_toggle_row.setContentsMargins(0, 0, 0, 0)

        dark_mode_label = QLabel("深色模式")
        dark_mode_label.setStyleSheet(
            f"font-size: 14px; color: {palette['text_primary']};"
        )
        dark_toggle_row.addWidget(dark_mode_label)
        dark_toggle_row.addStretch()

        self.dark_mode_switch = ToggleSwitch()
        if self.theme_manager:
            self.dark_mode_switch.setChecked(self.theme_manager.dark_mode_enabled)

        self.dark_mode_switch.toggled.connect(self.on_dark_mode_toggled)

        dark_toggle_row.addWidget(self.dark_mode_switch)
        dark_mode_layout.addLayout(dark_toggle_row)

        dark_mode_hint = QLabel("启用后界面将使用深色主题，适合低光环境。")
        dark_mode_hint.setStyleSheet(
            f"font-size: 12px; color: {palette['text_muted']};"
        )
        dark_mode_hint.setWordWrap(True)
        dark_mode_layout.addWidget(dark_mode_hint)

        # 自动模式开关行
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)

        mode_label = QLabel("跟随系统时间自动切换")
        mode_label.setStyleSheet(
            f"font-size: 14px; color: {palette['text_primary']};"
        )
        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()

        self.auto_mode_switch = ToggleSwitch()
        if self.theme_manager:
            self.auto_mode_switch.setChecked(self.theme_manager.auto_dark_mode)

        self.auto_mode_switch.toggled.connect(self.on_auto_mode_toggled)

        mode_layout.addWidget(self.auto_mode_switch)

        dark_mode_layout.addLayout(mode_layout)

        auto_mode_hint = QLabel("开启后将根据系统时间自动切换深浅色主题。")
        auto_mode_hint.setStyleSheet(
            f"font-size: 12px; color: {palette['text_muted']};"
        )
        auto_mode_hint.setWordWrap(True)
        dark_mode_layout.addWidget(auto_mode_hint)

        self.right_layout.addWidget(dark_mode_frame)

        # 自定义背景设置
        bg_frame = QFrame()
        bg_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_bg']};"
        )
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setSpacing(10)
        
        bg_label = QLabel("自定义背景")
        bg_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {palette['text_primary']};"
        )
        bg_layout.addWidget(bg_label)
        
        self.bg_path_button = QPushButton("选择背景路径")
        self.bg_path_button.setStyleSheet(
            self.build_button_style(padding="8px 15px", radius=4, font_size="12px", accent="info")
        )
        self.bg_path_button.clicked.connect(self.choose_background)
        bg_layout.addWidget(self.bg_path_button)
        
        # 显示当前背景路径
        self.bg_path_label = QLabel("未选择背景")
        self.bg_path_label.setStyleSheet(
            f"font-size: 11px; color: {palette['text_secondary']}; margin-top: 5px;"
        )
        self.bg_path_label.setWordWrap(True)
        
        # 设置当前背景状态
        if self.theme_manager and self.theme_manager.custom_background_path:
            # 判断背景类型
            bg_type = "视频" if self.theme_manager.is_video_background else "图片"
            self.bg_path_label.setText(f"已选择: {os.path.basename(self.theme_manager.custom_background_path)} ({bg_type})")
            
        bg_layout.addWidget(self.bg_path_label)
        
        self.right_layout.addWidget(bg_frame)
        
        # 文本折叠设置
        collapse_frame = QFrame()
        collapse_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_bg']};"
        )
        collapse_layout = QVBoxLayout(collapse_frame)
        collapse_layout.setSpacing(10)
        
        collapse_label = QLabel("长文本折叠设置")
        collapse_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {palette['text_primary']};"
        )
        collapse_layout.addWidget(collapse_label)
        
        collapse_hint = QLabel("当 Agent 回复超过设定字符数时，自动显示展开/收起按钮")
        collapse_hint.setStyleSheet(
            f"font-size: 12px; color: {palette['text_muted']};"
        )
        collapse_hint.setWordWrap(True)
        collapse_layout.addWidget(collapse_hint)
        
        # 阈值输入框
        threshold_row = QHBoxLayout()
        threshold_label = QLabel("折叠阈值（字符数）:")
        threshold_label.setStyleSheet(
            f"font-size: 13px; color: {palette['text_primary']};"
        )
        threshold_row.addWidget(threshold_label)
        
        from PyQt6.QtWidgets import QSpinBox
        self.collapse_threshold_spinbox = QSpinBox()
        self.collapse_threshold_spinbox.setMinimum(100)
        self.collapse_threshold_spinbox.setMaximum(5000)
        self.collapse_threshold_spinbox.setSingleStep(50)
        self.collapse_threshold_spinbox.setValue(self.load_collapse_threshold())
        self.collapse_threshold_spinbox.valueChanged.connect(self.save_collapse_threshold)
        self.collapse_threshold_spinbox.setStyleSheet(
            f"QSpinBox {{ background: {palette['input_bg']}; border: 1px solid {palette['input_border']}; padding: 6px; border-radius: 4px; color: {palette['text_primary']}; }}"
        )
        threshold_row.addWidget(self.collapse_threshold_spinbox)
        threshold_row.addStretch()
        
        collapse_layout.addLayout(threshold_row)
        
        # 预览长度输入框
        preview_row = QHBoxLayout()
        preview_label = QLabel("收起时显示字符数:")
        preview_label.setStyleSheet(
            f"font-size: 13px; color: {palette['text_primary']};"
        )
        preview_row.addWidget(preview_label)
        
        self.preview_length_spinbox = QSpinBox()
        self.preview_length_spinbox.setMinimum(50)
        self.preview_length_spinbox.setMaximum(1000)
        self.preview_length_spinbox.setSingleStep(50)
        self.preview_length_spinbox.setValue(self.load_preview_length())
        self.preview_length_spinbox.valueChanged.connect(self.save_preview_length)
        self.preview_length_spinbox.setStyleSheet(
            f"QSpinBox {{ background: {palette['input_bg']}; border: 1px solid {palette['input_border']}; padding: 6px; border-radius: 4px; color: {palette['text_primary']}; }}"
        )
        preview_row.addWidget(self.preview_length_spinbox)
        preview_row.addStretch()
        
        collapse_layout.addLayout(preview_row)
        
        self.right_layout.addWidget(collapse_frame)
        
        # 添加弹性空间
        self.right_layout.addStretch()

        print("=== 通用设置界面构建完成 ===")
    
    def show_chat_record_settings(self):
        """显示聊天记录管理子项"""
        print("=== 开始显示聊天记录管理 ===")
        
        # 检查布局是否存在
        if self.right_layout is None:
            print("错误: right_layout 不存在，无法显示聊天记录管理")
            return
        
        palette = self.get_theme_palette()

        # 标题
        title_label = QLabel("聊天记录管理")
        title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 15px;"
        )
        self.right_layout.addWidget(title_label)
        
        # 存储方式选择
        storage_frame = QFrame()
        storage_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_bg']};"
        )
        storage_layout = QVBoxLayout(storage_frame)
        storage_layout.setSpacing(12)
        
        storage_label = QLabel("存储方式选择")
        storage_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 8px;"
        )
        storage_layout.addWidget(storage_label)
        
        # DSN数据库存储按钮
        self.dsn_config_button = QPushButton("🗄️ 配置DSN数据库存储")
        self.dsn_config_button.setStyleSheet(
            self.build_button_style(padding="10px 15px", radius=6, font_size="13px", bold=True, accent="success")
        )
        self.dsn_config_button.clicked.connect(self.handle_dsn_config)
        storage_layout.addWidget(self.dsn_config_button)
        
        dsn_hint = QLabel("使用数据库存储聊天记录，支持高性能查询和云端同步。")
        dsn_hint.setStyleSheet(
            f"font-size: 11px; color: {palette['text_secondary']}; margin-left: 10px;"
        )
        storage_layout.addWidget(dsn_hint)
        
        # 文件存储按钮
        self.file_config_button = QPushButton("📁 使用本地文件存储")
        self.file_config_button.setStyleSheet(
            self.build_button_style(padding="10px 15px", radius=6, font_size="13px", bold=True, accent="info")
        )
        self.file_config_button.clicked.connect(self.handle_file_config)
        storage_layout.addWidget(self.file_config_button)
        
        file_hint = QLabel("使用本地文件存储聊天记录，简单方便，无需配置数据库。")
        file_hint.setStyleSheet(
            f"font-size: 11px; color: {palette['text_secondary']}; margin-left: 10px;"
        )
        storage_layout.addWidget(file_hint)
        
        self.right_layout.addWidget(storage_frame)
        
        # 存储状态显示
        status_frame = QFrame()
        status_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_alt_bg']};"
        )
        status_layout = QVBoxLayout(status_frame)
        
        status_label = QLabel("当前存储状态")
        status_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 8px;"
        )
        status_layout.addWidget(status_label)
        
        self.storage_status_label = QLabel("正在检测存储配置...")
        self.storage_status_label.setStyleSheet(
            f"font-size: 12px; color: {palette['text_secondary']}; padding: 5px;"
        )
        status_layout.addWidget(self.storage_status_label)
        
        # 更新存储状态显示
        self.update_storage_status()
        
        self.right_layout.addWidget(status_frame)
        
        # 数据管理操作
        manage_frame = QFrame()
        manage_frame.setStyleSheet(
            f"border: 1px solid {palette['card_border']}; border-radius: 8px; padding: 14px; margin: 8px 0; background-color: {palette['card_bg']};"
        )
        manage_layout = QVBoxLayout(manage_frame)
        
        manage_label = QLabel("数据管理操作")
        manage_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 8px;"
        )
        manage_layout.addWidget(manage_label)
        
        # 数据迁移按钮
        migrate_button = QPushButton("🔄 数据迁移")
        migrate_button.setStyleSheet(
            self.build_button_style(padding="8px 12px", radius=4, font_size="12px", accent="warning")
        )
        migrate_button.clicked.connect(self.show_migrate_options)
        manage_layout.addWidget(migrate_button)
        
        migrate_hint = QLabel("在不同存储方式之间迁移聊天数据。")
        migrate_hint.setStyleSheet(
            f"font-size: 11px; color: {palette['text_secondary']}; margin-left: 10px;"
        )
        manage_layout.addWidget(migrate_hint)
        
        self.right_layout.addWidget(manage_frame)
        
        # 添加弹性空间
        self.right_layout.addStretch()
        
        print("=== 聊天记录管理界面构建完成 ===")
    
    def handle_dsn_config(self):
        """处理DSN配置"""
        self.chat_config_dsn_signal.emit()
        
    def handle_file_config(self):
        """处理文件存储配置"""
        self.chat_config_file_signal.emit()
        
    def update_storage_status(self):
        """更新存储状态显示"""
        # 这里可以检查当前的存储配置并显示状态
        # 暂时显示默认状态
        self.storage_status_label.setText("📁 当前使用：本地文件存储")
        
    def show_migrate_options(self):
        """显示数据迁移选项"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("数据迁移")
        msg_box.setText("数据迁移功能将在存储配置完成后提供。\n请先配置您需要的存储方式。")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        palette = self.get_theme_palette()
        is_dark = self.is_dark_mode_enabled()
        msg_box.setStyleSheet("""
            QMessageBox {{
                background-color: {bg};
                color: {fg};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {btn_border};
                padding: 5px 15px;
                border-radius: 4px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """.format(
            bg=palette['card_bg'] if is_dark else "white",
            fg=palette['text_primary'] if is_dark else "black",
            btn_bg=palette['button_bg'] if is_dark else "#f0f0f0",
            btn_fg=palette['button_text'] if is_dark else "black",
            btn_border=palette['button_border'] if is_dark else "#cccccc",
            btn_hover=palette['button_hover'] if is_dark else "#e0e0e0"
        ))
        msg_box.exec()
    
    def show_api_settings(self):
        """显示API设置子项"""
        palette = self.get_theme_palette()
        # 标题
        title_label = QLabel("API设置")
        title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {palette['text_primary']}; margin-bottom: 15px;"
        )
        self.right_layout.addWidget(title_label)
        
        # 当前提供商信息
        try:
            current_provider = get_current_provider_name()
            provider_config = get_current_provider_config()
            provider_display_name = provider_config.get('display_name', current_provider)
            
            provider_info_label = QLabel(f"当前API提供商: {provider_display_name}")
            provider_info_label.setStyleSheet(
                f"font-size: 14px; color: {palette['text_secondary']}; margin-bottom: 10px; "
                f"background: {palette['card_bg']}; padding: 8px; border-radius: 4px;"
            )
            self.right_layout.addWidget(provider_info_label)
        except Exception as e:
            print(f"获取提供商信息失败: {e}")
            current_provider = 'deepseek'  # 默认值
        
        # API Key设置（根据提供商显示不同信息）
        is_gemini = current_provider == 'gemini'
        
        if is_gemini:
            api_key_label = QLabel("设置 Gemini API Key（回车确认）：")
            hint_text = "Gemini API Key 将自动保存到系统环境变量 GEMINI_API_KEY"
        else:
            api_key_label = QLabel("设置您的API_Key（回车确认）：")
            hint_text = "请输入您的API密钥"
            
        api_key_label.setStyleSheet(
            f"font-size: 13px; color: {palette['text_primary']}; margin-bottom: 5px;"
        )
        self.right_layout.addWidget(api_key_label)
        
        # 添加提示信息
        hint_label = QLabel(hint_text)
        hint_label.setStyleSheet(
            f"font-size: 11px; color: {palette['text_muted']}; margin-bottom: 5px;"
        )
        self.right_layout.addWidget(hint_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入API Key...")
        self.api_key_input.setStyleSheet(
            f"""
            QLineEdit {{ 
                background-color: {palette['input_bg']}; 
                border: 1px solid {palette['input_border']}; 
                padding: 8px; 
                font-size: 12px; 
                border-radius: 4px;
                color: {palette['text_primary']};
            }}
            QLineEdit:focus {{
                border: 1px solid {palette['highlight']};
            }}
        """
        )
        self.api_key_input.setClearButtonEnabled(True)
        self.api_key_input.returnPressed.connect(self.save_api_key)
        self.api_key_input.editingFinished.connect(self.save_api_key)
        self.right_layout.addWidget(self.api_key_input)
        
        # 间距
        spacer1 = QSpacerItem(0, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.right_layout.addItem(spacer1)
        
        # API URL设置（仅非Gemini提供商显示）
        if not is_gemini:
            api_url_label = QLabel("设置您的模型URL（回车确认）：")
            api_url_label.setStyleSheet(
                f"font-size: 13px; color: {palette['text_primary']}; margin-bottom: 5px;"
            )
            self.right_layout.addWidget(api_url_label)
            
            self.api_url_input = QLineEdit()
            self.api_url_input.setPlaceholderText("请输入模型URL...")
            self.api_url_input.setStyleSheet(
                f"""
                QLineEdit {{ 
                    background-color: {palette['input_bg']}; 
                    border: 1px solid {palette['input_border']}; 
                    padding: 8px; 
                    font-size: 12px; 
                    border-radius: 4px;
                    color: {palette['text_primary']};
                }}
                QLineEdit:focus {{
                    border: 1px solid {palette['highlight']};
                }}
            """
            )
            self.api_url_input.setClearButtonEnabled(True)
            self.api_url_input.returnPressed.connect(self.save_api_url)
            self.api_url_input.editingFinished.connect(self.save_api_url)
            self.right_layout.addWidget(self.api_url_input)
        else:
            # Gemini模式下，URL输入框不创建
            self.api_url_input = None

        # 安全提示
        mask_hint = QLabel("提示：为了安全，仅显示前4位和末尾2位，其余部分会使用 * 掩码。")
        mask_hint.setWordWrap(True)
        mask_hint.setStyleSheet(
            f"font-size: 11px; color: {palette['text_muted']}; margin-top: 6px;"
        )
        self.right_layout.addWidget(mask_hint)

        self._refresh_api_inputs()
        
        # 添加弹性空间
        self.right_layout.addStretch()
    
    def on_dark_mode_toggled(self, checked):
        """深色模式开关切换 - 增强响应版本"""
        print(f"🔘 深色模式状态变化: {checked}, theme_manager: {self.theme_manager}")
        
        if not self.theme_manager:
            print("[ERROR] 警告: theme_manager 为 None")
            return
        
        # 使用增强的主题管理器进行快速切换
        if hasattr(self.theme_manager, 'enable_dark_mode_fast'):
            print("⚡ 使用快速主题切换")
            self.theme_manager.enable_dark_mode_fast(checked)
        else:
            print("🐌 使用标准主题切换")
            self.theme_manager.enable_dark_mode(checked)

    def on_auto_mode_toggled(self, enabled):
        """自动模式开关切换 - 增强响应版本"""
        print(f"🔘 自动模式状态变化: {enabled}")
        
        # 立即提供用户反馈
        if enabled:
            print("⏰ 正在启用自动模式...")
            self.show_auto_mode_prompt()
        else:
            print("⏹️ 正在禁用自动模式...")
        
        if not self.theme_manager:
            print("[ERROR] 警告: theme_manager 为 None")
            return
            
        # 异步设置自动模式，避免阻塞UI
        QTimer.singleShot(0, lambda: self.theme_manager.set_auto_mode(enabled))

    def on_theme_manager_dark_mode_changed(self, enabled):
        """主题管理器回调，保持开关与全局状态同步"""
        if self.dark_mode_switch is not None:
            self.dark_mode_switch.blockSignals(True)
            self.dark_mode_switch.setChecked(bool(enabled))
            self.dark_mode_switch.blockSignals(False)

        self.apply_base_theme_styles()

        current_item = self.parent_list.currentItem() if self.parent_list else None
        if current_item:
            current_text = current_item.text()
    
    def load_collapse_threshold(self):
        """加载文本折叠阈值"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('collapse_threshold', 500)
        except Exception as e:
            print(f"加载折叠阈值失败: {e}")
        return 500  # 默认值
    
    def save_collapse_threshold(self, value):
        """保存文本折叠阈值"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            settings['collapse_threshold'] = value
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # 更新 chat_area.py 中的阈值
            from chat_area import CollapsibleBubbleLabel
            CollapsibleBubbleLabel.COLLAPSE_THRESHOLD = value
            
            print(f"折叠阈值已保存: {value}")
        except Exception as e:
            print(f"保存折叠阈值失败: {e}")
    
    def load_preview_length(self):
        """加载收起时显示的字符数"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('preview_length', 300)
        except Exception as e:
            print(f"加载预览长度失败: {e}")
        return 300  # 默认值
    
    def save_preview_length(self, value):
        """保存收起时显示的字符数"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            settings['preview_length'] = value
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # 更新 chat_area.py 中的预览长度
            from chat_area import CollapsibleBubbleLabel
            CollapsibleBubbleLabel.PREVIEW_LENGTH = value
            
            print(f"预览长度已保存: {value}")
        except Exception as e:
            print(f"保存预览长度失败: {e}")

    def show_auto_mode_prompt(self):
        """展示自动模式提示信息，使用浅色样式"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("自动模式")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("主题会根据系统时间自动切换深浅色模式。")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        palette = self.get_theme_palette()
        is_dark = self.is_dark_mode_enabled()
        msg_box.setStyleSheet("""
            QMessageBox {{
                background-color: {bg};
                color: {fg};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {btn_border};
                padding: 5px 15px;
                border-radius: 4px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """.format(
            bg=palette['card_bg'] if is_dark else "white",
            fg=palette['text_primary'] if is_dark else "black",
            btn_bg=palette['button_bg'] if is_dark else "#f0f0f0",
            btn_fg=palette['button_text'] if is_dark else "black",
            btn_border=palette['button_border'] if is_dark else "#cccccc",
            btn_hover=palette['button_hover'] if is_dark else "#e0e0e0"
        ))
        msg_box.exec()
        
    def choose_background(self):
        """选择背景图片或视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择背景图片或视频", 
            "", 
            "背景文件 (*.png *.jpg *.jpeg *.mp4 *.avi *.mov *.mkv);;图片文件 (*.png *.jpg *.jpeg);;视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            # 判断文件类型
            ext = os.path.splitext(file_path)[1].lower()
            is_video = ext in ['.mp4', '.avi', '.mov', '.mkv']
            file_type = "视频" if is_video else "图片"
            
            # 检查文件格式和分辨率
            if self.validate_background_file(file_path):
                self.bg_path_label.setText(f"已选择: {os.path.basename(file_path)} ({file_type})")
                if self.theme_manager:
                    # 传递 is_video 参数
                    self.theme_manager.set_custom_background(file_path, is_video=is_video)
                    # 立即应用背景并刷新UI
                    QTimer.singleShot(100, self.theme_manager.apply_background)
                
                print(f"✅ 背景{file_type}已设置: {file_path}")
                QMessageBox.information(self, "背景设置", f"✅ 背景{file_type}已更新\n\n文件: {os.path.basename(file_path)}\n类型: {file_type}文件")
            else:
                print(f"❌ 背景{file_type}验证失败: {file_path}")
                if is_video:
                    QMessageBox.warning(self, "格式错误", f"❌ 无法加载视频文件\n\n请确保:\n1. 视频文件未损坏\n2. 视频编码受支持（推荐 H.264）\n3. 文件路径正确")
                else:
                    QMessageBox.warning(self, "格式错误", f"❌ 只支持1920×1080分辨率的图片文件\n\n支持格式: PNG, JPG, JPEG")
    
    def validate_background_file(self, file_path):
        """验证背景文件格式和分辨率（支持图片和视频）"""
        try:
            # 检查文件扩展名
            ext = os.path.splitext(file_path)[1].lower()
            
            # 支持的图片格式
            if ext in ['.png', '.jpg', '.jpeg']:
                # 使用PIL检查分辨率（如果安装了PIL）
                if PIL_AVAILABLE:
                    try:
                        with Image.open(file_path) as img:
                            width, height = img.size
                            return width == 1920 and height == 1080
                    except Exception:
                        return False
                else:
                    # 如果PIL不可用，只检查扩展名
                    return True
            
            # 支持的视频格式
            elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                # 视频文件暂不检查分辨率（需要额外依赖）
                # 建议用户使用1920×1080的视频
                return True
            
            return False
                
        except Exception:
            return False
    
    def save_api_key(self):
        """保存API Key并持久化到配置文件"""
        raw_key = self.api_key_input.text().strip()
        if raw_key:
            try:
                current_provider = get_current_provider_name()
                if current_provider == 'gemini':
                    # 对于 Gemini，使用专门的设置函数
                    if set_gemini_api_key(raw_key):
                        print(f"Gemini API Key已保存并设置为环境变量: {raw_key[:10]}...")
                    else:
                        print("保存 Gemini API Key 失败")
                else:
                    # 对于其他提供商，使用标准方法
                    update_api_config(api_key=raw_key)
                    print(f"API Key已保存: {raw_key}")
                
                self._refresh_api_inputs()
            except Exception as e:
                print(f"保存API Key失败: {e}")
        
    def save_api_url(self):
        """保存API URL并持久化到配置文件"""
        raw_url = self.api_url_input.text().strip()
        if raw_url:
            update_api_config(api_url=raw_url)
            print(f"API URL已保存: {raw_url}")
            self._refresh_api_inputs()


class SearchDialog(QDialog):
    """搜索对话框 - 用于在聊天记录中查找文本"""
    search_in_current_signal = pyqtSignal(str)  # 在当前对话中搜索
    search_globally_signal = pyqtSignal(str)    # 全局搜索
    navigate_signal = pyqtSignal(int)  # 导航到第N个结果 (index)
    
    def __init__(self, parent=None, has_bubbles=False, has_conversations=False):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('搜索文本')
        self.setFixedSize(500, 200)
        
        self.has_bubbles = has_bubbles
        self.has_conversations = has_conversations
        self.result_label = None
        self.matches = []  # 存储搜索结果
        self.current_index = 0  # 当前显示的结果索引
        
        self.init_ui()
        self.apply_theme()
    
    def apply_theme(self):
        """应用主题"""
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        
        bg_color = "#2b2b2b" if is_dark else "white"
        text_color = "white" if is_dark else "black"
        gray_text = "#999999" if is_dark else "#666666"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
                font-size: 14px;
            }}
            QLabel#resultLabel {{
                color: {gray_text};
                font-size: 12px;
            }}
            QLineEdit {{
                background-color: {'#3b3b3b' if is_dark else '#f0f0f0'};
                color: {text_color};
                border: 1px solid {'#555' if is_dark else '#ccc'};
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {'#0078d4' if not is_dark else '#0d6efd'};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {'#106ebe' if not is_dark else '#0b5ed7'};
            }}
            QPushButton:disabled {{
                background-color: {'#cccccc' if not is_dark else '#555555'};
                color: {'#666666' if not is_dark else '#999999'};
            }}
        """)
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("输入要搜索的文本：")
        layout.addWidget(title_label)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入搜索内容...")
        self.search_input.returnPressed.connect(self.on_search_current)
        layout.addWidget(self.search_input)
        
        # 结果提示和导航按钮的水平布局
        result_nav_layout = QHBoxLayout()
        result_nav_layout.setSpacing(10)
        
        # 结果提示标签
        self.result_label = QLabel("")
        self.result_label.setObjectName("resultLabel")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        result_nav_layout.addWidget(self.result_label, 1)  # 占据剩余空间
        
        # 导航按钮容器
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(5)
        
        # 上一处按钮
        self.prev_btn = QPushButton("◀ 上一处")
        self.prev_btn.clicked.connect(self.on_previous)
        self.prev_btn.setVisible(False)
        self.prev_btn.setFixedWidth(100)
        nav_layout.addWidget(self.prev_btn)
        
        # 下一处按钮
        self.next_btn = QPushButton("下一处 ▶")
        self.next_btn.clicked.connect(self.on_next)
        self.next_btn.setVisible(False)
        self.next_btn.setFixedWidth(100)
        nav_layout.addWidget(self.next_btn)
        
        result_nav_layout.addWidget(nav_widget)
        layout.addLayout(result_nav_layout)
        
        # 搜索按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 查找按钮（仅在有气泡时可见）
        self.search_btn = QPushButton("查找")
        self.search_btn.clicked.connect(self.on_search_current)
        self.search_btn.setVisible(self.has_bubbles)
        self.search_btn.setEnabled(self.has_bubbles)
        button_layout.addWidget(self.search_btn)
        
        # 全局查找按钮（仅在有对话时可见）
        self.global_search_btn = QPushButton("全局查找")
        self.global_search_btn.clicked.connect(self.on_search_globally)
        self.global_search_btn.setVisible(self.has_conversations)
        self.global_search_btn.setEnabled(self.has_conversations)
        button_layout.addWidget(self.global_search_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 添加弹性空间
        layout.addStretch()
    
    def on_search_current(self):
        """在当前对话中搜索"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.show_result("请输入搜索内容", is_error=True)
            return
        
        if not self.has_bubbles:
            self.show_result("当前对话中没有消息", is_error=True)
            return
        
        self.search_in_current_signal.emit(search_text)
    
    def on_search_globally(self):
        """全局搜索"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.show_result("请输入搜索内容", is_error=True)
            return
        
        if not self.has_conversations:
            self.show_result("没有可搜索的对话", is_error=True)
            return
        
        self.search_globally_signal.emit(search_text)
    
    def on_previous(self):
        """跳转到上一处匹配"""
        if self.matches and self.current_index > 0:
            self.current_index -= 1
            self.navigate_signal.emit(self.current_index)
            self.update_result_display()
    
    def on_next(self):
        """跳转到下一处匹配"""
        if self.matches and self.current_index < len(self.matches) - 1:
            self.current_index += 1
            self.navigate_signal.emit(self.current_index)
            self.update_result_display()
    
    def set_search_results(self, matches, current_index=0):
        """设置搜索结果"""
        self.matches = matches
        self.current_index = current_index
        self.update_result_display()
        
        # 显示/隐藏导航按钮
        show_nav = len(matches) >= 2
        self.prev_btn.setVisible(show_nav)
        self.next_btn.setVisible(show_nav)
    
    def update_result_display(self):
        """更新结果显示"""
        if not self.matches:
            self.show_result("没有找到匹配内容", is_error=True)
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            return
        
        total = len(self.matches)
        current = self.current_index + 1
        self.show_result(f"已查找到 {total} 处内容，现在显示的是 {current}/{total} 处", is_error=False)
        
        # 更新按钮状态
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < total - 1)
    
    def show_result(self, message, is_error=False):
        """显示搜索结果消息"""
        if self.result_label:
            if is_error:
                self.result_label.setStyleSheet("color: red; font-size: 12px;")
            else:
                # 使用灰色字体
                parent = self.parent()
                is_dark = False
                if parent and hasattr(parent, 'theme_manager'):
                    is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
                gray_color = "#999999" if is_dark else "#666666"
                self.result_label.setStyleSheet(f"color: {gray_color}; font-size: 12px;")
            
            self.result_label.setText(message)
    
    def clear_result(self):
        """清除结果消息"""
        if self.result_label:
            self.result_label.setText("")
        self.matches = []
        self.current_index = 0
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)


class FileModeDialog(QDialog):
    """文件上传模式选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.selected_mode = None  # 'temporary' or 'persistent'
        self.setFixedSize(300, 300)
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("选择文件上传模式")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 按钮布局
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # 临时分析按钮
        self.temp_btn = QPushButton("📄 临时分析\n(仅单次对话)")
        self.temp_btn.setFixedHeight(50)
        self.temp_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2A5F8F;
            }
        """)
        self.temp_btn.clicked.connect(lambda: self.select_mode('temporary'))
        button_layout.addWidget(self.temp_btn)
        
        # 后续引用按钮
        self.persist_btn = QPushButton("🔗 后续引用\n(仅保存48小时)")
        self.persist_btn.setFixedHeight(50)
        self.persist_btn.setStyleSheet("""
            QPushButton {
                background-color: #50C878;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3FA368;
            }
            QPushButton:pressed {
                background-color: #2F8350;
            }
        """)
        self.persist_btn.clicked.connect(lambda: self.select_mode('persistent'))
        button_layout.addWidget(self.persist_btn)
        
        layout.addLayout(button_layout)
        
        # 添加取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #999999;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #777777;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
    
    def apply_theme(self):
        """应用主题"""
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        
        bg_color = "#2b2b2b" if is_dark else "white"
        text_color = "white" if is_dark else "black"
        border_color = "#555" if is_dark else "#ccc"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
    
    def select_mode(self, mode):
        """选择模式并关闭对话框"""
        self.selected_mode = mode
        self.accept()
    
    def get_selected_mode(self):
        """获取选择的模式"""
        return self.selected_mode


class FilePreviewDialog(QDialog):
    """文件预览对话框 - 支持图片、PDF、文本等文件预览"""
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.setWindowTitle(f"预览: {self.file_name}")
        self.setMinimumSize(600, 400)
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 文件信息标签
        info_label = QLabel(f"文件: {self.file_name}")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)
        
        # 滚动区域（用于显示内容）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 根据文件类型显示内容
        file_ext = os.path.splitext(self.file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif']:
            # 图片预览
            self.show_image_preview(content_layout)
        elif file_ext == '.pdf':
            # PDF预览（简单提示）
            self.show_pdf_preview(content_layout)
        elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
            # 视频预览（简单提示）
            self.show_video_preview(content_layout)
        else:
            # 不支持的文件类型
            self.show_unsupported_preview(content_layout)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 35)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def show_image_preview(self, layout):
        """显示图片预览"""
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                # 限制最大显示尺寸
                max_width = 800
                max_height = 600
                if pixmap.width() > max_width or pixmap.height() > max_height:
                    pixmap = pixmap.scaled(max_width, max_height, 
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                
                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(label)
            else:
                layout.addWidget(QLabel("无法加载图片"))
        except Exception as e:
            layout.addWidget(QLabel(f"加载图片失败: {str(e)}"))
    
    def show_text_preview(self, layout):
        """显示文本预览"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read(10000)  # 最多读取10000字符
            
            text_label = QLabel(content)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            text_label.setStyleSheet("padding: 10px; background: rgba(0,0,0,0.05); border-radius: 5px;")
            layout.addWidget(text_label)
            
            if len(content) == 10000:
                layout.addWidget(QLabel("（仅显示前10000字符）"))
        except Exception as e:
            layout.addWidget(QLabel(f"读取文件失败: {str(e)}"))
    
    def show_pdf_preview(self, layout):
        """显示PDF预览提示"""
        label = QLabel("📄 PDF文件\n\n此文件已上传，AI可以分析其内容。\n如需查看完整内容，请使用PDF阅读器打开。")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 14px; padding: 20px;")
        layout.addWidget(label)
        
        # 添加打开文件按钮
        open_btn = QPushButton("用系统默认程序打开")
        open_btn.clicked.connect(lambda: os.startfile(self.file_path))
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def show_video_preview(self, layout):
        """显示视频预览提示"""
        label = QLabel("🎬 视频文件\n\n此文件已上传，AI可以分析其内容。\n如需查看完整内容，请使用视频播放器打开。")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 14px; padding: 20px;")
        layout.addWidget(label)
        
        # 添加打开文件按钮
        open_btn = QPushButton("用系统默认程序打开")
        open_btn.clicked.connect(lambda: os.startfile(self.file_path))
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def show_unsupported_preview(self, layout):
        """显示不支持的文件类型提示"""
        label = QLabel(f"📁 {os.path.splitext(self.file_name)[1]} 文件\n\n此文件类型不支持预览。")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 14px; padding: 20px;")
        layout.addWidget(label)
        
        # 添加打开文件按钮
        open_btn = QPushButton("用系统默认程序打开")
        open_btn.clicked.connect(lambda: os.startfile(self.file_path))
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def apply_theme(self):
        """应用主题"""
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        
        bg_color = "#2b2b2b" if is_dark else "#f5f5f5"
        text_color = "white" if is_dark else "black"
        border_color = "#555" if is_dark else "#ccc"
        btn_bg = "#3a3a3a" if is_dark else "#e0e0e0"
        btn_hover = "#4a4a4a" if is_dark else "#d0d0d0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)


class ImagePreviewDialog(QDialog):
    """图片预览对话框 - 用于全分辨率预览生成的图片"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.image_path = image_path
        self.setWindowTitle(f"图片预览 - {os.path.basename(image_path)}")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图片标签
        image_label = QLabel()
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            # 显示全分辨率图片
            image_label.setPixmap(pixmap)
        else:
            image_label.setText("无法加载图片")
        
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 35)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def apply_theme(self):
        """应用主题"""
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        
        bg_color = "#1a1a1a" if is_dark else "#f5f5f5"
        text_color = "white" if is_dark else "black"
        btn_bg = "#3a3a3a" if is_dark else "#e0e0e0"
        btn_hover = "#4a4a4a" if is_dark else "#d0d0d0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)


class SearchEngineDialog(QDialog):
    """搜索引擎切换对话框"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('切换搜索引擎')
        self.setFixedSize(500, 320)
        
        # 导入配置管理器
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__)))
        from search_engine_config import get_search_engine_config
        
        self.config = get_search_engine_config()
        self.checkboxes = {}
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🔍 选择搜索引擎")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        info_label = QLabel("可以同时启用多个搜索引擎\n先选择的引擎将被优先使用")
        info_label.setStyleSheet("font-size: 11px; color: #666;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addSpacing(15)
        
        # 获取当前配置
        enabled_engines = self.config.get_enabled_engines()
        primary_engine = self.config.get_primary_engine()
        
        # 🔧 搜索引擎选项 - 并列布局
        engines_container = QHBoxLayout()
        engines_container.setSpacing(20)
        
        for engine_id, engine_info in self.config.AVAILABLE_ENGINES.items():
            # 创建每个引擎的垂直容器
            engine_vbox = QVBoxLayout()
            engine_vbox.setSpacing(10)
            
            # 复选框和引擎名称
            header_layout = QHBoxLayout()
            checkbox = QCheckBox()
            checkbox.setChecked(engine_id in enabled_engines)
            checkbox.stateChanged.connect(lambda state, eid=engine_id: self.on_engine_toggled(eid, state))
            self.checkboxes[engine_id] = checkbox
            
            icon = engine_info['icon']
            name = engine_info['name']
            is_primary = " [优先]" if engine_id == primary_engine else ""
            
            name_label = QLabel(f"{icon} <b>{name}</b>{is_primary}")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            name_label.setStyleSheet("font-size: 13px;")
            
            header_layout.addWidget(checkbox)
            header_layout.addWidget(name_label)
            header_layout.addStretch()
            
            # 描述文本
            desc = engine_info['description']
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 10px; color: #888; padding-left: 30px;")
            
            engine_vbox.addLayout(header_layout)
            engine_vbox.addWidget(desc_label)
            
            # 添加到水平布局
            engines_container.addLayout(engine_vbox, 1)
        
        layout.addLayout(engines_container)
        
        layout.addSpacing(15)
        
        # 🔧 当前配置显示 - 增加高度
        self.status_label = QLabel()
        self.update_status_label()
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(60)  # 设置最小高度
        self.status_label.setStyleSheet("""
            font-size: 11px; 
            color: #0078d4; 
            padding: 15px; 
            background-color: rgba(0,120,212,0.1); 
            border-radius: 5px;
            line-height: 1.5;
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.setFixedSize(90, 35)
        reset_btn.clicked.connect(self.reset_to_default)
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(90, 35)
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def on_engine_toggled(self, engine_id: str, state: int):
        """引擎切换事件"""
        # 检查是否至少保留一个引擎
        enabled_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        
        if enabled_count == 0:
            # 至少需要一个引擎
            self.checkboxes[engine_id].setChecked(True)
            QMessageBox.warning(self, "提示", "至少需要启用一个搜索引擎")
            return
        
        # 更新配置
        self.config.toggle_engine(engine_id)
        self.update_status_label()
        
        # 重新加载工具执行器以应用更改
        try:
            from tool_executor import get_tool_executor
            executor = get_tool_executor()
            # 清除现有工具并重新注册
            executor._tools.clear()
            executor._tool_schemas.clear()
            executor._register_default_tools()
        except Exception as e:
            print(f"[搜索引擎对话框] 更新工具失败: {e}")
    
    def update_status_label(self):
        """更新状态标签"""
        enabled = self.config.get_enabled_engines()
        primary = self.config.get_primary_engine()
        
        enabled_names = [self.config.AVAILABLE_ENGINES[e]['name'] for e in enabled]
        primary_name = self.config.AVAILABLE_ENGINES[primary]['name']
        
        status_text = f"✅ 已启用: {', '.join(enabled_names)}<br>⭐ 优先使用: {primary_name}"
        self.status_label.setText(status_text)
    
    def reset_to_default(self):
        """恢复默认配置"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要恢复默认配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 恢复默认：启用百度和Google，优先百度
            self.config.set_engines(["baidu", "google"], "baidu")
            
            # 更新复选框状态
            for engine_id, checkbox in self.checkboxes.items():
                checkbox.setChecked(engine_id in ["baidu", "google"])
            
            self.update_status_label()
            
            # 重新加载工具
            try:
                from tool_executor import get_tool_executor
                executor = get_tool_executor()
                executor._tools.clear()
                executor._tool_schemas.clear()
                executor._register_default_tools()
            except Exception as e:
                print(f"[搜索引擎对话框] 重置工具失败: {e}")
    
    def apply_theme(self):
        """应用主题"""
        is_dark = False
        parent = self.parent()
        if parent and hasattr(parent, 'theme_manager'):
            is_dark = getattr(parent.theme_manager, 'dark_mode_enabled', False)
        
        bg_color = "#1a1a1a" if is_dark else "#f5f5f5"
        text_color = "white" if is_dark else "black"
        btn_bg = "#3a3a3a" if is_dark else "#e0e0e0"
        btn_hover = "#4a4a4a" if is_dark else "#d0d0d0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QCheckBox {{
                color: {text_color};
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #999;
                background-color: {"#2a2a2a" if is_dark else "white"};
            }}
            QCheckBox::indicator:hover {{
                border-color: #0078d4;
            }}
            QCheckBox::indicator:checked {{
                background-color: #10b981;
                border-color: #10b981;
                image: url(none);
            }}
            QCheckBox::indicator:checked::after {{
                content: "✓";
                color: white;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)



