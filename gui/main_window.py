"""主窗口 —— 音频转写 / 文本校对 双模式"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTabWidget,
    QPushButton, QLabel, QProgressBar, QFileDialog, QMessageBox,
    QTextEdit, QCheckBox, QListWidgetItem,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor

from gui.asr_settings import ASRSettingsWidget
from gui.llm_settings import LLMSettingsWidget
from config import load_config, save_config
from engine.asr import OMLXASR
from engine.llm import OpenAICompatibleLLM
from engine.processor import AudioProcessor
from engine.text_processor import TextProcessor


# ── workers ──────────────────────────────────────────────

class AudioWorker(QThread):
    progress = pyqtSignal(str, str)
    current_file = pyqtSignal(str)
    file_done = pyqtSignal(str, str, bool)
    all_done = pyqtSignal()

    def __init__(self, processor: AudioProcessor, files: list[str]):
        super().__init__()
        self.processor = processor
        self.files = files

    def run(self):
        import time
        for f in self.files:
            self.current_file.emit(f)
            t0 = time.time()
            def cb(stage, msg): self.progress.emit(stage, msg)
            r = self.processor.process(f, progress_callback=cb)
            elapsed = time.time() - t0
            dur = f"{int(elapsed//60)}分{int(elapsed%60)}秒" if elapsed >= 60 else f"{elapsed:.0f}秒"
            detail = r.output_path if r.success else f"错误: {r.error}"
            self.file_done.emit(f, f"{detail}\n  用时: {dur}", r.success)
        self.all_done.emit()

    def stop(self):
        self.processor.stop()


class TextWorker(QThread):
    progress = pyqtSignal(str, str)
    current_file = pyqtSignal(str)
    file_done = pyqtSignal(str, str, bool)
    all_done = pyqtSignal()

    def __init__(self, processor: TextProcessor, files: list[str]):
        super().__init__()
        self.processor = processor
        self.files = files

    def run(self):
        import time
        for f in self.files:
            self.current_file.emit(f)
            t0 = time.time()
            def cb(stage, msg): self.progress.emit(stage, msg)
            r = self.processor.process(f, progress_callback=cb)
            elapsed = time.time() - t0
            dur = f"{int(elapsed//60)}分{int(elapsed%60)}秒" if elapsed >= 60 else f"{elapsed:.0f}秒"
            detail = r.output_path if r.success else f"错误: {r.error}"
            self.file_done.emit(f, f"{detail}\n  用时: {dur}", r.success)
        self.all_done.emit()

    def stop(self):
        self.processor.stop()


# ── file panel helper ────────────────────────────────────

class FilePanel:
    """封装文件列表 + 操作按钮 + 颜色标记"""
    def __init__(self, parent, filter_str: str, add_btn: QPushButton,
                 remove_btn: QPushButton, clear_btn: QPushButton,
                 file_list: QListWidget):
        self._parent = parent
        self._filter = filter_str
        self._add = add_btn
        self._rm = remove_btn
        self._clr = clear_btn
        self._list = file_list
        self._files: list[str] = []

        self._add.clicked.connect(self._on_add)
        self._rm.clicked.connect(self._on_remove)
        self._clr.clicked.connect(self._on_clear)

    @property
    def files(self) -> list[str]:
        return list(self._files)

    @property
    def count(self) -> int:
        return len(self._files)

    def clear_colors(self):
        for i in range(self._list.count()):
            self._set_color(i, "#ffffff")

    def highlight(self, path: str, color: str):
        try:
            idx = self._files.index(path)
        except ValueError:
            return
        self._set_color(idx, color)
        self._list.scrollToItem(self._list.item(idx), QListWidget.ScrollHint.EnsureVisible)

    def _set_color(self, idx: int, bg: str):
        if 0 <= idx < self._list.count():
            self._list.item(idx).setBackground(QColor(bg))

    def _on_add(self):
        files, _ = QFileDialog.getOpenFileNames(self._parent, "选择文件", "", self._filter)
        for f in files:
            if f not in self._files:
                self._files.append(f)
                self._list.addItem(os.path.basename(f))

    def _on_remove(self):
        for item in self._list.selectedItems():
            idx = self._list.row(item)
            self._list.takeItem(idx)
            del self._files[idx]

    def _on_clear(self):
        self._files.clear()
        self._list.clear()


# ── main window ──────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音频转文字 & 文本校对")
        self.resize(860, 800)
        self.setMinimumSize(800, 720)
        self._config = load_config()
        self._audio_worker: AudioWorker | None = None
        self._text_worker: TextWorker | None = None
        self._processed_count = 0
        self._setup_ui()

    # ── UI ───────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # settings shared across tabs
        self.asr_settings = ASRSettingsWidget(self._config.get("asr", {}))
        root.addWidget(self.asr_settings)
        self.llm_settings = LLMSettingsWidget(self._config.get("llm", {}))
        root.addWidget(self.llm_settings)

        # output dir
        out = QHBoxLayout()
        out.addWidget(QLabel("输出目录:"))
        self.output_label = QLabel(self._config.get("output_dir", ""))
        out.addWidget(self.output_label, 1)
        browse = QPushButton("浏览...")
        browse.clicked.connect(lambda: self._browse_dir())
        out.addWidget(browse)
        root.addLayout(out)

        # summary checkbox + save location
        sum_row = QHBoxLayout()
        self.summary_cb = QCheckBox("同时生成重点摘要")
        self.summary_cb.setChecked(self._config.get("generate_summary", True))
        sum_row.addWidget(self.summary_cb)
        sum_row.addWidget(QLabel("  摘要保存位置:"))
        self.summary_dir_label = QLabel(self._config.get("summary_dir", ""))
        self.summary_dir_label.setStyleSheet("color: #888;")
        sum_row.addWidget(self.summary_dir_label, 1)
        sum_browse = QPushButton("浏览...")
        sum_browse.clicked.connect(lambda: self._browse_summary_dir())
        sum_row.addWidget(sum_browse)
        root.addLayout(sum_row)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_audio_tab(), "音频转写 (mp3/wav)")
        self.tabs.addTab(self._make_text_tab(), "文本校对 (txt/md)")
        root.addWidget(self.tabs)

        # progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        root.addWidget(self.status_label)

        # log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(160)
        root.addWidget(self.log_area)

        # actions
        act = QHBoxLayout()
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self._start)
        self.start_btn.setMinimumHeight(36)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        act.addWidget(self.start_btn)
        act.addWidget(self.stop_btn)
        act.addStretch()
        root.addLayout(act)

    def _make_audio_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(QLabel("音频文件列表:"))
        fl = QHBoxLayout()
        alist = QListWidget()
        fl.addWidget(alist, 1)
        vb = QVBoxLayout()
        add = QPushButton("添加文件")
        rm = QPushButton("移除选中")
        clr = QPushButton("清空列表")
        vb.addWidget(add); vb.addWidget(rm); vb.addWidget(clr); vb.addStretch()
        fl.addLayout(vb)
        lay.addLayout(fl)

        self._audio_panel = FilePanel(self, "音频文件 (*.mp3 *.wav);;所有文件 (*)", add, rm, clr, alist)
        return w

    def _make_text_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(QLabel("文本文件列表 (支持 .txt / .md):"))
        fl = QHBoxLayout()
        tlist = QListWidget()
        fl.addWidget(tlist, 1)
        vb = QVBoxLayout()
        add = QPushButton("添加文件")
        rm = QPushButton("移除选中")
        clr = QPushButton("清空列表")
        vb.addWidget(add); vb.addWidget(rm); vb.addWidget(clr); vb.addStretch()
        fl.addLayout(vb)
        lay.addLayout(fl)

        self._text_panel = FilePanel(self, "文本文件 (*.txt *.md);;所有文件 (*)", add, rm, clr, tlist)
        return w

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择校对稿保存位置")
        if d:
            self.output_label.setText(d)

    def _browse_summary_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择摘要保存位置")
        if d:
            self.summary_dir_label.setText(d)
            self.summary_dir_label.setStyleSheet("color: #000;")

    # ── engine ───────────────────────────────────────────

    def _make_llm(self) -> OpenAICompatibleLLM:
        cfg = self.llm_settings.get_config()
        if cfg["backend"] == "omlx":
            c = cfg["omlx"]
        else:
            c = cfg["openai"]
        return OpenAICompatibleLLM(api_key=c["api_key"], base_url=c["base_url"], model=c["model"])

    def _out_dir(self) -> str:
        return self.output_label.text() or self._config.get("output_dir", ".")

    def _summary_out_dir(self) -> str:
        return self.summary_dir_label.text() or self._out_dir()

    # ── start / stop ─────────────────────────────────────

    def _start(self):
        is_audio = self.tabs.currentIndex() == 0
        panel = self._audio_panel if is_audio else self._text_panel

        if not panel.files:
            QMessageBox.warning(self, "提示", "请先添加文件。")
            return
        if not self._out_dir():
            QMessageBox.warning(self, "提示", "请选择输出目录。")
            return

        llm_cfg = self.llm_settings.get_config()
        if llm_cfg["backend"] == "openai" and not llm_cfg["openai"]["api_key"]:
            QMessageBox.warning(self, "提示", "使用 OpenAI API 需要填写 API Key。")
            return

        self._save_config()
        gen_summary = self.summary_cb.isChecked()

        if is_audio:
            asr_cfg = self.asr_settings.get_config()
            asr = OMLXASR(api_key=asr_cfg.get("api_key", "omlx"),
                          base_url=asr_cfg["base_url"], model=asr_cfg["model"])
            llm = self._make_llm()
            proc = AudioProcessor(asr=asr, llm=llm, output_dir=self._out_dir(),
                                  generate_summary=gen_summary,
                                  summary_dir=self._summary_out_dir())
            self._audio_worker = AudioWorker(proc, panel.files)
            w = self._audio_worker
        else:
            llm = self._make_llm()
            proc = TextProcessor(llm=llm, output_dir=self._out_dir(),
                                 generate_summary=gen_summary,
                                 summary_dir=self._summary_out_dir())
            self._text_worker = TextWorker(proc, panel.files)
            w = self._text_worker

        w.current_file.connect(lambda p: panel.highlight(p, "#c8e6ff"))
        w.progress.connect(self._on_progress)
        w.file_done.connect(lambda p, m, ok: self._on_file_done(panel, p, m, ok))
        w.all_done.connect(self._on_all_done)

        self._processed_count = 0
        panel.clear_colors()
        self.progress_bar.setMaximum(panel.count)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("处理中...")
        w.start()

    def _stop(self):
        w = self._audio_worker or self._text_worker
        if w:
            w.stop()
            self.status_label.setText("正在停止...")
            self.stop_btn.setEnabled(False)

    # ── signals ──────────────────────────────────────────

    def _on_progress(self, stage: str, msg: str):
        labels = {"transcribing": "转写", "cleaning": "清洗", "proofreading": "校对",
                   "summarizing": "摘要", "writing": "写入", "reading": "读取"}
        self.status_label.setText(f"[{labels.get(stage, stage)}] {msg}")

    def _on_file_done(self, panel: FilePanel, path: str, msg: str, ok: bool):
        self._processed_count += 1
        self.progress_bar.setValue(self._processed_count)
        panel.highlight(path, "#d4edda" if ok else "#f8d7da")
        fname = os.path.basename(path)
        if ok:
            self.log_area.append(f"[完成] {fname} → {msg}")
        else:
            self.log_area.append(f"[失败] {fname}\n  {msg}\n")

    def _on_all_done(self):
        self.status_label.setText(f"全部完成，共处理 {self._processed_count} 个文件")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._audio_worker = None
        self._text_worker = None

    # ── config ───────────────────────────────────────────

    def _save_config(self):
        save_config({
            "asr": self.asr_settings.get_config(),
            "llm": self.llm_settings.get_config(),
            "output_dir": self.output_label.text(),
            "summary_dir": self.summary_dir_label.text(),
            "generate_summary": self.summary_cb.isChecked(),
        })

    def closeEvent(self, event):
        for w in (self._audio_worker, self._text_worker):
            if w and w.isRunning():
                w.stop()
                w.wait(3000)
        self._save_config()
        event.accept()
