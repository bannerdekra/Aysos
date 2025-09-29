from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QMessageBox, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QEvent, QObject, pyqtSignal, QDateTime
from PyQt6.QtGui import QKeyEvent, QClipboard
import sys
import os
import time
import re
from datetime import datetime

# Simple persistent save path
AUTOSAVE_PATH = os.path.join(os.path.dirname(__file__), 'dev_notebook_autosave.txt')

class TripleClickFilter(QObject):
    tripleLeftClicked = pyqtSignal()
    tripleRightClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # separate click time lists per button
        self._click_times = {
            Qt.MouseButton.LeftButton: [],
            Qt.MouseButton.RightButton: []
        }

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() in (
            Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton
        ):
            btn = event.button()
            now = time.time()
            times = self._click_times.get(btn, [])
            times = [t for t in times if now - t < 0.25]  # keep only clicks within 0.3s
            times.append(now)
            self._click_times[btn] = times
            if len(times) >= 3:
                # reset
                self._click_times[btn] = []
                if btn == Qt.MouseButton.LeftButton:
                    self.tripleLeftClicked.emit()
                else:
                    self.tripleRightClicked.emit()
                return True
        return False


class NumberingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_number = 0

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Determine numbering for new line
            cursor = self.textCursor()
            # get text of current block (line)
            block_text = cursor.block().text()
            # try to find a leading number like "1." or "1. " or "1)"
            import re
            m = re.match(r"\s*(\d+)\s*[\.|\)\-]", block_text)
            if m:
                try:
                    num = int(m.group(1))
                except Exception:
                    num = None
            else:
                # try pattern like "1 "
                m2 = re.match(r"\s*(\d+)\s+", block_text)
                if m2:
                    try:
                        num = int(m2.group(1))
                    except Exception:
                        num = None
                else:
                    num = None

            if num is not None:
                next_num = num + 1
                super().keyPressEvent(event)
                cursor = self.textCursor()
                cursor.insertText(f"{next_num}. ")
                return
        super().keyPressEvent(event)


