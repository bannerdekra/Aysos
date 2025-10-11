#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的开关组件 - 支持防抖动和即时反馈
解决按钮点击无反应的问题
"""

from PyQt6.QtWidgets import QCheckBox, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QPaintEvent, QMouseEvent
import time


class ResponsiveToggleSwitch(QCheckBox):
    """响应式切换开关 - 支持即时反馈和防抖动"""
    
    # 自定义信号，确保状态变化能正确传递
    state_changed = pyqtSignal(bool)
    click_feedback = pyqtSignal()  # 点击反馈信号
    
    def __init__(self, parent=None, width=58, height=30, margin=3):
        super().__init__(parent)
        
        # 尺寸设置
        self._width = width
        self._height = height
        self._margin = margin
        self.setFixedSize(self._width, self._height)
        
        # 外观设置
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 状态管理
        self._is_animating = False
        self._last_click_time = 0
        self._debounce_delay_ms = 5  # 5ms防抖动
        self._visual_state = self.isChecked()  # 视觉状态，用于即时反馈
        
        # 动画相关
        self._knob_position = 0.0  # 0.0 = 左侧, 1.0 = 右侧
        self._animation = QPropertyAnimation(self, b"knob_position")
        self._animation.setDuration(150)  # 150ms动画
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 防抖动定时器
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_state_change)
        
        # 连接原始信号
        super().toggled.connect(self._handle_toggle)
        
        # 初始化动画位置
        self._update_knob_position()
    
    @property
    def knob_position(self):
        return self._knob_position
    
    @knob_position.setter
    def knob_position(self, pos):
        self._knob_position = pos
        self.update()  # 触发重绘
    
    def _update_knob_position(self):
        """更新旋钮位置动画"""
        target_position = 1.0 if self._visual_state else 0.0
        
        if abs(self._knob_position - target_position) > 0.01:
            self._animation.stop()
            self._animation.setStartValue(self._knob_position)
            self._animation.setEndValue(target_position)
            self._animation.start()
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件 - 立即提供视觉反馈"""
        if event.button() == Qt.MouseButton.LeftButton:
            current_time = time.time() * 1000  # 转换为毫秒
            
            # 检查防抖动
            if current_time - self._last_click_time < self._debounce_delay_ms:
                print("🚫 防抖动：忽略过快的点击")
                return
            
            self._last_click_time = current_time
            
            print(f"🖱️ 按钮点击 - 当前状态: {self.isChecked()}")
            
            # 立即更新视觉状态，提供即时反馈
            self._visual_state = not self._visual_state
            self._update_knob_position()
            
            # 发射点击反馈信号
            self.click_feedback.emit()
            
            print(f"⚡ 视觉状态立即更新为: {self._visual_state}")
        
        # 调用父类方法处理实际的状态切换
        super().mousePressEvent(event)
    
    def _handle_toggle(self, checked: bool):
        """处理状态切换"""
        print(f"🔄 开关状态切换: {checked}")
        
        # 确保视觉状态与实际状态同步
        if self._visual_state != checked:
            self._visual_state = checked
            self._update_knob_position()
        
        # 使用防抖动定时器延迟发射信号
        self._debounce_timer.stop()
        self._debounce_timer.start(self._debounce_delay_ms)
    
    def _emit_state_change(self):
        """发射状态变化信号（防抖动后）"""
        actual_state = self.isChecked()
        print(f"📡 发射状态变化信号: {actual_state}")
        self.state_changed.emit(actual_state)
    
    def set_checked_silently(self, checked: bool):
        """静默设置状态（不触发信号）"""
        print(f"🔇 静默设置状态: {checked}")
        
        # 暂时断开信号
        self.blockSignals(True)
        self.setChecked(checked)
        self._visual_state = checked
        self._update_knob_position()
        self.blockSignals(False)
    
    def paintEvent(self, event: QPaintEvent):
        """自定义绘制"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制轨道
        track_rect = QRect(0, (self.height() - self._height) // 2, self._width, self._height)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 根据视觉状态选择颜色
        if self.isEnabled():
            if self._visual_state:
                track_color = QColor("#3DC06C")  # 绿色
            else:
                track_color = QColor("#D8D8D8")  # 灰色
        else:
            track_color = QColor("#BEBEBE")  # 禁用状态
        
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, self._height // 2, self._height // 2)
        
        # 计算旋钮位置
        knob_diameter = self._height - self._margin * 2
        knob_range = self._width - knob_diameter - self._margin * 2
        knob_x = self._margin + knob_range * self._knob_position
        
        knob_rect = QRect(
            int(knob_x), 
            track_rect.top() + self._margin, 
            knob_diameter, 
            knob_diameter
        )
        
        # 绘制旋钮
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_rect)
        
        # 绘制阴影效果
        painter.setPen(QColor(0, 0, 0, 20))
        painter.drawEllipse(knob_rect)


class EnhancedSettingsDialog:
    """增强的设置对话框集成类"""
    
    def __init__(self, settings_dialog):
        self.dialog = settings_dialog
        self._setup_enhanced_switches()
    
    def _setup_enhanced_switches(self):
        """设置增强的开关组件"""
        # 替换深色模式开关
        if hasattr(self.dialog, 'dark_mode_switch'):
            old_switch = self.dialog.dark_mode_switch
            parent = old_switch.parent()
            
            # 创建新的增强开关
            new_switch = ResponsiveToggleSwitch(parent)
            new_switch.set_checked_silently(old_switch.isChecked())
            
            # 替换布局中的组件
            layout = parent.layout()
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == old_switch:
                        layout.removeWidget(old_switch)
                        layout.insertWidget(i, new_switch)
                        break
            
            # 连接新的信号
            new_switch.state_changed.connect(self.dialog.on_dark_mode_toggled)
            new_switch.click_feedback.connect(lambda: print("🔘 深色模式按钮点击反馈"))
            
            # 更新引用
            self.dialog.dark_mode_switch = new_switch
            old_switch.deleteLater()
            
            print("[OK] 深色模式开关已增强")
        
        # 替换自动模式开关
        if hasattr(self.dialog, 'auto_mode_switch'):
            old_switch = self.dialog.auto_mode_switch
            parent = old_switch.parent()
            
            # 创建新的增强开关
            new_switch = ResponsiveToggleSwitch(parent)
            new_switch.set_checked_silently(old_switch.isChecked())
            
            # 替换布局中的组件
            layout = parent.layout()
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == old_switch:
                        layout.removeWidget(old_switch)
                        layout.insertWidget(i, new_switch)
                        break
            
            # 连接新的信号
            new_switch.state_changed.connect(self.dialog.on_auto_mode_toggled)
            new_switch.click_feedback.connect(lambda: print("🔘 自动模式按钮点击反馈"))
            
            # 更新引用
            self.dialog.auto_mode_switch = new_switch
            old_switch.deleteLater()
            
            print("[OK] 自动模式开关已增强")


def enhance_settings_dialog(dialog):
    """增强现有的设置对话框"""
    enhancer = EnhancedSettingsDialog(dialog)
    return enhancer