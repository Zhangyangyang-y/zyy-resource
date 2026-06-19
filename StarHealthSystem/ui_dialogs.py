from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QRadioButton, QPushButton,
                               QGridLayout, QComboBox, QDateEdit, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate


class ShapeAskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("体态评估")
        self.setFixedSize(340, 160)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 28, 30, 28)

        label = QLabel("您的体态正常，是否需要塑形方案？")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1a3c6e;")
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        self.yes_btn = QPushButton("是的，我要塑形")
        self.no_btn = QPushButton("暂时不用")
        self.no_btn.setObjectName("OutlineBtn")
        btn_layout.addWidget(self.yes_btn)
        btn_layout.addWidget(self.no_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.yes_btn.clicked.connect(self.accept)
        self.no_btn.clicked.connect(self.reject)


class NewUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui("新建用户")

    def _build_ui(self, title):
        self.setWindowTitle(title)
        self.setMinimumSize(420, 380)

        layout = QGridLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(28, 24, 28, 24)

        layout.addWidget(QLabel("姓名 *"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入姓名")
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("性别"), 1, 0)
        self.male_radio = QRadioButton("男")
        self.female_radio = QRadioButton("女")
        self.male_radio.setChecked(True)
        gender_layout = QHBoxLayout()
        gender_layout.addWidget(self.male_radio)
        gender_layout.addWidget(self.female_radio)
        gender_layout.addStretch()
        layout.addLayout(gender_layout, 1, 1)

        layout.addWidget(QLabel("身高(cm) *"), 2, 0)
        self.height_edit = QLineEdit()
        self.height_edit.setPlaceholderText("例如 170")
        layout.addWidget(self.height_edit, 2, 1)

        layout.addWidget(QLabel("年龄"), 3, 0)
        self.age_edit = QLineEdit()
        self.age_edit.setPlaceholderText("例如 25")
        layout.addWidget(self.age_edit, 3, 1)

        layout.addWidget(QLabel("活动水平"), 4, 0)
        self.activity_combo = QComboBox()
        self.activity_combo.addItems(["久坐", "轻度活动", "中度活动", "高度活动", "极高活动"])
        layout.addWidget(self.activity_combo, 4, 1)

        layout.addWidget(QLabel("目标体重(kg)"), 5, 0)
        self.target_weight_edit = QLineEdit()
        self.target_weight_edit.setPlaceholderText("可选")
        layout.addWidget(self.target_weight_edit, 5, 1)

        layout.addWidget(QLabel("目标日期"), 6, 0)
        self.target_date_edit = QDateEdit()
        self.target_date_edit.setDate(QDate.currentDate())
        self.target_date_edit.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self.target_date_edit, 6, 1)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box, 7, 0, 1, 2)

        self.setLayout(layout)

    def get_data(self):
        gender = "男" if self.male_radio.isChecked() else "女"
        return (
            self.name_edit.text().strip(),
            gender,
            self.height_edit.text().strip(),
            self.age_edit.text().strip(),
            self.activity_combo.currentText(),
            self.target_weight_edit.text().strip(),
            self.target_date_edit.date().toString("yyyy-MM-dd"),
        )


class EditUserDialog(NewUserDialog):
    def __init__(self, user_info, parent=None):
        self.user_info = user_info
        super().__init__(parent)

    def _build_ui(self, title):
        super()._build_ui("编辑用户")
        # 预填当前值
        self.name_edit.setText(self.user_info.get('name', ''))
        gender = self.user_info.get('gender', '男')
        if gender == '女':
            self.female_radio.setChecked(True)
            self.male_radio.setChecked(False)
        self.height_edit.setText(str(self.user_info.get('height', '')))
        self.age_edit.setText(str(self.user_info.get('age', '')))
        activity_map = {"久坐": 0, "轻度活动": 1, "中度活动": 2, "高度活动": 3, "极高活动": 4}
        ac = self.user_info.get('activity', '中度活动')
        self.activity_combo.setCurrentIndex(activity_map.get(ac, 2))
        tw = self.user_info.get('target_weight', 0)
        if tw:
            self.target_weight_edit.setText(str(tw))
        td = self.user_info.get('target_date', '')
        if td:
            try:
                self.target_date_edit.setDate(QDate.fromString(td, "yyyy-MM-dd"))
            except:
                pass
