# app/ui/login_screen.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt
from app.db.connection import get_conn


class LoginScreen(QWidget):
    """
    Temporary login:
    - Takes username/password as UI input
    - Tries a DB connection (SELECT 1)
    - If DB works => allow access
    """

    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success

        self.setWindowTitle("PharmacyApp - Login")
        self.resize(420, 260)

        # 🎨 Styling
        self.setStyleSheet("""
            QWidget {
                background: #EAF4FF;
                font-family: Segoe UI;
            }
            QFrame#Card {
                background: white;
                border: 1px solid #D6E6FA;
                border-radius: 14px;
            }
            QLabel#Title {
                font-size: 22px;
                font-weight: 700;
                color: #0F172A;
            }
            QLabel#Subtitle {
                color: #64748B;
                font-size: 11px;
            }
            QLineEdit {
                background: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 8px 10px;
                height: 34px;
            }
            QLineEdit:focus {
                border: 1px solid #60A5FA;
            }
            QPushButton {
                background: #60A5FA;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                font-weight: 700;
                min-height: 36px;
            }
            QPushButton:hover { background: #3B82F6; }
            QPushButton:pressed { background: #2563EB; }

            QLabel#StatusOk { color: #2563EB; }
            QLabel#StatusErr { color: #DC2626; }
        """)

        # 🔹 Outer layout (centers the card)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        # 🔹 Card
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(320)
        outer.addWidget(card, alignment=Qt.AlignCenter)

        # 🔹 Card layout
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Login")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Enter your credentials to continue.")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setFixedWidth(240)
        layout.addWidget(self.username, alignment=Qt.AlignCenter)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedWidth(240)
        layout.addWidget(self.password, alignment=Qt.AlignCenter)

        self.btn = QPushButton("Login")
        self.btn.setFixedWidth(140)
        self.btn.clicked.connect(self.handle_login)
        layout.addWidget(self.btn, alignment=Qt.AlignCenter)

        self.status = QLabel("")
        self.status.setObjectName("StatusOk")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

    def handle_login(self):
        u = self.username.text().strip()
        p = self.password.text().strip()

        if not u or not p:
            self._set_status("Please enter username and password.", error=True)
            return

        try:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as e:
            self._set_status(f"DB connection failed: {e}", error=True)
            return

        self._set_status("")
        self.on_login_success({"username": u, "role": "STAFF"})

    def _set_status(self, text: str, error: bool = False):
        self.status.setObjectName("StatusErr" if error else "StatusOk")
        self.status.setText(text)
        self.style().unpolish(self.status)
        self.style().polish(self.status)