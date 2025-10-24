from PyQt6.QtWidgets import QPushButton, QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QEvent
from PyQt6.QtGui import QClipboard

class CopyButton(QPushButton):
    """复制按钮组件"""
    def __init__(self, parent=None):
        super().__init__("复制", parent)
        self.setFixedSize(50, 25)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.95);
                color: black;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid rgba(0, 0, 0, 0.8);
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 1.0);
                border: 2px solid rgba(0, 0, 0, 1.0);
                color: #333;
            }
            QPushButton:pressed {
                background: rgba(220, 220, 220, 1.0);
                border: 2px solid rgba(0, 0, 0, 1.0);
                color: black;
            }
        """)
        self.hide()

class EditButton(QPushButton):
    """修改按钮组件"""
    def __init__(self, parent=None):
        super().__init__("修改", parent)
        self.setFixedSize(50, 25)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(135, 206, 250, 0.9);
                color: black;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid rgba(0, 0, 150, 0.8);
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: rgba(135, 206, 250, 1.0);
                border: 2px solid rgba(0, 0, 150, 1.0);
                color: #333;
            }
            QPushButton:pressed {
                background: rgba(100, 180, 220, 1.0);
                border: 2px solid rgba(0, 0, 150, 1.0);
                color: black;
            }
        """)
        self.hide()

