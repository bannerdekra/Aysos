"""
创作控制面板
用于调整 Stable Diffusion 的生成参数
支持参数持久化，自动保存和加载用户习惯
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QComboBox, QTextEdit,
    QSpinBox, QGroupBox, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator
import requests
from sd_config import get_sd_config, save_sd_params


class CreationPanel(QDialog):
    """创作控制面板"""
    
    # 信号：当用户点击"应用"时，发送所有参数
    params_applied = pyqtSignal(dict)
    
    # 采样器列表
    SAMPLERS = [
        "DPM++ 2M",
        "DPM++ SDE",
        "DPM++ 2M SDE",
        "DPM++ 2M SDE Heun",
        "DPM++ 2S a",
        "DPM++ 3M SDE",
        "Euler a",
        "Euler",
        "LMS",
        "Heun",
        "DPM2",
        "DPM2 a",
        "DPM fast",
        "DPM adaptive",
        "Restart",
        "DDIM",
        "DDIM CFG++",
        "PLMS",
        "UniPC",
        "LCM"
    ]
    
    # 调度器列表
    SCHEDULERS = [
        "自动",
        "Uniform",
        "Karras",
        "Exponential",
        "Polyexponential",
        "SGM Uniform",
        "KL Optimal",
        "Align Your Steps",
        "单一值",
        "Normal",
        "DDIM",
        "Beta"
    ]
    
    def __init__(self, parent=None, current_params=None):
        """
        初始化创作控制面板
        
        Args:
            parent: 父窗口
            current_params: 当前参数字典（如果提供，会覆盖保存的配置）
        """
        super().__init__(parent)
        
        # 加载保存的配置
        sd_config = get_sd_config()
        self.default_params = sd_config.get_all()
        
        # 如果提供了当前参数，更新配置
        if current_params:
            self.default_params.update(current_params)
        
        self.init_ui()
        self.load_params(self.default_params)
    
    def init_ui(self):
        """初始化UI - 紧凑布局优化版"""
        self.setWindowTitle("创作控制面板")
        self.setFixedSize(600, 680)  # 🔧 减小高度（800->680）
        self.setModal(True)  # 模态对话框
        
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(240, 248, 255, 1.0),
                    stop:1 rgba(230, 240, 255, 1.0));
            }
            QLabel {
                color: #2c3e50;
                font-size: 12px;
            }
            QTextEdit {
                background: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 11px;
            }
            QTextEdit:focus {
                border: 2px solid #3498db;
            }
            QComboBox {
                background: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 11px;
                min-height: 30px;
            }
            QComboBox:focus {
                border: 2px solid #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #2c3e50;
                margin-right: 5px;
            }
            QSlider::groove:horizontal {
                background: #bdc3c7;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
                border: 2px solid white;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5dade2, stop:1 #3498db);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #5dade2);
                border-radius: 3px;
            }
            QSpinBox {
                background: white;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 11px;
                min-height: 25px;
            }
            QSpinBox:focus {
                border: 2px solid #3498db;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)  # 🔧 减小间距（10->6）
        main_layout.setContentsMargins(15, 8, 15, 12)  # 🔧 减小边距（20,20,20,20 -> 15,8,15,12）
        
        # 标题 - 更紧凑
        title = QLabel("🎨 创作控制面板")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding: 3px;
        """)  # 🔧 减小标题字体和padding（18px,10px -> 16px,3px）
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # 1. 提示词区域（并排，更紧凑，无外框）
        prompts_layout = QHBoxLayout()
        
        # 正向提示词
        positive_container = QVBoxLayout()
        positive_container.setSpacing(3)  # 🔧 减小内部间距
        positive_header = QHBoxLayout()
        positive_title = QLabel("正向提示词")
        positive_title.setStyleSheet("""
            font-weight: bold;
            color: #3498db;
            font-size: 12px;
        """)  # 🔧 减小字体（13px->12px）
        self.positive_word_count = QLabel("0/75")
        self.positive_word_count.setStyleSheet("""
            font-weight: bold;
            color: #7f8c8d;
            font-size: 11px;
        """)  # 🔧 减小字体（12px->11px）
        positive_header.addWidget(positive_title)
        positive_header.addStretch()
        positive_header.addWidget(self.positive_word_count)
        positive_container.addLayout(positive_header)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setFixedHeight(60)  # 🔧 减小高度（70->60）
        self.prompt_edit.setPlaceholderText("输入正向提示词...")
        self.prompt_edit.textChanged.connect(self.update_positive_word_count)
        positive_container.addWidget(self.prompt_edit)
        
        # 负向提示词
        negative_container = QVBoxLayout()
        negative_container.setSpacing(3)  # 🔧 减小内部间距
        negative_header = QHBoxLayout()
        negative_title = QLabel("负向提示词")
        negative_title.setStyleSheet("""
            font-weight: bold;
            color: #e74c3c;
            font-size: 12px;
        """)  # 🔧 减小字体（13px->12px）
        self.negative_word_count = QLabel("0/75")
        self.negative_word_count.setStyleSheet("""
            font-weight: bold;
            color: #7f8c8d;
            font-size: 11px;
        """)  # 🔧 减小字体（12px->11px）
        negative_header.addWidget(negative_title)
        negative_header.addStretch()
        negative_header.addWidget(self.negative_word_count)
        negative_container.addLayout(negative_header)
        
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setFixedHeight(60)  # 🔧 减小高度（70->60）
        self.negative_prompt_edit.setPlaceholderText("输入负向提示词...")
        self.negative_prompt_edit.textChanged.connect(self.update_negative_word_count)
        negative_container.addWidget(self.negative_prompt_edit)
        
        prompts_layout.addLayout(positive_container)
        prompts_layout.addLayout(negative_container)
        main_layout.addLayout(prompts_layout)
        
        # 1.5 模型选择（新增）
        model_layout = QHBoxLayout()
        model_label = QLabel("选择模型:")
        model_label.setStyleSheet("font-weight: bold;")
        self.model_combo = QComboBox()
        self.model_combo.setPlaceholderText("加载中...")
        
        # 刷新按钮
        refresh_model_btn = QPushButton("🔄")
        refresh_model_btn.setFixedSize(35, 35)
        refresh_model_btn.setToolTip("刷新模型列表")
        refresh_model_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        refresh_model_btn.clicked.connect(self.refresh_models)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(refresh_model_btn)
        main_layout.addLayout(model_layout)
        
        # 自动加载模型列表
        self.refresh_models()
        
        # 2. 采样方式与调度类型（并排）
        sampler_layout = QHBoxLayout()
        
        # 采样方式
        sampler_label = QLabel("采样方式:")
        sampler_label.setStyleSheet("font-weight: bold;")
        self.sampler_combo = QComboBox()
        self.sampler_combo.addItems(self.SAMPLERS)
        self.sampler_combo.setCurrentText("DPM++ 2M")
        
        sampler_layout.addWidget(sampler_label)
        sampler_layout.addWidget(self.sampler_combo, 1)
        
        # 调度类型
        scheduler_label = QLabel("调度类型:")
        scheduler_label.setStyleSheet("font-weight: bold;")
        self.scheduler_combo = QComboBox()
        self.scheduler_combo.addItems(self.SCHEDULERS)
        self.scheduler_combo.setCurrentText("Karras")
        
        sampler_layout.addWidget(scheduler_label)
        sampler_layout.addWidget(self.scheduler_combo, 1)
        
        main_layout.addLayout(sampler_layout)
        
        # 3. 迭代步数（可编辑）
        steps_layout = QHBoxLayout()
        steps_label = QLabel("迭代步数:")
        steps_label.setStyleSheet("font-weight: bold;")
        self.steps_slider = QSlider(Qt.Orientation.Horizontal)
        self.steps_slider.setRange(1, 150)
        self.steps_slider.setValue(20)
        
        # 可编辑的数值框（无按钮）
        self.steps_spinbox = QSpinBox()
        self.steps_spinbox.setRange(1, 150)
        self.steps_spinbox.setValue(20)
        self.steps_spinbox.setFixedWidth(60)
        self.steps_spinbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.steps_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # 移除加减按钮
        
        # 双向绑定
        self.steps_slider.valueChanged.connect(self.steps_spinbox.setValue)
        self.steps_spinbox.valueChanged.connect(self.steps_slider.setValue)
        
        # 鼠标滚轮支持（精度1）
        self.steps_slider.wheelEvent = lambda e: self._handle_wheel(e, self.steps_slider, 1, 150, 1)
        
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(self.steps_slider, 1)
        steps_layout.addWidget(self.steps_spinbox)
        main_layout.addLayout(steps_layout)
        
        # 4. 宽度滑动条（可编辑）
        width_layout = QHBoxLayout()
        width_label = QLabel("宽度:")
        width_label.setStyleSheet("font-weight: bold;")
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(256, 1024)
        self.width_slider.setSingleStep(64)
        self.width_slider.setValue(512)
        
        # 可编辑的数值框（无按钮）
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(256, 1024)
        self.width_spinbox.setSingleStep(64)
        self.width_spinbox.setValue(512)
        self.width_spinbox.setFixedWidth(60)
        self.width_spinbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.width_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # 移除加减按钮
        
        # 双向绑定
        self.width_slider.valueChanged.connect(self.width_spinbox.setValue)
        self.width_spinbox.valueChanged.connect(self.width_slider.setValue)
        
        # 鼠标滚轮支持（精度1）
        self.width_slider.wheelEvent = lambda e: self._handle_wheel(e, self.width_slider, 256, 1024, 1)
        
        width_layout.addWidget(width_label)
        width_layout.addWidget(self.width_slider, 1)
        width_layout.addWidget(self.width_spinbox)
        main_layout.addLayout(width_layout)
        
        # 5. 高度滑动条（可编辑）
        height_layout = QHBoxLayout()
        height_label = QLabel("高度:")
        height_label.setStyleSheet("font-weight: bold;")
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(256, 1024)
        self.height_slider.setSingleStep(64)
        self.height_slider.setValue(512)
        
        # 可编辑的数值框（无按钮）
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(256, 1024)
        self.height_spinbox.setSingleStep(64)
        self.height_spinbox.setValue(512)
        self.height_spinbox.setFixedWidth(60)
        self.height_spinbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.height_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # 移除加减按钮
        
        # 双向绑定
        self.height_slider.valueChanged.connect(self.height_spinbox.setValue)
        self.height_spinbox.valueChanged.connect(self.height_slider.setValue)
        
        # 鼠标滚轮支持（精度1）
        self.height_slider.wheelEvent = lambda e: self._handle_wheel(e, self.height_slider, 256, 1024, 1)
        
        height_layout.addWidget(height_label)
        height_layout.addWidget(self.height_slider, 1)
        height_layout.addWidget(self.height_spinbox)
        main_layout.addLayout(height_layout)
        
        # 6. 提示词服从度滑动条（支持0.5精度）
        cfg_layout = QHBoxLayout()
        cfg_label = QLabel("提示词服从度:")
        cfg_label.setStyleSheet("font-weight: bold;")
        self.cfg_slider = QSlider(Qt.Orientation.Horizontal)
        self.cfg_slider.setRange(10, 300)  # 1.0-30.0, 步进0.1
        self.cfg_slider.setValue(70)  # 7.0
        
        # 可编辑的数值框（支持0.5精度，无按钮）
        from PyQt6.QtWidgets import QDoubleSpinBox
        self.cfg_spinbox = QDoubleSpinBox()
        self.cfg_spinbox.setRange(1.0, 30.0)
        self.cfg_spinbox.setSingleStep(0.5)  # 步进0.5
        self.cfg_spinbox.setDecimals(1)
        self.cfg_spinbox.setValue(7.0)
        self.cfg_spinbox.setFixedWidth(60)
        self.cfg_spinbox.setStyleSheet("font-weight: bold; color: #3498db;")
        self.cfg_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)  # 移除加减按钮
        
        # 双向绑定（需要转换，支持0.5精度）
        def slider_to_spinbox(v):
            # 滑动条值转为0.5的倍数
            value = round(v / 10.0 * 2) / 2  # 四舍五入到0.5
            self.cfg_spinbox.setValue(value)
        
        def spinbox_to_slider(v):
            # spinbox值转为滑动条值
            self.cfg_slider.setValue(int(v * 10))
        
        self.cfg_slider.valueChanged.connect(slider_to_spinbox)
        self.cfg_spinbox.valueChanged.connect(spinbox_to_slider)
        
        # 鼠标滚轮支持（精度0.5，即滑动条移动5）
        self.cfg_slider.wheelEvent = lambda e: self._handle_wheel(e, self.cfg_slider, 10, 300, 5)
        
        cfg_layout.addWidget(cfg_label)
        cfg_layout.addWidget(self.cfg_slider, 1)
        cfg_layout.addWidget(self.cfg_spinbox)
        main_layout.addLayout(cfg_layout)
        
        # 7. 随机数种子
        seed_layout = QHBoxLayout()
        seed_label = QLabel("随机数种子:")
        seed_label.setStyleSheet("font-weight: bold;")
        self.seed_spinbox = QSpinBox()
        self.seed_spinbox.setRange(-1, 2147483647)
        self.seed_spinbox.setValue(-1)
        self.seed_spinbox.setSpecialValueText("随机")
        seed_info = QLabel("(-1 为随机)")
        seed_info.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        
        seed_layout.addWidget(seed_label)
        seed_layout.addWidget(self.seed_spinbox, 1)
        seed_layout.addWidget(seed_info)
        main_layout.addLayout(seed_layout)
        
        # 8. 应用和取消按钮（并排，更紧凑）
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)  # 🔧 设置按钮间距
        buttons_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(90, 36)  # 🔧 减小按钮尺寸（100x40 -> 90x36）
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #95a5a6, stop:1 #7f8c8d);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7f8c8d, stop:1 #6c7a7b);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.setFixedSize(90, 36)  # 🔧 减小按钮尺寸（100x40 -> 90x36）
        apply_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        apply_btn.clicked.connect(self.apply_params)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(apply_btn)
        buttons_layout.addStretch()
        
        main_layout.addSpacing(5)  # 🔧 减小底部间距（10->5）
        main_layout.addLayout(buttons_layout)
    
    def _handle_wheel(self, event, slider, min_val, max_val, step):
        """处理滚轮事件"""
        delta = event.angleDelta().y()
        current = slider.value()
        
        if delta > 0:  # 向上滚
            new_value = min(current + step, max_val)
        else:  # 向下滚
            new_value = max(current - step, min_val)
        
        slider.setValue(new_value)
        event.accept()
    
    def refresh_models(self):
        """从SD WebUI获取可用模型列表"""
        try:
            # 清空当前列表
            self.model_combo.clear()
            self.model_combo.addItem("加载中...")
            
            # 🚨 绕过代理，直连本地 SD WebUI
            no_proxy = {'http': None, 'https': None}
            
            # 获取模型列表
            response = requests.get(
                "http://127.0.0.1:7860/sdapi/v1/sd-models",
                timeout=5,
                proxies=no_proxy
            )
            
            if response.status_code == 200:
                models = response.json()
                self.model_combo.clear()
                
                if not models:
                    self.model_combo.addItem("未找到模型")
                    return
                
                # 添加模型到下拉列表
                for model in models:
                    model_name = model.get('title', model.get('model_name', '未知'))
                    self.model_combo.addItem(model_name)
                
                print(f"[OK] 加载了 {len(models)} 个模型")
            else:
                self.model_combo.clear()
                self.model_combo.addItem("加载失败")
                print(f"[ERROR] 获取模型列表失败: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.model_combo.clear()
            self.model_combo.addItem("SD WebUI 未运行")
            print("[ERROR] 无法连接到 SD WebUI")
        except Exception as e:
            self.model_combo.clear()
            self.model_combo.addItem("加载失败")
            print(f"[ERROR] 获取模型列表异常: {e}")
    
    def load_params(self, params: dict):
        """加载参数到UI"""
        self.prompt_edit.setPlainText(params.get("prompt", ""))
        self.negative_prompt_edit.setPlainText(params.get("negative_prompt", ""))
        
        sampler = params.get("sampler_name", "DPM++ 2M")
        if sampler in self.SAMPLERS:
            self.sampler_combo.setCurrentText(sampler)
        
        scheduler = params.get("scheduler", "Karras")
        if scheduler in self.SCHEDULERS:
            self.scheduler_combo.setCurrentText(scheduler)
        
        self.steps_spinbox.setValue(params.get("steps", 20))
        self.cfg_spinbox.setValue(params.get("cfg_scale", 7.0))
        self.seed_spinbox.setValue(params.get("seed", -1))
        self.width_spinbox.setValue(params.get("width", 512))
        self.height_spinbox.setValue(params.get("height", 512))
        
        # 加载模型（如果有）
        if params.get("model"):
            index = self.model_combo.findText(params["model"])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
    
    def get_params(self) -> dict:
        """获取当前UI的参数"""
        params = {
            "prompt": self.prompt_edit.toPlainText().strip(),
            "negative_prompt": self.negative_prompt_edit.toPlainText().strip(),
            "sampler_name": self.sampler_combo.currentText(),
            "scheduler": self.scheduler_combo.currentText(),
            "steps": self.steps_spinbox.value(),
            "cfg_scale": self.cfg_spinbox.value(),
            "seed": self.seed_spinbox.value(),
            "width": self.width_spinbox.value(),
            "height": self.height_spinbox.value()
        }
        
        # 添加模型（如果不是错误消息）
        model_text = self.model_combo.currentText()
        if model_text and model_text not in ["加载中...", "加载失败", "SD WebUI 未运行", "未找到模型"]:
            params["model"] = model_text
        
        return params
    
    def apply_params(self):
        """应用参数"""
        params = self.get_params()
        
        # 验证提示词长度（75个单词限制）
        def count_words(text):
            if not text:
                return 0
            return len(text.replace(',', '').split())
        
        pos_words = count_words(params["prompt"])
        neg_words = count_words(params["negative_prompt"])
        
        if pos_words > 75:
            QMessageBox.warning(
                self, 
                "提示词过长", 
                f"正向提示词超过75个单词限制！\n当前: {pos_words} 个单词"
            )
            return
        
        if neg_words > 75:
            QMessageBox.warning(
                self, 
                "提示词过长", 
                f"负向提示词超过75个单词限制！\n当前: {neg_words} 个单词"
            )
            return
        
        # 保存参数到配置文件（自动持久化）
        print("[创作面板] 保存参数到配置...")
        save_sd_params(params)
        
        # 发送信号
        self.params_applied.emit(params)
        self.accept()
    
    def count_words(self, text: str) -> int:
        """计算单词数量"""
        if not text:
            return 0
        # 移除逗号，然后按空格分割
        return len(text.replace(',', '').split())
    
    def update_positive_word_count(self):
        """更新正向提示词的单词计数"""
        text = self.prompt_edit.toPlainText()
        word_count = self.count_words(text)
        
        # 根据数量设置颜色
        if word_count > 75:
            color = "#e74c3c"  # 红色，超出限制
        elif word_count > 60:
            color = "#f39c12"  # 橙色，接近限制
        else:
            color = "#7f8c8d"  # 灰色，正常
        
        self.positive_word_count.setText(f"{word_count}/75")
        self.positive_word_count.setStyleSheet(f"""
            font-weight: bold;
            color: {color};
            font-size: 12px;
        """)
    
    def update_negative_word_count(self):
        """更新负向提示词的单词计数"""
        text = self.negative_prompt_edit.toPlainText()
        word_count = self.count_words(text)
        
        # 根据数量设置颜色
        if word_count > 75:
            color = "#e74c3c"  # 红色，超出限制
        elif word_count > 60:
            color = "#f39c12"  # 橙色，接近限制
        else:
            color = "#7f8c8d"  # 灰色，正常
        
        self.negative_word_count.setText(f"{word_count}/75")
        self.negative_word_count.setStyleSheet(f"""
            font-weight: bold;
            color: {color};
            font-size: 12px;
        """)