class DevNotebook(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('开发记事本')
        self.resize(700, 600)

        self.layout = QVBoxLayout(self)

        # top buttons
        top_layout = QHBoxLayout()
        self.theme_btn = QPushButton('切换主题')
        self.save_path_btn = QPushButton('保存路径')
        self.copy_btn = QPushButton('复制')
        top_layout.addWidget(self.theme_btn)
        top_layout.addWidget(self.save_path_btn)
        top_layout.addWidget(self.copy_btn)
        top_layout.addStretch()
        self.layout.addLayout(top_layout)

        # three sections
        self.sections = {}
        for title in ['问题|现象', '改进方向', '控制台信息']:
            # checkbox + label on one line
            h = QHBoxLayout()
            cb = QCheckBox()
            # default: only 问题|现象 checked
            if title == '问题|现象':
                cb.setChecked(True)
            else:
                cb.setChecked(False)
            lbl = QLabel(title)
            h.addWidget(cb)
            h.addWidget(lbl)
            h.addStretch()
            edit = NumberingTextEdit()
            edit.setPlaceholderText(title)
            edit.setAcceptRichText(False)
            edit.setStyleSheet('background: white; color: black;')
            self.layout.addLayout(h)
            self.layout.addWidget(edit)
            # store both edit and checkbox
            self.sections[title] = {'edit': edit, 'check': cb}

        # save and file management
        # create Data folder next to script and use as default save dir
        script_dir = os.path.dirname(__file__)
        data_dir = os.path.join(script_dir, 'Data')
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception as e:
            print('无法创建 Data 文件夹:', e)
            data_dir = script_dir
        self.save_dir = data_dir
        self.current_save_file = None
        # when True, next modification will create a new file
        self.new_file_on_next_change = False
        # when True, next new file will use first 6 chars of 改进方向 as prefix
        self.use_six_chars_for_next_save = False
        # suspend save while programmatically loading text
        self._suspend_save = False

        # theme state
        self.is_dark = False
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.save_path_btn.clicked.connect(self.choose_save_path)
        self.copy_btn.clicked.connect(self.copy_all_sections)

        # triple click filter on whole application (catch clicks anywhere)
        self.triple_filter = TripleClickFilter(self)
        self.triple_filter.tripleLeftClicked.connect(self._on_triple_left)
        self.triple_filter.tripleRightClicked.connect(self._on_triple_right)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self.triple_filter)
        else:
            # fallback to widget-level filter
            self.installEventFilter(self.triple_filter)

        # connect change signals to save on modification
        for info in self.sections.values():
            info['edit'].textChanged.connect(self.on_text_changed)

        # load previous autosave if exists
        self.load_autosave()

    def toggle_theme(self):
        if not self.is_dark:
            # softer dark: use #4f4b4b background and soft white text
            for info in self.sections.values():
                info['edit'].setStyleSheet('background: #4f4b4b; color: #f5f5f5;')
            self.setStyleSheet('background: #333; color: #f5f5f5;')
            self.is_dark = True
        else:
            for info in self.sections.values():
                info['edit'].setStyleSheet('background: white; color: black;')
            self.setStyleSheet('')
            self.is_dark = False

    def copy_all_sections(self):
        pieces = []
        for title, info in self.sections.items():
            if not info['check'].isChecked():
                continue
            txt = info['edit'].toPlainText().strip()
            if not txt:
                txt = '无'
            pieces.append(f"{title}：{txt}")
        if not pieces:
            QMessageBox.warning(self, '复制', '未选择任何模块或所选模块为空，未复制')
            return
        out = '\n'.join(pieces)
        cb: QClipboard = QApplication.clipboard()
        cb.setText(out)
        QMessageBox.information(self, '复制', '已复制到剪贴板，并保存到 Data 文件夹')
        # also save a copy into Data folder
        try:
            self._save_clip_to_data(out)
        except Exception as e:
            print('保存到 Data 失败:', e)
        # Mark that next modification should create a new file
        self.new_file_on_next_change = True

    def _on_triple_left(self):
        # triple left click: same as copy button (will also save to Data)
        self.copy_all_sections()
        # Keep legacy flag behavior for compatibility
        self.use_six_chars_for_next_save = True

    def _on_triple_right(self):
        # triple right click: clear all sections
        for info in self.sections.values():
            info['edit'].clear()
        # save cleared state
        self.save_to_file()

    def autosave(self):
        # 保留旧的 autosave 方法以兼容，但不再自动使用定时器
        try:
            with open(AUTOSAVE_PATH, 'w', encoding='utf-8') as f:
                for title, info in self.sections.items():
                    f.write(f"[{title}]\n")
                    f.write(info['edit'].toPlainText())
                    f.write('\n\n')
        except Exception as e:
            print('自动保存失败:', e)

    def choose_save_path(self):
        dirpath = QFileDialog.getExistingDirectory(self, '选择保存文件夹', os.path.expanduser('~'))
        if dirpath:
            self.save_dir = dirpath
            QMessageBox.information(self, '保存路径', f'保存目录已设置为:\n{self.save_dir}')

    def sanitize_filename(self, s: str) -> str:
        s = s.strip()
        # take first 5 characters for filename prefix (default)
        s = s[:5]
        # remove illegal filename chars
        return re.sub(r'[<>:"/\\|?*]', '_', s) or 'default'

    def save_to_file(self):
        if self._suspend_save:
            return
        # base directory (user selected or script dir)
        base = self.save_dir or os.path.dirname(__file__)
        # filename prefix from 改进方向; default 5 chars, but if use_six_chars_for_next_save True use 6
        improve_info = self.sections.get('改进方向')
        improve_text = ''
        if improve_info:
            improve_text = improve_info['edit'].toPlainText().strip()
        if improve_text:
            if self.use_six_chars_for_next_save:
                raw = improve_text[:6]
            else:
                raw = improve_text[:5]
            prefix = re.sub(r'[<>:"/\\|?*]', '_', raw) or 'notes'
        else:
            prefix = 'notes'

        if self.current_save_file is None or self.new_file_on_next_change:
            # create a new file (timestamped) or default notes
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{prefix}_{timestamp}.txt' if self.new_file_on_next_change else f'{prefix}.txt'
            self.current_save_file = os.path.join(base, filename)
            # reset flags after creating new file
            self.new_file_on_next_change = False
            self.use_six_chars_for_next_save = False

        try:
            with open(self.current_save_file, 'w', encoding='utf-8') as f:
                for title, info in self.sections.items():
                    f.write(f"{title}:\n")
                    f.write(info['edit'].toPlainText())
                    f.write('\n\n')
        except Exception as e:
            print('保存文件失败:', e)

    def on_text_changed(self):
        # called on any user modification; save immediately
        if self._suspend_save:
            return
        self.save_to_file()

    def load_autosave(self):
        if os.path.exists(AUTOSAVE_PATH):
            try:
                with open(AUTOSAVE_PATH, 'r', encoding='utf-8') as f:
                    data = f.read()
                # simple parser: split by [title]
                # reuse old autosave format
                for title in self.sections.keys():
                    marker = f"[{title}]\n"
                    if marker in data:
                        part = data.split(marker, 1)[1]
                        # find next section marker
                        next_idx = len(part)
                        for t2 in self.sections.keys():
                            if t2 == title:
                                continue
                            m = part.find(f"[{t2}]\n")
                            if m != -1 and m < next_idx:
                                next_idx = m
                        content = part[:next_idx].strip()
                        self._suspend_save = True
                        # self.sections stores dicts now
                        if title in self.sections:
                            self.sections[title]['edit'].setPlainText(content)
                        self._suspend_save = False
            except Exception as e:
                print('加载自动保存失败:', e)

    def _save_clip_to_data(self, text: str):
        # ensure data dir exists
        base = self.save_dir or os.path.dirname(__file__)
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        # prefix from 问题|现象 first 10 chars
        q_info = self.sections.get('问题|现象')
        prefix = 'clip'
        if q_info:
            raw = q_info['edit'].toPlainText().strip()[:10]
            raw = re.sub(r'[<>:"/\\|?*]', '_', raw)
            if raw:
                prefix = raw
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{timestamp}.txt"
        fullpath = os.path.join(base, filename)
        with open(fullpath, 'w', encoding='utf-8') as f:
            f.write(text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = DevNotebook()
    w.show()
    sys.exit(app.exec())
