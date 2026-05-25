"""ASR 模型设置面板"""

from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QApplication
from PyQt6.QtCore import pyqtSignal


def _fetch_models(base_url: str, api_key: str) -> list[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, max_retries=1, timeout=5)
        resp = client.models.list()
        return [m.id for m in resp.data]
    except Exception:
        return []


class ASRSettingsWidget(QGroupBox):
    model_changed = pyqtSignal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__("ASR 语音识别设置", parent)
        self._config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout()

        layout.addWidget(QLabel("引擎: oMLX 本地"))

        layout.addWidget(QLabel("API 地址:"))
        self.url_input = QLineEdit()
        self.url_input.setText(self._config.get("base_url", "http://localhost:8000/v1"))
        self.url_input.setFixedWidth(200)
        layout.addWidget(self.url_input)

        layout.addWidget(QLabel("模型:"))

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(220)
        current = self._config.get("model", "Qwen3-ASR-1.7B-8bit")
        self.model_combo.setEditText(current)
        layout.addWidget(self.model_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        self.refresh_btn.clicked.connect(self._refresh_models)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()
        self.setLayout(layout)

    def _refresh_models(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("…")
        QApplication.processEvents()

        base_url = self.url_input.text().strip()
        models = _fetch_models(base_url, "omlx")

        current = self.model_combo.currentText().strip()
        self.model_combo.clear()
        found = False
        for m in models:
            self.model_combo.addItem(m)
            if m == current:
                found = True
        if not found and current:
            self.model_combo.setEditText(current)

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新")

    def get_config(self) -> dict:
        return {
            "base_url": self.url_input.text().strip(),
            "api_key": "omlx",
            "model": self.model_combo.currentText().strip(),
        }

    @property
    def model_size(self) -> str:
        return self.model_combo.currentText().strip()