class DeleteButton(QPushButton):
    """删除按钮组件"""
    def __init__(self, parent=None):
        super().__init__("删除", parent)
        self.setFixedSize(50, 25)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 100, 100, 0.9);
                color: black;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid rgba(150, 0, 0, 0.8);
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 1.0);
                border: 2px solid rgba(150, 0, 0, 1.0);
                color: #333;
            }
            QPushButton:pressed {
                background: rgba(220, 80, 80, 1.0);
                border: 2px solid rgba(150, 0, 0, 1.0);
                color: black;
            }
        """)
        self.hide()

class EditMessageDialog(QDialog):
    """修改消息对话框"""
    def __init__(self, original_text, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle('修改消息')
        self.setFixedSize(500, 300)
        self.new_text = ''
        
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        
        # 提示标签
        label = QLabel("修改消息内容：")
        label.setStyleSheet("color: black; font-size: 14px; margin: 5px;")
        layout.addWidget(label)
        
        # 文本编辑框
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlainText(original_text)
        self.text_edit.selectAll()  # 选中所有文本
        self.text_edit.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; padding: 5px; font-size: 14px;")
        layout.addWidget(self.text_edit)
        
        # 按钮
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
        self.text_edit.setFocus()
        
    def accept(self):
        self.new_text = self.text_edit.toPlainText().strip()
        if self.new_text:
            super().accept()
        else:
            self.text_edit.setFocus()

# 全局复制按钮管理器
class CopyButtonManager:
    _instance = None
    _current_buttons = []
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_button(self, button):
        """注册按钮"""
        if button not in self._current_buttons:
            self._current_buttons.append(button)
    
    def clear_all_buttons(self):
        """清除所有按钮"""
        count = len(self._current_buttons)
        if count:
            print(f"[DEBUG] 回收聊天功能按钮 {count} 个（切换对话或刷新时自动清理）")
        for button in self._current_buttons:
            if button:
                try:
                    button.hide()
                    button.deleteLater()
                except RuntimeError:
                    pass  # 按钮可能已经被删除
        self._current_buttons.clear()

class BubbleCopyMixin:
    """为气泡添加功能按钮的混入类"""
    
    def __init__(self, *args, **kwargs):
        # 提取side参数
        self.side = kwargs.get('side', 'left')
        # 移除side参数，避免传递给父类
        if 'side' in kwargs:
            del kwargs['side']
        
        super().__init__(*args, **kwargs)
        self.copy_button = None
        self.edit_button = None
        self.delete_button = None
        self.last_mouse_y = 0
        self.hide_timer = None
        self.bubble_index = None  # 气泡在对话中的索引
        
        # 延迟初始化功能按钮，等待样式应用完成
        QTimer.singleShot(0, self._delayed_init)
        
    def _delayed_init(self):
        """延迟初始化功能按钮，确保样式已应用"""
        # 强制验证和修复side参数
        self._validate_bubble_side()
        self._init_copy_functionality()
        
    def set_bubble_index(self, index):
        """设置气泡索引"""
        self.bubble_index = index
        
    def _validate_bubble_side(self):
        """验证和修复气泡side参数"""
        # 检查气泡颜色来确定类型
        style_sheet = self.styleSheet()
        if 'rgb(50,205,50)' in style_sheet or 'rgb(50, 205, 50)' in style_sheet:
            # 绿色气泡 = 用户气泡
            self.side = 'right'
        elif 'rgb(30,144,255)' in style_sheet or 'rgb(30, 144, 255)' in style_sheet:
            # 蓝色气泡 = AI气泡
            self.side = 'left'
        
    def _init_copy_functionality(self):
        """初始化功能按钮"""
        # 创建按钮，父级设置为顶层窗口
        top_window = self
        while top_window.parent():
            top_window = top_window.parent()
        
        # 创建复制按钮（所有气泡都有）
        self.copy_button = CopyButton(top_window)
        self.copy_button.clicked.connect(self._copy_text_to_clipboard)
        CopyButtonManager.get_instance().register_button(self.copy_button)
        
        # 创建删除按钮（所有气泡都有）
        self.delete_button = DeleteButton(top_window)
        self.delete_button.clicked.connect(self._delete_bubble)
        CopyButtonManager.get_instance().register_button(self.delete_button)
        
        # 创建修改按钮（只有用户气泡有）
        if self.side == 'right':
            self.edit_button = EditButton(top_window)
            self.edit_button.clicked.connect(self._edit_bubble)
            CopyButtonManager.get_instance().register_button(self.edit_button)
        
        # 初始化延迟隐藏定时器
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self._hide_buttons)
        self.hide_timer.setSingleShot(True)
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._register_mouse_tracking_targets()
        
    def _copy_text_to_clipboard(self):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        text_content = self.text()
        clipboard.setText(text_content)
        self._show_copy_success_feedback()
        
    def _edit_bubble(self):
        """修改气泡内容"""
        dialog = EditMessageDialog(self.text(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.new_text:
            # 发送修改信号，包含气泡索引和新内容
            chat_window = self._find_chat_window()
            if chat_window:
                chat_window.edit_message_signal.emit(self.bubble_index, dialog.new_text)
                
    def _delete_bubble(self):
        """删除气泡"""
        # 确认删除对话框
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认删除")
        msg_box.setText("确认删除这条消息吗？删除后无法恢复。")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # 设置按钮文本为中文
        yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
        yes_button.setText("确认删除")
        no_button = msg_box.button(QMessageBox.StandardButton.No)
        no_button.setText("取消")
        
        # 移除气泡包围样式，使用简洁的白色背景
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: black;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            QMessageBox QLabel {
                background-color: white;
                color: black;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
                font-size: 14px;
                color: black;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # 发送删除信号，包含气泡索引
            chat_window = self._find_chat_window()
            if chat_window:
                chat_window.delete_message_signal.emit(self.bubble_index)
                print(f"发送删除信号: 索引={self.bubble_index}")
    
    def _find_chat_window(self):
        """查找ChatWindow实例"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'edit_message_signal') and hasattr(parent, 'delete_message_signal'):
                return parent
            parent = parent.parent()
        return None

    def _register_mouse_tracking_targets(self):
        """为子控件开启鼠标追踪并添加事件过滤"""
        for child in self.findChildren(QWidget):
            # 跳过功能按钮（它们挂在顶层窗口）
            if isinstance(child, (CopyButton, DeleteButton, EditButton)):
                continue
            child.setMouseTracking(True)
            child.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        """捕获子控件的鼠标事件以更新按钮位置"""
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self._handle_child_mouse_activity(obj, event)
        elif event.type() in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            self._handle_child_mouse_activity(obj, event, fallback_center=True)
        return super().eventFilter(obj, event)

    def _handle_child_mouse_activity(self, widget, event, fallback_center=False):
        """根据子控件事件计算相对位置并更新按钮高度"""
        if not hasattr(self, 'copy_button') or not self.copy_button:
            return

        try:
            if hasattr(event, 'position'):
                local_pos = event.position()
            elif hasattr(event, 'pos'):
                local_pos = event.pos()
            else:
                local_pos = None

            if local_pos is not None and hasattr(local_pos, 'toPoint'):
                local_point = local_pos.toPoint()
            elif local_pos is not None:
                local_point = QPoint(int(local_pos.x()), int(local_pos.y()))
            else:
                local_point = None

            if local_point is not None:
                global_pos = widget.mapToGlobal(local_point)
                bubble_point = self.mapFromGlobal(global_pos)
                clamped_y = max(0, min(int(bubble_point.y()), self.height()))
            elif fallback_center:
                clamped_y = self.height() // 2
            else:
                return

            self.last_mouse_y = clamped_y
            self._show_buttons(clamped_y)
        except Exception:
            pass

    def _update_buttons_position(self, mouse_y_in_bubble):
        """更新按钮位置"""
        if not hasattr(self, 'copy_button') or not self.copy_button:
            return
            
        # 再次验证气泡类型（防止错误）
        self._validate_bubble_side()
            
        button_width = 50
        button_height = 25
        button_spacing = 5
        
        # 获取气泡在顶层窗口中的全局位置
        bubble_global_pos = self.mapToGlobal(QPoint(0, 0))
        top_window = self.copy_button.parent()
        if top_window:
            bubble_local_pos = top_window.mapFromGlobal(bubble_global_pos)
        else:
            bubble_local_pos = bubble_global_pos
        
        # 计算按钮Y坐标
        button_y = bubble_local_pos.y() + mouse_y_in_bubble - button_height // 2
        
        # 限制按钮Y坐标在气泡高度范围内
        min_y = bubble_local_pos.y()
        max_y = bubble_local_pos.y() + self.height() - button_height
        button_y = max(min_y, min(button_y, max_y))
        
        if self.side == 'right':
            # 用户气泡：【删除】【修改】【复制】--------
            buttons = [self.delete_button]
            if self.edit_button:
                buttons.append(self.edit_button)
            buttons.append(self.copy_button)
            
            total_width = len(buttons) * button_width + (len(buttons) - 1) * button_spacing
            start_x = bubble_local_pos.x() - total_width - 3  # 完全贴合，无间距

            for i, button in enumerate(buttons):
                button_x = start_x + i * (button_width + button_spacing)
                button.move(button_x, button_y)
                
        else:
            # AI气泡：--------【复制】【删除】
            buttons = [self.copy_button, self.delete_button]
            start_x = bubble_local_pos.x() + self.width() + 3  # 缩小间距从10到3
            
            for i, button in enumerate(buttons):
                button_x = start_x + i * (button_width + button_spacing)
                button.move(button_x, button_y)
        
        # 全局边界检查
        if top_window:
            for button in [self.copy_button, self.delete_button] + ([self.edit_button] if self.edit_button else []):
                current_pos = button.pos()
                if current_pos.x() < 0:
                    button.move(10, current_pos.y())
                elif current_pos.x() + button_width > top_window.width():
                    button.move(top_window.width() - button_width - 10, current_pos.y())
                    
                if current_pos.y() < 0:
                    button.move(current_pos.x(), 10)
                elif current_pos.y() + button_height > top_window.height():
                    button.move(current_pos.x(), top_window.height() - button_height - 10)

    def _show_buttons(self, mouse_y):
        """显示按钮"""
        if not hasattr(self, 'copy_button') or not self.copy_button:
            return
            
        if self.hide_timer and self.hide_timer.isActive():
            self.hide_timer.stop()
            
        self._update_buttons_position(mouse_y)
        
        # 显示所有按钮
        self.copy_button.show()
        self.copy_button.raise_()
        self.delete_button.show()
        self.delete_button.raise_()
        if hasattr(self, 'edit_button') and self.edit_button is not None:
            self.edit_button.show()
            self.edit_button.raise_()
        
    def _hide_buttons(self):
        """隐藏按钮"""
        if hasattr(self, 'copy_button') and self.copy_button:
            self.copy_button.hide()
        if hasattr(self, 'delete_button') and self.delete_button:
            self.delete_button.hide()
        if hasattr(self, 'edit_button') and self.edit_button:
            self.edit_button.hide()
            
    def _start_hide_timer(self):
        """启动2秒延迟隐藏定时器"""
        if self.hide_timer:
            self.hide_timer.start(2000)
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        clamped_y = max(0, min(int(event.position().y()), self.height()))
        self.last_mouse_y = clamped_y
        self._show_buttons(clamped_y)
        super().mouseMoveEvent(event)
        
    def enterEvent(self, event):
        """鼠标进入事件"""
        initial_y = self.height() // 2
        self.last_mouse_y = initial_y
        self._show_buttons(initial_y)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开事件"""
        if hasattr(self, 'copy_button') and self.copy_button:
            safe_last_y = max(0, min(self.last_mouse_y, self.height()))
            self._update_buttons_position(safe_last_y)
            self._show_buttons(safe_last_y)
            
        self._start_hide_timer()
        super().leaveEvent(event)
        
    def resizeEvent(self, event):
        """窗口大小改变时调整按钮位置"""
        super().resizeEvent(event)
        if (hasattr(self, 'copy_button') and self.copy_button and 
            self.copy_button.isVisible() and hasattr(self, 'last_mouse_y')):
            safe_last_y = max(0, min(self.last_mouse_y, self.height()))
            self._update_buttons_position(safe_last_y)

    # 添加复制成功反馈方法（修复 AttributeError）
    def _show_copy_success_feedback(self):
        """复制成功时短暂修改复制按钮样式与文本以提示用户，然后恢复原状。"""
        if not hasattr(self, 'copy_button') or not self.copy_button:
            return
        try:
            original_style = self.copy_button.styleSheet()
            original_text = self.copy_button.text()
            
            success_style = """
                QPushButton {
                    background: rgba(0, 200, 0, 0.9);
                    color: white;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    border: 2px solid rgba(0, 150, 0, 1.0);
                    padding: 2px 6px;
                }
            """
            self.copy_button.setStyleSheet(success_style)
            self.copy_button.setText("已复制!")
            
            # 800ms 后恢复
            QTimer.singleShot(800, lambda: (
                self.copy_button.setStyleSheet(original_style),
                self.copy_button.setText(original_text)
            ))
        except Exception as e:
            # 不阻塞主逻辑，打印调试信息
            print(f"_show_copy_success_feedback 异常: {e}")

def create_copyable_bubble_class(base_label_class):
    """工厂函数：创建带功能按钮的气泡类"""
    class CopyableBubbleLabel(BubbleCopyMixin, base_label_class):
        def __init__(self, text, side='left', parent=None, is_history=False):
            # 可选的调试打印，必要时打开
            # print(f"创建功能气泡: text={text[:20]}..., side={side}")
            super().__init__(text=text, side=side, parent=parent, is_history=is_history)

    return CopyableBubbleLabel
