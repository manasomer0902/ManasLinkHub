import os
import sys

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView


BASE_URL = "https://manaslinkhub.onrender.com"


class AnalyticsWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()

        self.setWindowTitle("Manas Link Hub Analytics")

        storage_path = os.path.join(
            os.path.expanduser("~"),
            ".manas_link_hub",
        )

        os.makedirs(storage_path, exist_ok=True)

        # Persistent WebEngine profile.
        # Keep the profile alive for the entire application.
        self.profile = QWebEngineProfile(
            "ManasLinkHub",
            app,
        )

        self.profile.setPersistentStoragePath(
            storage_path
        )

        self.profile.setCachePath(
            os.path.join(storage_path, "cache")
        )

        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        # Create the page after the persistent profile.
        self.page = QWebEnginePage(
            self.profile,
            self,
        )

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)

        self.browser.setUrl(
            QUrl(f"{BASE_URL}/admin/dashboard")
        )

        self.setCentralWidget(self.browser)

        self.setStyleSheet("""
            QMainWindow {
                background: #08090c;
            }
        """)


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Manas Link Hub Analytics")

    window = AnalyticsWindow(app)
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
