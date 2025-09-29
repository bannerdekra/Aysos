from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QPainter, QColor
import datetime
import json
import os


class ThemeManager(QObject):
    """主题管理器 - 处理深色模式和主题切换"""
    theme_changed = pyqtSignal(bool)  # 深色模式状态变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.dark_mode_enabled = False
        self.auto_dark_mode = False
        self.custom_background_path = ""
        
        # 自动模式定时器
        self.auto_mode_timer = QTimer()
        self.auto_mode_timer.timeout.connect(self.check_auto_dark_mode)
        
        # 加载设置
        self.load_settings()
        
    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window
        
    def enable_dark_mode(self, enabled=True):
        """启用/禁用深色模式"""
        if self.dark_mode_enabled == enabled:
            return
        
        print(f"🎨 正在切换主题模式: {'深色' if enabled else '浅色'}")
        self.dark_mode_enabled = enabled
        
        # 应用主题
        self.apply_theme()
        
        # 保存设置
        self.save_settings()
        
        # 发射信号
        self.theme_changed.emit(enabled)
        
        # 强制刷新主窗口和所有子组件
        if self.main_window:
            print("🔄 正在刷新UI组件...")
            
            # 更新主窗口
            self.main_window.update()
            self.main_window.repaint()
            
            # 更新输入栏
            if hasattr(self.main_window, 'input_bar') and self.main_window.input_bar:
                self.main_window.input_bar.update()
                self.main_window.input_bar.repaint()
            
            # 更新侧边栏
            if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
                self.main_window.sidebar.update()
                self.main_window.sidebar.repaint()
            
            # 更新聊天区域
            if hasattr(self.main_window, 'chat_area') and self.main_window.chat_area:
                self.main_window.chat_area.update()
                self.main_window.chat_area.repaint()
            
            # 递归更新所有子组件
            self._update_all_children(self.main_window)
            
            print("✅ UI刷新完成")
    
    def _update_all_children(self, widget):
        """递归更新所有子组件"""
        for child in widget.findChildren(QWidget):
            child.update()
            child.repaint()
        
    def set_auto_mode(self, enabled=True):
        """设置自动模式"""
        self.auto_dark_mode = enabled
        print(f"🔄 自动模式设置为: {enabled}")
        
        if enabled:
            # 启动定时器，每5秒检查一次，提高响应速度
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
            self.enable_dark_mode(is_dark_time)
            if is_dark_time:
                print("🌙 已切换到深色模式")
            else:
                print("☀️ 已切换到浅色模式")
        else:
            print("✅ 主题状态无需更改")
    
    def set_custom_background(self, path):
        """设置自定义背景"""
        self.custom_background_path = path
        self.apply_background()
        self.save_settings()
        
    def apply_theme(self):
        """应用主题到所有UI组件"""
        if not self.main_window:
            return
        
        print(f"🎨 应用{'深色' if self.dark_mode_enabled else '浅色'}主题")
        
        if self.dark_mode_enabled:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        
        print("✅ 主题应用完成")
            
    def apply_dark_theme(self):
        """应用深色主题"""
        if not self.main_window:
            return
        
        print("🌙 应用深色主题样式")
        
        # 应用各组件的深色样式
        if hasattr(self.main_window, 'input_bar') and self.main_window.input_bar:
            self.apply_dark_input_bar_style()
        
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            self.apply_dark_sidebar_style()
        
        # 设置深色标题栏（Windows）
        self.set_dark_title_bar()
        
        # 触发重绘以显示蒙版
        self.main_window.update()
        self.main_window.repaint()
        
    def apply_light_theme(self):
        """应用浅色主题"""
        if not self.main_window:
            return
        
        print("☀️ 应用浅色主题样式")
        
        # 应用各组件的浅色样式
        if hasattr(self.main_window, 'input_bar') and self.main_window.input_bar:
            self.apply_light_input_bar_style()
        
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            self.apply_light_sidebar_style()
        
        # 设置浅色标题栏（Windows）
        self.set_light_title_bar()
        
        # 触发重绘以移除蒙版
        self.main_window.update()
        self.main_window.repaint()
    
    def apply_dark_input_bar_style(self):
        """应用深色输入栏样式"""
        input_bar = self.main_window.input_bar
        
        # 功能按钮深色样式
        input_bar.features_btn.setStyleSheet("""
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
        """)
        
        # 输入框深色样式
        input_bar.input_line.setStyleSheet("""
            background: rgba(40, 40, 40, 0.9); 
            border: 2px solid rgba(255, 255, 255, 0.3); 
            color: white; 
            font-size: 16px; 
            border-radius: 12px; 
            padding: 8px 12px;
        """)
        
        # 发送按钮深色样式（保持原色调但调整透明度）
        if not input_bar.is_waiting_response:
            input_bar.send_btn.setStyleSheet("""
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
            """)
        
        # 输入栏容器深色样式
        input_bar.setStyleSheet("""
            background: rgba(30, 30, 30, 0.4); 
            border-radius: 20px; 
            border: 2px solid rgba(255, 255, 255, 0.2);
        """)
    
    def apply_light_input_bar_style(self):
        """恢复浅色输入栏样式"""
        input_bar = self.main_window.input_bar
        
        # 恢复功能按钮原样式
        input_bar.features_btn.setStyleSheet("""
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
        
        # 恢复输入框原样式
        input_bar.input_line.setStyleSheet("""
            background: rgba(255,255,255,0.9); 
            border: 2px solid rgba(100, 149, 237, 0.3); 
            color: #222; 
            font-size: 16px; 
            border-radius: 12px; 
            padding: 8px 12px;
        """)
        
        # 恢复发送按钮原样式
        if not input_bar.is_waiting_response:
            input_bar.send_btn.setStyleSheet("""
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
        
        # 恢复输入栏容器原样式
        input_bar.setStyleSheet("""
            background: rgba(255,255,255,0.25); 
            border-radius: 20px; 
            border: 2px solid rgba(255,255,255,0.3);
        """)
    
    def apply_dark_sidebar_style(self):
        """应用深色侧边栏样式"""
        sidebar = self.main_window.sidebar
        
        # 新建对话按钮深色样式
        sidebar.new_chat_button.setStyleSheet("""
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
        """)
        
        # 侧边栏容器深色样式
        sidebar.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.3);
                border-radius: 15px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
    
    def apply_light_sidebar_style(self):
        """恢复浅色侧边栏样式"""
        sidebar = self.main_window.sidebar
        
        # 恢复新建对话按钮原样式
        sidebar.new_chat_button.setStyleSheet("""
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
        """)
        
        # 恢复侧边栏容器原样式
        sidebar.setStyleSheet("""
            background: rgba(255,255,255,0.25); 
            border-radius: 15px; 
            border: 2px solid rgba(255,255,255,0.3);
        """)
    
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
    
    def apply_background(self):
        """应用自定义背景"""
        if not self.main_window or not self.custom_background_path:
            return
            
        # 检查文件是否存在
        if not os.path.exists(self.custom_background_path):
            print(f"背景文件不存在: {self.custom_background_path}")
            return
            
        # 更新主窗口的背景图片
        try:
            from PyQt6.QtGui import QPixmap
            new_pixmap = QPixmap(self.custom_background_path)
            if not new_pixmap.isNull():
                self.main_window.bg_pixmap = new_pixmap
                self.main_window.update()  # 触发重绘
                self.main_window.repaint()  # 强制重绘
                print(f"背景已更新: {self.custom_background_path}")
            else:
                print(f"无法加载背景图片: {self.custom_background_path}")
        except Exception as e:
            print(f"应用背景失败: {e}")
    
    def save_settings(self):
        """保存设置到文件"""
        settings = {
            'dark_mode_enabled': self.dark_mode_enabled,
            'auto_dark_mode': self.auto_dark_mode,
            'custom_background_path': self.custom_background_path
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