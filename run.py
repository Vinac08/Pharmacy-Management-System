# run.py
import sys
from PySide6.QtWidgets import QApplication

from app.ui.login_screen import LoginScreen
from app.ui.app_window import MainWindow


def main():
    app = QApplication(sys.argv)

    main_window = {"w": None}  # holder so it doesn't get garbage-collected

    def on_login_success(user: dict):
        # close login
        login.close()

        # open main app
        w = MainWindow(user=user)
        w.show()
        main_window["w"] = w  # keep reference

    login = LoginScreen(on_login_success=on_login_success)
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()