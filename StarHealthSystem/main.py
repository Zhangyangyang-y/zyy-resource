import sys
from PySide6.QtWidgets import QApplication
from database import init_db
from ui_main_window import MainWindow

# 应用 qt-material Material Design 主题
from qt_material import apply_stylesheet

# 自定义补充样式（仅针对特有组件，不覆盖 Material 基础样式）
EXTRA_QSS = """
* {
    font-family: "Microsoft YaHei", "Noto Sans SC", "Roboto", sans-serif;
}
QFrame#Card {
    background-color: white;
    border-radius: 12px;
    padding: 16px;
}
QFrame#MetricCard {
    background-color: white;
    border-radius: 10px;
    padding: 14px;
}
QLabel#MetricValue {
    font-size: 24px;
    font-weight: bold;
    color: #1565c0;
}
QLabel#MetricLabel {
    font-size: 12px;
    font-weight: bold;
    color: #546e7a;
}
QLabel#MetricStatus {
    font-size: 13px;
    font-weight: bold;
    padding: 3px 12px;
    border-radius: 10px;
}
QLabel#TitleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #0d47a1;
}
QPushButton#DangerBtn {
    background-color: #e53935;
    color: white;
}
QPushButton#DangerBtn:hover {
    background-color: #c62828;
}
QPushButton#DangerBtn:pressed {
    background-color: #b71c1c;
}
QPushButton#OutlineBtn {
    background-color: transparent;
    color: #1565c0;
    border: 1.5px solid #1565c0;
}
QPushButton#OutlineBtn:hover {
    background-color: #e3f2fd;
}
QStatusBar::item {
    border: none;
}
"""

if __name__ == '__main__':
    init_db()
    app = QApplication(sys.argv)

    # Material Design 主题
    apply_stylesheet(
        app,
        theme='light_blue.xml',
        invert_secondary=False,
    )
    # 在 Material 主题之上叠加自定义样式
    app.setStyleSheet(app.styleSheet() + EXTRA_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
