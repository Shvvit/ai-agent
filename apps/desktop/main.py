from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, QSettings, QThread, Signal, Slot
from PySide6.QtGui import QAction, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agents.base import BaseAgent, build_model
from config.model_config import ModelConfig
from core.task_manager import TaskManager
from memory.manager import MemoryManager
from tools.file_manager import FileManager
from tools.test_runner import TestRunner
from tools.tool_executor import ToolExecutor


APP_NAME = "WlasneAI"
APP_ORG = "Shvvit"
APP_VERSION = "0.1.0"


def app_data_dir() -> Path:
    base = Path(os.getenv("APPDATA", Path.home() / "AppData/Roaming"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    """Small local SQLite store for desktop conversations."""

    def __init__(self, path: Path) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
        """)
        self.db.commit()

    def create_session(self, title: str = "Nowa sesja") -> str:
        session_id = str(uuid.uuid4())
        now = utc_now()
        self.db.execute(
            "INSERT INTO sessions(id,title,created_at,updated_at) VALUES(?,?,?,?)",
            (session_id, title, now, now),
        )
        self.db.commit()
        return session_id

    def list_sessions(self) -> list[dict[str, str]]:
        rows = self.db.execute(
            "SELECT id,title,created_at,updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        rows = self.db.execute(
            "SELECT role,content,created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        now = utc_now()
        self.db.execute(
            "INSERT INTO messages(session_id,role,content,created_at) VALUES(?,?,?,?)",
            (session_id, role, content, now),
        )
        self.db.execute(
            "UPDATE sessions SET updated_at=?, title=CASE "
            "WHEN title='Nowa sesja' AND ?='user' THEN substr(?,1,64) ELSE title END "
            "WHERE id=?",
            (now, role, content, session_id),
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()


class ModelSettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Ustawienia modelu")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.provider = QComboBox()
        self.provider.addItem("Ollama (lokalnie)", "ollama")
        self.provider.addItem("OpenRouter", "openrouter")
        self.provider.addItem("OpenAI compatible", "openai_compatible")
        current_provider = str(settings.value("provider", os.getenv("AI_PROVIDER", "ollama"))).strip().lower()
        idx = self.provider.findData(current_provider)
        self.provider.setCurrentIndex(max(0, idx))

        self.model = QLineEdit(str(settings.value("model", os.getenv("AI_MODEL", "qwen3:8b"))))
        self.host = QLineEdit(str(settings.value("host", os.getenv("AI_HOST", os.getenv("AI_BASE_URL", "http://127.0.0.1:11434")))))
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Pozostaw puste, aby użyć zmiennej środowiskowej")
        self.temperature = QLineEdit(str(settings.value("temperature", os.getenv("AI_TEMPERATURE", "0.2"))))

        form.addRow("Dostawca", self.provider)
        form.addRow("Model", self.model)
        form.addRow("Adres API", self.host)
        form.addRow("Klucz API", self.api_key)
        form.addRow("Temperatura (0–2)", self.temperature)
        layout.addLayout(form)

        note = QLabel(
            "Klucz API jest przechowywany tylko w Menedżerze poświadczeń Windows "
            "przez keyring. Nie zapisujemy go w pliku ustawień."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, Any]:
        return {
            "provider": str(self.provider.currentData()),
            "model": self.model.text().strip(),
            "host": self.host.text().strip(),
            "api_key": self.api_key.text().strip(),
            "temperature": float(self.temperature.text().strip()),
        }


@dataclass
class WorkRequest:
    session_id: str
    task_id: str
    prompt: str
    agent: BaseAgent
    task_manager: TaskManager


class AgentWorker(QObject):
    finished = Signal(str, str, bool)
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, request: WorkRequest) -> None:
        super().__init__()
        self.request = request

    @Slot()
    def run(self) -> None:
        try:
            self.status.emit("Planowanie i wykonywanie zadania…")
            answer = self.request.agent.run(self.request.prompt)
            self.request.task_manager.transition(
                self.request.task_id, "completed", result=answer
            )
            self.finished.emit(self.request.session_id, answer, True)
        except Exception as exc:
            try:
                record = self.request.task_manager.get(self.request.task_id)
                if record and record.status.value == "running":
                    self.request.task_manager.transition(
                        self.request.task_id, "failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
            except Exception:
                pass
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MessageCard(QFrame):
    def __init__(self, role: str, content: str) -> None:
        super().__init__()
        self.setObjectName("messageCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        heading = QLabel("TY" if role == "user" else "WŁASNE AI")
        heading.setObjectName("messageRole")
        layout.addWidget(heading)

        body = QTextBrowser()
        body.setObjectName("messageBody")
        body.setOpenExternalLinks(True)
        body.setReadOnly(True)
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setMarkdown(content)
        body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        body.setMinimumHeight(34)
        body.document().setDocumentMargin(0)
        body.document().adjustSize()
        body.setFixedHeight(max(42, min(600, int(body.document().size().height()) + 18)))
        layout.addWidget(body)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Własne AI")
        self.resize(1440, 920)
        self.setMinimumSize(980, 640)

        self.settings = QSettings(APP_ORG, APP_NAME)
        self.data_dir = app_data_dir()
        self.store = SessionStore(self.data_dir / "sessions.sqlite3")
        self.memory = MemoryManager(self.data_dir / "memory.sqlite3")
        self.tasks = TaskManager(self.data_dir / "tasks.sqlite3")
        self.workspace = self.data_dir / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.current_session = ""
        self.agent: BaseAgent | None = None
        self.thread: QThread | None = None
        self.worker: AgentWorker | None = None
        self._build_ui()
        self._refresh_sessions()
        sessions = self.store.list_sessions()
        if sessions:
            self._select_session(sessions[0]["id"])
        else:
            self.new_session()
        self._refresh_model_label()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # Sidebar: compact OpenCode-inspired session navigation.
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(330)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 18, 14, 14)
        side.setSpacing(12)

        brand = QLabel("◈  WŁASNE AI")
        brand.setObjectName("brand")
        side.addWidget(brand)

        self.new_button = QPushButton("+  Nowa sesja")
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(self.new_session)
        side.addWidget(self.new_button)

        section = QLabel("HISTORIA")
        section.setObjectName("sectionLabel")
        side.addWidget(section)

        self.session_list = QListWidget()
        self.session_list.setObjectName("sessionList")
        self.session_list.currentItemChanged.connect(self._on_session_selected)
        side.addWidget(self.session_list, 1)

        bottom = QHBoxLayout()
        self.workspace_button = QPushButton("Otwórz workspace")
        self.workspace_button.clicked.connect(self._show_workspace)
        bottom.addWidget(self.workspace_button)
        side.addLayout(bottom)

        self.settings_button = QPushButton("⚙  Ustawienia")
        self.settings_button.setObjectName("secondaryButton")
        self.settings_button.clicked.connect(self._open_settings)
        side.addWidget(self.settings_button)

        splitter.addWidget(side)

        # Main conversation area.
        main = QWidget()
        main.setObjectName("mainArea")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 12, 22, 12)
        self.session_title = QLabel("Nowa sesja")
        self.session_title.setObjectName("topTitle")
        top_layout.addWidget(self.session_title)
        top_layout.addStretch(1)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(190)
        self.model_combo.addItems(["qwen3:8b"])
        self.model_combo.setCurrentText(str(self.settings.value("model", os.getenv("AI_MODEL", "qwen3:8b"))))
        self.model_combo.setToolTip("Wybierz nazwę modelu")
        self.model_combo.currentTextChanged.connect(self._model_changed)
        top_layout.addWidget(self.model_combo)

        self.provider_label = QLabel("OLLAMA")
        self.provider_label.setObjectName("providerPill")
        top_layout.addWidget(self.provider_label)
        main_layout.addWidget(topbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setObjectName("chatScroll")
        self.messages_host = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_host)
        self.messages_layout.setContentsMargins(0, 28, 0, 28)
        self.messages_layout.setSpacing(14)
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.messages_host)
        main_layout.addWidget(self.scroll, 1)

        self.welcome = QLabel(
            "Jak mogę pomóc?\n\nOpisz zadanie — agent może analizować, pisać kod "
            "i korzystać z narzędzi dostępnych w swoim workspace."
        )
        self.welcome.setObjectName("welcome")
        self.welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.messages_layout.insertWidget(0, self.welcome)

        composer_wrap = QFrame()
        composer_wrap.setObjectName("composerWrap")
        composer_layout = QVBoxLayout(composer_wrap)
        composer_layout.setContentsMargins(24, 12, 24, 12)
        composer_layout.setSpacing(8)

        composer = QFrame()
        composer.setObjectName("composer")
        composer_row = QHBoxLayout(composer)
        composer_row.setContentsMargins(12, 10, 12, 10)
        self.prompt = QTextEdit()
        self.prompt.setObjectName("promptInput")
        self.prompt.setPlaceholderText("Napisz, co mam zrobić…")
        self.prompt.setAcceptRichText(False)
        self.prompt.setFixedHeight(86)
        self.prompt.installEventFilter(self)
        composer_row.addWidget(self.prompt, 1)

        self.send_button = QPushButton("Wyślij  ↗")
        self.send_button.setObjectName("sendButton")
        self.send_button.setMinimumWidth(104)
        self.send_button.clicked.connect(self.send_message)
        composer_row.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignBottom)
        composer_layout.addWidget(composer)

        footer = QHBoxLayout()
        self.status_label = QLabel("Gotowy")
        self.status_label.setObjectName("muted")
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        self.security_label = QLabel("Kod Python: wyłączony domyślnie")
        self.security_label.setObjectName("muted")
        footer.addWidget(self.security_label)
        composer_layout.addLayout(footer)
        main_layout.addWidget(composer_wrap)

        splitter.addWidget(main)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1180])
        self.setCentralWidget(central)

        quit_action = QAction("Zamknij", self)
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)
        self.setStyleSheet(STYLE)

    def eventFilter(self, watched: QObject, event: Any) -> bool:
        from PySide6.QtCore import QEvent
        if watched is self.prompt and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                self.send_message()
                return True
        return super().eventFilter(watched, event)

    def _refresh_model_label(self) -> None:
        provider = str(self.settings.value("provider", os.getenv("AI_PROVIDER", "ollama"))).upper()
        self.provider_label.setText(provider.replace("_COMPATIBLE", " API"))
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(str(self.settings.value("model", os.getenv("AI_MODEL", "qwen3:8b"))))
        self.model_combo.blockSignals(False)

    def _model_changed(self, value: str) -> None:
        value = value.strip()
        if value:
            self.settings.setValue("model", value)

    def _model_config(self) -> ModelConfig:
        provider = str(self.settings.value("provider", os.getenv("AI_PROVIDER", "ollama")))
        model = self.model_combo.currentText().strip() or os.getenv("AI_MODEL", "qwen3:8b")
        defaults = {
            "ollama": "http://127.0.0.1:11434",
            "openrouter": "https://openrouter.ai/api/v1",
            "openai_compatible": "https://api.openai.com/v1",
        }
        host = str(self.settings.value("host", os.getenv("AI_HOST", os.getenv("AI_BASE_URL", defaults[provider]))))
        api_key = os.getenv("AI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if provider != "ollama":
            try:
                import keyring
                api_key = keyring.get_password("WlasneAI", f"{provider}:{host}") or api_key
            except Exception:
                pass
        return ModelConfig(
            provider=provider,
            model=model,
            host=host,
            temperature=float(self.settings.value("temperature", os.getenv("AI_TEMPERATURE", 0.2))),
            api_key=api_key,
        )

    def _new_agent(self) -> BaseAgent:
        config = self._model_config()
        file_manager = FileManager(self.workspace)
        test_runner = TestRunner(workspace=self.workspace)
        executor = ToolExecutor(file_manager=file_manager, test_runner=test_runner)
        return BaseAgent(model=build_model(config), tools=executor)

    def _refresh_sessions(self) -> None:
        current = self.current_session
        self.session_list.blockSignals(True)
        self.session_list.clear()
        selected = None
        for session in self.store.list_sessions():
            item = QListWidgetItem(session["title"])
            item.setData(Qt.ItemDataRole.UserRole, session["id"])
            self.session_list.addItem(item)
            if session["id"] == current:
                selected = item
        if selected:
            self.session_list.setCurrentItem(selected)
        self.session_list.blockSignals(False)

    def _select_session(self, session_id: str) -> None:
        self.current_session = session_id
        messages = self.store.get_messages(session_id)
        self._clear_messages()
        for message in messages:
            self._add_message(message["role"], message["content"])
        self.agent = self._new_agent()
        self.agent.history = [
            {"role": item["role"], "content": item["content"]}
            for item in messages if item["role"] in {"user", "assistant"}
        ][-self.agent.max_history_messages:]
        sessions = {s["id"]: s for s in self.store.list_sessions()}
        self.session_title.setText(sessions.get(session_id, {}).get("title", "Nowa sesja"))
        self._refresh_sessions()
        self._scroll_bottom()

    def _on_session_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        session_id = current.data(Qt.ItemDataRole.UserRole)
        if session_id and session_id != self.current_session and not self._busy():
            self._select_session(session_id)

    def new_session(self) -> None:
        if self._busy():
            return
        session_id = self.store.create_session()
        self._select_session(session_id)

    def _clear_messages(self) -> None:
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is self.welcome:
                continue
            if widget is not None:
                widget.deleteLater()
        self.messages_layout.addStretch(1)
        has_messages = bool(self.store.get_messages(self.current_session)) if self.current_session else False
        if has_messages:
            self.welcome.hide()
        else:
            self.welcome.show()
            self.messages_layout.insertWidget(0, self.welcome)

    def _add_message(self, role: str, content: str) -> None:
        if self.welcome:
            self.welcome.hide()
        card = MessageCard(role, content)
        # Insert before the permanent stretch at the end.
        self.messages_layout.insertWidget(max(0, self.messages_layout.count() - 1), card)

    def _scroll_bottom(self) -> None:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(40, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _busy(self) -> bool:
        return self.thread is not None and self.thread.isRunning()

    @Slot()
    def send_message(self) -> None:
        if self._busy():
            return
        prompt = self.prompt.toPlainText().strip()
        if not prompt:
            return
        if self.agent is None:
            try:
                self.agent = self._new_agent()
            except Exception as exc:
                QMessageBox.critical(self, "Nie można uruchomić modelu", str(exc))
                return

        self.prompt.clear()
        self._add_message("user", prompt)
        self.store.add_message(self.current_session, "user", prompt)
        self.session_title.setText(prompt[:64])
        self._refresh_sessions()

        task = self.tasks.create(prompt)
        self.tasks.transition(task.id, "running")
        request = WorkRequest(
            session_id=self.current_session,
            task_id=task.id,
            prompt=prompt,
            agent=self.agent,
            task_manager=self.tasks,
        )
        self.thread = QThread(self)
        self.worker = AgentWorker(request)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self._set_status)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_worker)
        self.send_button.setEnabled(False)
        self.new_button.setEnabled(False)
        self.status_label.setText("Agent pracuje…")
        self.thread.start()

    @Slot(str)
    def _set_status(self, value: str) -> None:
        self.status_label.setText(value)

    @Slot(str, str, bool)
    def _on_finished(self, session_id: str, answer: str, success: bool) -> None:
        if session_id == self.current_session:
            self._add_message("assistant", answer)
            self._scroll_bottom()
        self.store.add_message(session_id, "assistant", answer)
        self.status_label.setText("Gotowy")
        self._refresh_sessions()

    @Slot(str)
    def _on_failed(self, error: str) -> None:
        self._add_message("assistant", f"**Wystąpił błąd:**\n\n{error}")
        self.store.add_message(self.current_session, "assistant", f"Błąd: {error}")
        self.status_label.setText("Błąd")
        QMessageBox.warning(self, "Agent nie ukończył zadania", error)

    @Slot()
    def _cleanup_worker(self) -> None:
        self.send_button.setEnabled(True)
        self.new_button.setEnabled(True)
        if self.thread:
            self.thread.deleteLater()
        if self.worker:
            self.worker.deleteLater()
        self.thread = None
        self.worker = None

    def _open_settings(self) -> None:
        dialog = ModelSettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values()
            if not values["model"]:
                raise ValueError("Wpisz nazwę modelu.")
            provider = values["provider"]
            host = values["host"]
            if not host:
                raise ValueError("Wpisz adres API.")
            self.settings.setValue("provider", provider)
            self.settings.setValue("model", values["model"])
            self.settings.setValue("host", host)
            self.settings.setValue("temperature", values["temperature"])
            if values["api_key"]:
                try:
                    import keyring
                    keyring.set_password("WlasneAI", f"{provider}:{host}", values["api_key"])
                except Exception as exc:
                    raise RuntimeError(
                        "Nie udało się zapisać klucza w Menedżerze poświadczeń Windows. "
                        "Możesz ustawić go jako AI_API_KEY."
                    ) from exc
            self.agent = None
            self._refresh_model_label()
            self.status_label.setText("Ustawienia zapisane")
        except Exception as exc:
            QMessageBox.warning(self, "Niepoprawne ustawienia", str(exc))

    def _show_workspace(self) -> None:
        try:
            os.startfile(str(self.workspace))
        except Exception as exc:
            QMessageBox.warning(self, "Workspace", str(exc))

    def closeEvent(self, event: Any) -> None:
        if self._busy():
            QMessageBox.information(
                self, "Agent pracuje",
                "Poczekaj na zakończenie zadania przed zamknięciem aplikacji.",
            )
            event.ignore()
            return
        self.store.close()
        self.memory.close()
        self.tasks.close()
        event.accept()


STYLE = """
QMainWindow, QWidget { background: #101113; color: #e7e7e8; font-family: "Segoe UI"; font-size: 13px; }
#sidebar { background: #151619; border-right: 1px solid #292a2e; }
#brand { color: #f4f4f5; font-size: 16px; font-weight: 700; padding: 4px 2px 14px 2px; }
#sectionLabel, #messageRole { color: #85868d; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
#sessionList { background: transparent; border: none; outline: none; }
#sessionList::item { color: #b9bac0; padding: 10px 9px; border-radius: 7px; margin: 1px 0; }
#sessionList::item:selected { background: #292a2f; color: #fff; }
QPushButton { background: #25262b; border: 1px solid #34353b; border-radius: 7px; color: #e7e7e8; padding: 9px 12px; }
QPushButton:hover { background: #303137; border-color: #55565e; }
QPushButton:disabled { color: #686970; background: #1b1c20; }
#primaryButton, #sendButton { background: #e6e6e8; color: #17181b; border: none; font-weight: 700; }
#primaryButton:hover, #sendButton:hover { background: #fff; }
#secondaryButton { text-align: left; background: transparent; border-color: transparent; }
#mainArea { background: #101113; }
#topbar { background: #101113; border-bottom: 1px solid #292a2e; }
#topTitle { font-size: 14px; font-weight: 600; }
#providerPill { color: #b8b9bf; background: #222328; border: 1px solid #33343a; border-radius: 10px; padding: 5px 9px; font-size: 10px; font-weight: 700; }
QComboBox { background: #202126; border: 1px solid #36373e; border-radius: 7px; padding: 7px 9px; color: #e7e7e8; }
QComboBox QAbstractItemView { background: #202126; selection-background-color: #3a3b43; }
#chatScroll { background: #101113; }
#messageCard { background: #17181c; border: 1px solid #28292e; border-radius: 11px; }
#messageBody { background: transparent; color: #e7e7e8; font-size: 14px; }
#messageRole { color: #a4a5ad; }
#welcome { color: #bfc0c6; font-size: 19px; font-weight: 500; padding: 40px; }
#composerWrap { background: #101113; border-top: 1px solid #292a2e; }
#composer { background: #1b1c20; border: 1px solid #393a41; border-radius: 12px; }
#promptInput { background: transparent; border: none; color: #f1f1f2; font-size: 14px; selection-background-color: #55565e; }
#muted { color: #777981; font-size: 11px; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #383940; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialog { background: #17181c; }
QLineEdit { background: #202126; border: 1px solid #393a41; border-radius: 6px; padding: 8px; color: #eee; }
QTextBrowser { background: transparent; }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
