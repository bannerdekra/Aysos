#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的主题管理器 - 支持预渲染和异步更新
解决按钮响应延迟问题
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QThread, QMutex
from PyQt6.QtGui import QPainter, QColor
import datetime
import json
import os
import threading
from typing import Dict, Optional, Callable


class AsyncUIUpdater(QThread):
    """异步UI更新线程"""
    update_completed = pyqtSignal(bool)  # 更新完成信号
    
    def __init__(self, update_func: Callable, *args, **kwargs):
        super().__init__()
        self.update_func = update_func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        """在后台线程执行UI更新"""
        try:
            self.update_func(*self.args, **self.kwargs)
            self.update_completed.emit(True)
        except Exception as e:
            print(f"异步UI更新失败: {e}")
            self.update_completed.emit(False)


class StyleCache:
    """样式缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, str]] = {}
        self._prerendered = False
    
    def prerender_styles(self):
        """预渲染所有样式"""
        if self._prerendered:
            return
            
        print("🎨 开始预渲染样式...")
        
        # 深色模式样式
        self._cache['dark'] = {
            'input_bar_features_btn': """
                QPushButton { 
                    background: rgba(40, 40, 40, 0.9); 
                    color: white; 
                    font-size: 14px; 
                    font-weight: bold;
                    border-radius: 10px; 
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                QPushButton:hover {
                    background: rgba(60, 60, 60, 0.9);
                }
                QPushButton:pressed { 
                    background: rgba(20, 20, 20, 0.9); 
                }
            """,
            'input_bar_input_line': """
                background: rgba(40, 40, 40, 0.9); 
                border: 2px solid rgba(255, 255, 255, 0.3); 
                color: white; 
                font-size: 16px; 
                border-radius: 12px; 
                padding: 8px 12px;
            """,
            'input_bar_send_btn': """
                QPushButton { 
                    background: rgba(34, 139, 34, 0.9); 
                    color: white; 
                    font-size: 14px; 
                    font-weight: bold;
                    border-radius: 10px; 
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                QPushButton:hover {
                    background: rgba(60, 179, 60, 0.9);
                }
                QPushButton:pressed { 
                    background: rgba(0, 128, 0, 0.9); 
                }
            """,
            'input_bar_container': """
                background: rgba(30, 30, 30, 0.4); 
                border-radius: 20px; 
                border: 2px solid rgba(255, 255, 255, 0.2);
            """,
            'sidebar_new_chat_button': """
                QPushButton {
                    background: rgba(40, 40, 40, 0.9);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(60, 60, 60, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.4);
                }
                QPushButton:pressed {
                    background: rgba(20, 20, 20, 0.9);
                }
            """,
            'sidebar_container': """
                QWidget {
                    background: rgba(20, 20, 20, 0.3);
                    border-radius: 15px;
                    border: 2px solid rgba(255, 255, 255, 0.1);
                }
            """
        }
        
        # 浅色模式样式
        self._cache['light'] = {
            'input_bar_features_btn': """
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
            """,
            'input_bar_input_line': """
                background: rgba(255,255,255,0.9); 
                border: 2px solid rgba(100, 149, 237, 0.3); 
                color: #222; 
                font-size: 16px; 
                border-radius: 12px; 
                padding: 8px 12px;
            """,
            'input_bar_send_btn': """
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
            """,
            'input_bar_container': """
                background: rgba(255,255,255,0.25); 
                border-radius: 20px; 
                border: 2px solid rgba(255,255,255,0.3);
            """,
            'sidebar_new_chat_button': """
                QPushButton {
                    background: rgba(100, 149, 237, 0.8);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(72, 118, 255, 0.9);
                }
                QPushButton:pressed {
                    background: rgba(30, 90, 200, 0.9);
                }
            """,
            'sidebar_container': """
                background: rgba(255,255,255,0.25); 
                border-radius: 15px; 
                border: 2px solid rgba(255,255,255,0.3);
            """
        }
        
        self._prerendered = True
        print("[OK] 样式预渲染完成")
    
    def get_style(self, theme: str, component: str) -> str:
        """获取缓存的样式"""
        if not self._prerendered:
            self.prerender_styles()
        
        return self._cache.get(theme, {}).get(component, "")


class EnhancedThemeManager(QObject):
    """增强的主题管理器 - 支持预渲染和异步更新"""
    theme_changed = pyqtSignal(bool)  # 深色模式状态变化信号
    theme_change_started = pyqtSignal()  # 主题切换开始信号
    theme_change_completed = pyqtSignal()  # 主题切换完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.dark_mode_enabled = False
        self.auto_dark_mode = False
        self.custom_background_path = ""
        self.is_video_background = False  # 新增：是否为视频背景
        
        # 状态管理
        self._is_updating = False
        self._update_lock = threading.Lock()
        self._pending_updates = []
        
        # 样式缓存
        self.style_cache = StyleCache()
        
        # 自动模式定时器
        self.auto_mode_timer = QTimer()
        self.auto_mode_timer.timeout.connect(self.check_auto_dark_mode)
        
        # 异步更新器
        self.async_updater = None
        
        # 立即预渲染样式
        self.style_cache.prerender_styles()
        
        # 加载设置
        self.load_settings()
        
    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window
        
    def enable_dark_mode_fast(self, enabled=True):
        """快速响应的深色模式切换"""
        # 立即更新按钮状态，提供即时反馈
        self._update_button_state_immediately(enabled)
        
        # 异步执行实际的主题切换
        self._schedule_theme_update(enabled)
        
    def _update_button_state_immediately(self, enabled: bool):
        """立即更新按钮状态，提供即时反馈"""
        if self.dark_mode_enabled == enabled:
            return
            
        print(f"⚡ 立即更新按钮状态: {'深色' if enabled else '浅色'}")
        
        # 发射信号，让UI立即响应
        self.theme_change_started.emit()
        
        # 更新内部状态
        self.dark_mode_enabled = enabled
        
        # 立即发射主题变化信号
        self.theme_changed.emit(enabled)
        
    def _schedule_theme_update(self, enabled: bool):
        """调度主题更新任务"""
        with self._update_lock:
            if self._is_updating:
                # 如果正在更新，将新请求加入队列
                self._pending_updates.append(enabled)
                print(f"📋 主题更新任务已排队: {'深色' if enabled else '浅色'}")
                return
            
            self._is_updating = True
        
        # 创建异步更新任务
        self.async_updater = AsyncUIUpdater(self._apply_theme_async, enabled)
        self.async_updater.update_completed.connect(self._on_update_completed)
        self.async_updater.start()
        
    def _apply_theme_async(self, enabled: bool):
        """在后台线程执行主题应用"""
        print(f"🎨 异步应用主题: {'深色' if enabled else '浅色'}")
        
        # 在主线程中执行UI更新
        QTimer.singleShot(0, lambda: self._apply_theme_to_ui(enabled))
        
    def _apply_theme_to_ui(self, enabled: bool):
        """在主线程中应用主题到UI"""
        if not self.main_window:
            return
            
        try:
            theme_name = 'dark' if enabled else 'light'
            
            # 快速应用预渲染的样式
            self._apply_cached_styles(theme_name)
            
            # 设置标题栏
            if enabled:
                self.set_dark_title_bar()
            else:
                self.set_light_title_bar()
            
            # 保存设置
            self.save_settings()
            
            print(f"[OK] 主题UI更新完成: {theme_name}")
            
        except Exception as e:
            print(f"[ERROR] 主题UI更新失败: {e}")
            
    def _apply_cached_styles(self, theme_name: str):
        """应用缓存的样式"""
        if not self.main_window:
            return
            
        # 更新输入栏样式
        if hasattr(self.main_window, 'input_bar') and self.main_window.input_bar:
            input_bar = self.main_window.input_bar
            
            # 功能按钮
            if hasattr(input_bar, 'features_btn'):
                style = self.style_cache.get_style(theme_name, 'input_bar_features_btn')
                input_bar.features_btn.setStyleSheet(style)
            
            # 输入框
            if hasattr(input_bar, 'input_line'):
                style = self.style_cache.get_style(theme_name, 'input_bar_input_line')
                input_bar.input_line.setStyleSheet(style)
            
            # 发送按钮
            if hasattr(input_bar, 'send_btn') and not getattr(input_bar, 'is_waiting_response', False):
                style = self.style_cache.get_style(theme_name, 'input_bar_send_btn')
                input_bar.send_btn.setStyleSheet(style)
            
            # 容器
            container_style = self.style_cache.get_style(theme_name, 'input_bar_container')
            input_bar.setStyleSheet(container_style)
            
        # 更新侧边栏样式
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            sidebar = self.main_window.sidebar
            
            # 新建对话按钮
            if hasattr(sidebar, 'new_chat_button'):
                style = self.style_cache.get_style(theme_name, 'sidebar_new_chat_button')
                sidebar.new_chat_button.setStyleSheet(style)
            
            # 容器
            container_style = self.style_cache.get_style(theme_name, 'sidebar_container')
            sidebar.setStyleSheet(container_style)
        
        # 强制更新显示
        self.main_window.update()
        self.main_window.repaint()
        
    def _on_update_completed(self, success: bool):
        """更新完成回调"""
        with self._update_lock:
            self._is_updating = False
            
            # 处理排队的更新
            if self._pending_updates:
                next_update = self._pending_updates.pop(0)
                print(f"🔄 处理排队的更新: {'深色' if next_update else '浅色'}")
                QTimer.singleShot(10, lambda: self._schedule_theme_update(next_update))
        
        # 发射完成信号
        self.theme_change_completed.emit()
        
        if success:
            print("[OK] 主题切换完成")
        else:
            print("[ERROR] 主题切换失败")
    
    # 保持原有接口兼容性
    def enable_dark_mode(self, enabled=True):
        """原有的主题切换接口（兼容性）"""
        self.enable_dark_mode_fast(enabled)
        
    def set_auto_mode(self, enabled=True):
        """设置自动模式"""
        self.auto_dark_mode = enabled
        print(f"🔄 自动模式设置为: {enabled}")
        
        if enabled:
            # 启动定时器，每5秒检查一次
            self.auto_mode_timer.start(5000)  # 5秒检查一次
            print("⏰ 自动模式定时器已启动，每5秒检查一次")
            # 立即执行一次检查
            self.check_auto_dark_mode()
        else:
            self.auto_mode_timer.stop()
            print("⏹️ 自动模式定时器已停止")
        
        self.save_settings()
        
    def check_auto_dark_mode(self):
        """检查是否应该启用自动深色模式（18:00-6:00）"""
        if not self.auto_dark_mode:
            return
            
        current_time = datetime.datetime.now().time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # 18:00-23:59 或 0:00-6:00 为深色模式时间
        is_dark_time = (current_hour >= 18) or (current_hour < 6)
        
        print(f"🕐 当前时间: {current_hour:02d}:{current_minute:02d}")
        print(f"🌙 是否应启用深色模式: {is_dark_time}")
        print(f"🎨 当前深色模式状态: {self.dark_mode_enabled}")
        
        if is_dark_time != self.dark_mode_enabled:
            print(f"🔄 主题需要切换: {self.dark_mode_enabled} -> {is_dark_time}")
            self.enable_dark_mode_fast(is_dark_time)
            if is_dark_time:
                print("🌙 已切换到深色模式")
            else:
                print("☀️ 已切换到浅色模式")
        else:
            print("[OK] 主题状态无需更改")
    
    def set_custom_background(self, path, is_video=False):
        """设置自定义背景（支持图片和视频）
        
        Args:
            path: 背景文件路径
            is_video: 是否为视频背景
        """
        self.custom_background_path = path
        self.is_video_background = is_video
        self.apply_background()
        self.save_settings()
        
    def apply_background(self):
        """应用自定义背景（支持图片和视频）"""
        if not self.main_window or not self.custom_background_path:
            return
            
        # 检查文件是否存在
        if not os.path.exists(self.custom_background_path):
            print(f"背景文件不存在: {self.custom_background_path}")
            return
        
        try:
            if self.is_video_background:
                # 应用视频背景
                print(f"[主题管理器] 应用视频背景: {self.custom_background_path}")
                self.main_window.play_video_background(self.custom_background_path)
            else:
                # 应用静态图片背景
                print(f"[主题管理器] 应用静态图片背景: {self.custom_background_path}")
                self.main_window.set_background_static(self.custom_background_path)
                
        except Exception as e:
            print(f"应用背景失败: {e}")
            import traceback
            traceback.print_exc()
    
    def set_dark_title_bar(self):
        """设置深色标题栏（Windows特定）"""
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = int(self.main_window.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(ctypes.c_int(1)), 
                ctypes.sizeof(ctypes.c_int)
            )
        except:
            pass  # 如果失败就忽略
    
    def set_light_title_bar(self):
        """恢复浅色标题栏"""
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = int(self.main_window.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(ctypes.c_int(0)), 
                ctypes.sizeof(ctypes.c_int)
            )
        except:
            pass
    
    def save_settings(self):
        """保存设置到文件"""
        settings = {
            'dark_mode_enabled': self.dark_mode_enabled,
            'auto_dark_mode': self.auto_dark_mode,
            'custom_background_path': self.custom_background_path,
            'is_video_background': self.is_video_background  # 保存视频背景标记
        }
        
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存主题设置失败: {e}")
    
    def load_settings(self):
        """从文件加载设置"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), 'theme_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                self.dark_mode_enabled = settings.get('dark_mode_enabled', False)
                self.auto_dark_mode = settings.get('auto_dark_mode', False)
                self.custom_background_path = settings.get('custom_background_path', '')
                self.is_video_background = settings.get('is_video_background', False)  # 加载视频背景标记
                
                # 如果启用了自动模式，启动定时器
                if self.auto_dark_mode:
                    self.set_auto_mode(True)
                    
        except Exception as e:
            print(f"加载主题设置失败: {e}")


class DarkModeOverlay(QWidget):
    """深色模式蒙版组件 - 覆盖在背景图片上"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect() if parent else self.rect())
        
    def paintEvent(self, event):
        """绘制半透明灰黑蒙版"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))  # 半透明黑色蒙版