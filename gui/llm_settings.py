"""LLM 模型设置面板 —— oMLX 本地 / OpenAI API 双后端切换"""

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QStackedWidget, QWidget, QPushButton, QApplication,
)
from PyQt6.QtCore import pyqtSignal, Qt


def _fetch_models(base_url: str, api_key: str) -> list[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, max_retries=1, timeout=5)
        resp = client.models.list()
        return [m.id for m in resp.data]
    except Exception:
        return []


class LLMSettingsWidget(QGroupBox):
    backend_changed = pyqtSignal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__("LLM 校对与摘要设置", parent)
        self._config = config
        self._omlx_models = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout()

        top = QHBoxLayout()
        top.addWidget(QLabel("LLM 后端:"))

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("oMLX (本地)", "omlx")
        self.backend_combo.addItem("OpenAI API (在线)", "openai")
        idx = self.backend_combo.findData(self._config.get("backend", "omlx"))
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        top.addWidget(self.backend_combo)
        top.addStretch()
        main_layout.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._make_omlx_panel())
        self.stack.addWidget(self._make_openai_panel())
        main_layout.addWidget(self.stack)

        self.setLayout(main_layout)
        self._on_backend_changed()

    def _make_omlx_panel(self) -> QWidget:
        cfg = self._config.get("omlx", {})
        w = QWidget()
        layout = QVBoxLayout()

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("API 地址:"))
        self.omlx_url_input = QLineEdit()
        self.omlx_url_input.setText(cfg.get("base_url", "http://localhost:8000/v1"))
        r1.addWidget(self.omlx_url_input)
        layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("API Key:"))
        self.omlx_key_input = QLineEdit()
        self.omlx_key_input.setText(cfg.get("api_key", "omlx"))
        r2.addWidget(self.omlx_key_input)
        layout.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("模型:"))

        self.omlx_model_combo = QComboBox()
        self.omlx_model_combo.setMinimumWidth(250)
        self.omlx_model_combo.setEditable(True)  # 允许手动输入
        r3.addWidget(self.omlx_model_combo, 1)

        self.omlx_refresh_btn = QPushButton("刷新")
        self.omlx_refresh_btn.setFixedWidth(60)
        self.omlx_refresh_btn.clicked.connect(self._refresh_omlx_models)
        r3.addWidget(self.omlx_refresh_btn)
        layout.addLayout(r3)

        layout.addStretch()
        w.setLayout(layout)
        return w

    def _make_openai_panel(self) -> QWidget:
        cfg = self._config.get("openai", {})
        w = QWidget()
        layout = QVBoxLayout()

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("API Key:"))
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setText(cfg.get("api_key", ""))
        r1.addWidget(self.openai_key_input)

        self.toggle_key_btn = QPushButton("显示")
        self.toggle_key_btn.setFixedWidth(50)
        self.toggle_key_btn.clicked.connect(self._toggle_key_visibility)
        r1.addWidget(self.toggle_key_btn)
        layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Base URL:"))
        self.openai_url_input = QLineEdit()
        self.openai_url_input.setText(cfg.get("base_url", "https://api.openai.com/v1"))
        r2.addWidget(self.openai_url_input)
        layout.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("模型:"))
        self.openai_model_input = QLineEdit()
        self.openai_model_input.setText(cfg.get("model", "gpt-4o"))
        r3.addWidget(self.openai_model_input)
        layout.addLayout(r3)

        layout.addStretch()
        w.setLayout(layout)
        return w

    def _refresh_omlx_models(self):
        self.omlx_refresh_btn.setEnabled(False)
        self.omlx_refresh_btn.setText("…")
        QApplication.processEvents()

        base_url = self.omlx_url_input.text().strip()
        api_key = self.omlx_key_input.text().strip()
        models = _fetch_models(base_url, api_key)

        self.omlx_model_combo.clear()
        current = self._config.get("omlx", {}).get("model", "")
        found = False
        for m in models:
            self.omlx_model_combo.addItem(m)
            if m == current:
                found = True

        if not found and current:
            self.omlx_model_combo.setEditText(current)

        self.omlx_refresh_btn.setEnabled(True)
        self.omlx_refresh_btn.setText("刷新")

    def _on_backend_changed(self):
        backend = self.backend_combo.currentData()
        self.stack.setCurrentIndex(0 if backend == "omlx" else 1)
        self.backend_changed.emit(backend)

    def _toggle_key_visibility(self):
        if self.openai_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_key_btn.setText("隐藏")
        else:
            self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_key_btn.setText("显示")

    def _get_omlx_model(self) -> str:
        if hasattr(self, "omlx_model_combo"):
            return self.omlx_model_combo.currentText().strip()
        return self._config.get("omlx", {}).get("model", "")

    def get_config(self) -> dict:
        return {
            "backend": self.backend_combo.currentData(),
            "omlx": {
                "base_url": self.omlx_url_input.text().strip(),
                "api_key": self.omlx_key_input.text().strip(),
                "model": self._get_omlx_model(),
            },
            "openai": {
                "api_key": self.openai_key_input.text().strip(),
                "base_url": self.openai_url_input.text().strip(),
                "model": self.openai_model_input.text().strip(),
            },
        }

    @property
    def backend(self) -> str:
        return self.backend_combo.currentData()
