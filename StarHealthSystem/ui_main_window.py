from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QFrame, QMessageBox, QStatusBar, QProgressBar, QSizePolicy,
    QGridLayout
)
from PySide6.QtCore import Qt
import csv
from datetime import datetime
import numpy as np

from ui_dialogs import ShapeAskDialog, NewUserDialog, EditUserDialog
from ui_components import MplCanvas
import database as db
import calculations as calc


class MetricCard(QFrame):
    """仪表盘指标卡片"""

    def __init__(self, title, value="--", status="", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricLabel")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        layout.addWidget(self.value_label)

        self.status_label = QLabel(status)
        self.status_label.setObjectName("MetricStatus")
        layout.addWidget(self.status_label)

    def update(self, value="--", status="", status_color=None):
        self.value_label.setText(str(value))
        self.status_label.setText(status)
        if status_color:
            self.status_label.setStyleSheet(
                f"font-size:13px; font-weight:bold; padding:2px 10px; "
                f"border-radius:10px; background-color:{status_color}20; color:{status_color};"
            )
        else:
            self.status_label.setStyleSheet("")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("星衡体态 · 智能健康管理系统")
        self.setGeometry(100, 100, 1250, 850)

        self.current_user_id = None
        self.current_gender = None
        self.current_height = None
        self.current_age = 25
        self.current_activity = "中度活动"
        self.current_target_weight = 0
        self.current_target_date = ""
        self.plan_type = None

        self.init_ui()
        self.load_users()

    # ==================== UI 构建 ====================

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(28, 24, 28, 24)

        # ---- 标题 ----
        title = QLabel("星衡体态 · 智能健康管理系统")
        title.setObjectName("TitleLabel")
        main_layout.addWidget(title)

        # ---- Dashboard 指标卡 ----
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(14)
        self.bmi_card = MetricCard("BMI 指数", "--")
        self.bf_card = MetricCard("体脂率", "--")
        self.status_card = MetricCard("体态评估", "--")
        self.progress_card = MetricCard("目标进度", "--")
        dash_layout.addWidget(self.bmi_card)
        dash_layout.addWidget(self.bf_card)
        dash_layout.addWidget(self.status_card)
        dash_layout.addWidget(self.progress_card)
        main_layout.addLayout(dash_layout)

        # ---- 用户管理 ----
        user_card = QFrame()
        user_card.setObjectName("Card")
        user_row = QHBoxLayout(user_card)
        user_row.setContentsMargins(16, 10, 16, 10)
        user_row.setSpacing(10)

        user_label = QLabel("当前用户")
        user_label.setObjectName("MetricLabel")
        user_row.addWidget(user_label)

        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        self.user_combo.currentIndexChanged.connect(self.on_user_changed)
        user_row.addWidget(self.user_combo)

        user_row.addStretch()

        self.new_user_btn = QPushButton("新建用户")
        self.new_user_btn.clicked.connect(self.create_user)
        user_row.addWidget(self.new_user_btn)

        self.edit_user_btn = QPushButton("编辑用户")
        self.edit_user_btn.setObjectName("OutlineBtn")
        self.edit_user_btn.clicked.connect(self.edit_user)
        self.edit_user_btn.setEnabled(False)
        user_row.addWidget(self.edit_user_btn)

        self.delete_user_btn = QPushButton("删除用户")
        self.delete_user_btn.setObjectName("DangerBtn")
        self.delete_user_btn.clicked.connect(self.delete_user)
        self.delete_user_btn.setEnabled(False)
        user_row.addWidget(self.delete_user_btn)

        self.export_btn = QPushButton("导出 CSV")
        self.export_btn.setObjectName("OutlineBtn")
        self.export_btn.clicked.connect(self.export_csv)
        user_row.addWidget(self.export_btn)

        main_layout.addWidget(user_card)

        # ---- BMI 计算 ----
        calc_card = QFrame()
        calc_card.setObjectName("Card")
        calc_row = QHBoxLayout(calc_card)
        calc_row.setContentsMargins(16, 12, 16, 12)
        calc_row.setSpacing(12)

        calc_row.addWidget(QLabel("体重 (kg)"))
        self.weight_edit = QLineEdit()
        self.weight_edit.setPlaceholderText("请输入当前体重")
        self.weight_edit.setFixedWidth(160)
        self.weight_edit.returnPressed.connect(self.calculate)
        calc_row.addWidget(self.weight_edit)

        self.calc_btn = QPushButton("计算 BMI")
        self.calc_btn.clicked.connect(self.calculate)
        calc_row.addWidget(self.calc_btn)

        self.result_label = QLabel("BMI: --  状态: --")
        self.result_label.setStyleSheet("font-size: 15px; font-weight: bold; padding: 0 8px;")
        calc_row.addWidget(self.result_label)

        self.plan_btn = QPushButton("生成个性化饮食/运动方案")
        self.plan_btn.setEnabled(False)
        self.plan_btn.clicked.connect(self.generate_plan)
        self.plan_btn.setFixedHeight(36)
        calc_row.addWidget(self.plan_btn)

        calc_row.addStretch()
        main_layout.addWidget(calc_card)

        # ---- Tab ----
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # 饮食
        self.food_table = QTableWidget()
        self.food_table.setColumnCount(4)
        self.food_table.setHorizontalHeaderLabels(['餐次', '食物', '份量', '热量(kcal)'])
        self.food_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.food_table.setAlternatingRowColors(True)

        # 运动
        self.exercise_table = QTableWidget()
        self.exercise_table.setColumnCount(3)
        self.exercise_table.setHorizontalHeaderLabels(['运动项目', '时长', '消耗热量(kcal)'])
        self.exercise_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.exercise_table.setAlternatingRowColors(True)

        # 历史
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(['日期', '体重(kg)', 'BMI', '体态', '计划类型', '操作'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 图表
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(16, 12, 16, 12)
        chart_top = QHBoxLayout()
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(["体重变化曲线", "人群BMI分布"])
        self.chart_combo.currentTextChanged.connect(self.update_chart)
        chart_top.addWidget(QLabel("图表类型:"))
        chart_top.addWidget(self.chart_combo)
        chart_top.addStretch()
        chart_layout.addLayout(chart_top)
        self.canvas = MplCanvas()
        chart_layout.addWidget(self.canvas)

        # 统计
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(12)
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)
        stats_layout.addLayout(self.stats_grid)
        stats_layout.addStretch()

        self.stats_labels = {}
        stats_fields = [
            ("记录总数", "total_records"),
            ("最新体重", "latest_weight"),
            ("最新 BMI", "latest_bmi"),
            ("平均 BMI", "avg_bmi"),
            ("最高 BMI", "max_bmi"),
            ("最低 BMI", "min_bmi"),
            ("体重变化", "weight_change"),
            ("平均体重", "avg_weight"),
        ]
        for i, (label, key) in enumerate(stats_fields):
            card = QFrame()
            card.setObjectName("MetricCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.addWidget(QLabel(label))
            val = QLabel("--")
            val.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a3c6e;")
            cl.addWidget(val)
            self.stats_labels[key] = val
            self.stats_grid.addWidget(card, i // 4, i % 4)

        self.tab_widget.addTab(self.food_table, "饮食计划")
        self.tab_widget.addTab(self.exercise_table, "运动计划")
        self.tab_widget.addTab(self.history_table, "历史记录")
        self.tab_widget.addTab(chart_widget, "数据图表")
        self.tab_widget.addTab(stats_widget, "统计分析")

        main_layout.addWidget(self.tab_widget, 1)

    # ==================== 用户管理 ====================

    def load_users(self):
        users = db.get_all_users()
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        if users:
            for u in users:
                self.user_combo.addItem(f"{u[1]} ({u[2]}, {u[3]}cm)", u[0])
            self.user_combo.blockSignals(False)
            self.on_user_changed(0)
        else:
            self.user_combo.addItem("-- 请先创建用户 --", -1)
            self.user_combo.blockSignals(False)
            self.clear_dashboard()

    def on_user_changed(self, index):
        uid = self.user_combo.currentData()
        if uid == -1 or uid is None:
            self.current_user_id = None
            self.edit_user_btn.setEnabled(False)
            self.delete_user_btn.setEnabled(False)
            self.clear_dashboard()
            return

        self.current_user_id = uid
        info = db.get_user_full_info(uid)
        if info:
            self.current_gender = info['gender']
            self.current_height = info['height']
            self.current_age = info['age'] or 25
            self.current_activity = info['activity'] or "中度活动"
            self.current_target_weight = info['target_weight'] or 0
            self.current_target_date = info.get('target_date', '') or ''
            self.edit_user_btn.setEnabled(True)
            self.delete_user_btn.setEnabled(True)

        self.load_history()
        self.update_dashboard()
        self.update_chart()
        self.statusBar().showMessage(f"当前用户: {self.user_combo.currentText()}")

    def create_user(self):
        dialog = NewUserDialog(self)
        if dialog.exec():
            name, gender, height, age, activity, target_weight, target_date = dialog.get_data()
            if not name or not height:
                QMessageBox.warning(self, "提示", "姓名和身高为必填项！")
                return
            try:
                height = float(height)
            except ValueError:
                QMessageBox.warning(self, "提示", "身高请输入有效数字！")
                return
            if db.add_user(name, gender, height, age, activity, target_weight, target_date):
                self.load_users()
                QMessageBox.information(self, "成功", f"用户 {name} 创建成功！")
            else:
                QMessageBox.warning(self, "提示", "用户名已存在，请使用其他姓名！")

    def edit_user(self):
        if not self.current_user_id:
            return
        info = db.get_user_full_info(self.current_user_id)
        if not info:
            return
        dialog = EditUserDialog(info, self)
        if dialog.exec():
            name, gender, height, age, activity, target_weight, target_date = dialog.get_data()
            if not name or not height:
                QMessageBox.warning(self, "提示", "姓名和身高为必填项！")
                return
            try:
                height = float(height)
            except ValueError:
                QMessageBox.warning(self, "提示", "身高请输入有效数字！")
                return
            db.update_user(self.current_user_id, name, gender, height, age, activity, target_weight, target_date)
            self.load_users()
            QMessageBox.information(self, "成功", "用户信息已更新！")

    def delete_user(self):
        if not self.current_user_id:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            "确定删除该用户及其所有记录？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_user(self.current_user_id)
            self.current_user_id = None
            self.load_users()
            self.clear_dashboard()
            self.statusBar().showMessage("用户已删除")

    # ==================== BMI 计算 ====================

    def calculate(self):
        if not self.current_user_id:
            QMessageBox.warning(self, "提示", "请先选择用户！")
            return
        try:
            weight = float(self.weight_edit.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效体重！")
            return

        bmi = calc.calc_bmi(weight, self.current_height)
        status = calc.get_bmi_status(bmi)

        # 体脂率
        bf, bf_status = calc.estimate_body_fat(bmi, self.current_age, self.current_gender)

        # 颜色
        color_map = {"偏瘦": "#3498db", "正常": "#27ae60", "偏胖": "#f39c12", "肥胖": "#e74c3c"}
        c = color_map.get(status, "#7a8ba3")
        self.result_label.setStyleSheet(f"font-size:15px; font-weight:bold; color:{c}; padding:0 8px;")
        self.result_label.setText(f"BMI: {bmi}  状态: {status}  体脂率: {bf}%")

        if status == "正常":
            if ShapeAskDialog().exec():
                self.plan_type = "塑形"
            else:
                self.plan_type = None
        else:
            self.plan_type = "减脂" if status in ["偏胖", "肥胖"] else "增重"

        self.plan_btn.setEnabled(self.plan_type is not None)
        db.add_record(self.current_user_id, weight, bmi, status, self.plan_type)
        self.load_history()
        self.update_dashboard()
        self.update_chart()
        self.statusBar().showMessage(f"BMI 计算完成，记录已保存 | 体脂率: {bf}% ({bf_status})")

    # ==================== 方案生成 ====================

    def generate_plan(self):
        if not self.current_user_id or self.plan_type is None:
            QMessageBox.warning(self, "提示", "请先完成 BMI 计算！")
            return

        records = db.get_user_records(self.current_user_id)
        if not records:
            QMessageBox.warning(self, "提示", "暂无体重记录！")
            return
        latest = records[0]
        weight = latest[2]
        current_bmi = latest[3]

        # 计算热量，使用用户实际年龄和活动水平
        bmr = calc.calc_bmr(weight, self.current_height, self.current_age, self.current_gender)
        tdee = calc.calc_tdee(bmr, self.current_activity)

        if self.plan_type == '减脂':
            target_cal = tdee - 400
        elif self.plan_type == '增重':
            target_cal = tdee + 400
        else:
            target_cal = tdee + 100

        # 修复: 解包返回值
        food_plan, nutrition = calc.generate_food_plan(target_cal, age=self.current_age)
        self.food_table.setRowCount(len(food_plan))
        for i, row in enumerate(food_plan):
            self.food_table.setItem(i, 0, QTableWidgetItem(row[0]))
            self.food_table.setItem(i, 1, QTableWidgetItem(row[1]))
            self.food_table.setItem(i, 2, QTableWidgetItem(row[2]))
            self.food_table.setItem(i, 3, QTableWidgetItem(str(row[3])))

        # 显示营养信息
        protein, fat, carb, cal = nutrition
        nutrition_text = f"蛋白质: {protein}g  脂肪: {fat}g  碳水: {carb}g  总热量: {cal}kcal"
        self.statusBar().showMessage(
            f"方案生成完成 | 目标: {round(target_cal)} kcal/日 | {nutrition_text}"
        )

        status = calc.get_bmi_status(current_bmi)
        exercise_plan = calc.generate_exercise_plan(status, self.plan_type, weight, age=self.current_age)
        self.exercise_table.setRowCount(len(exercise_plan))
        for i, row in enumerate(exercise_plan):
            self.exercise_table.setItem(i, 0, QTableWidgetItem(row[0]))
            self.exercise_table.setItem(i, 1, QTableWidgetItem(row[1]))
            self.exercise_table.setItem(i, 2, QTableWidgetItem(str(row[2])))

        self.tab_widget.setCurrentIndex(0)

    # ==================== 历史记录 ====================

    def load_history(self):
        self.history_table.setRowCount(0)
        if not self.current_user_id:
            return
        records = db.get_user_records(self.current_user_id)
        self.history_table.setRowCount(len(records))
        for i, rec in enumerate(records):
            self.history_table.setItem(i, 0, QTableWidgetItem(str(rec[1])))  # date
            self.history_table.setItem(i, 1, QTableWidgetItem(str(rec[2])))  # weight
            self.history_table.setItem(i, 2, QTableWidgetItem(str(rec[3])))  # bmi
            self.history_table.setItem(i, 3, QTableWidgetItem(rec[4]))        # status
            self.history_table.setItem(i, 4, QTableWidgetItem(rec[5] if rec[5] else "无"))  # plan_type

            # 删除按钮
            del_btn = QPushButton("删除")
            del_btn.setObjectName("DangerBtn")
            del_btn.setFixedSize(60, 28)
            del_btn.clicked.connect(lambda checked, rid=rec[0]: self.delete_record(rid))
            self.history_table.setCellWidget(i, 5, del_btn)

    def delete_record(self, record_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该条记录？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_record(record_id)
            self.load_history()
            self.update_dashboard()
            self.update_chart()
            self.statusBar().showMessage("记录已删除")

    def export_csv(self):
        if not self.current_user_id:
            QMessageBox.warning(self, "提示", "请先选择用户！")
            return
        records = db.get_user_records(self.current_user_id)
        if not records:
            QMessageBox.information(self, "提示", "暂无数据可导出！")
            return

        filename = f"体态记录_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '体重(kg)', 'BMI', '体态', '计划类型'])
            for r in records:
                writer.writerow([r[1], r[2], r[3], r[4], r[5] if r[5] else ""])
        QMessageBox.information(self, "成功", f"数据已导出至: {filename}")

    # ==================== Dashboard ====================

    def update_dashboard(self):
        if not self.current_user_id:
            self.clear_dashboard()
            return

        records = db.get_user_records(self.current_user_id)
        if not records:
            self.bmi_card.update("--", "暂无数据")
            self.bf_card.update("--", "")
            self.status_card.update("--", "")
            self.progress_card.update("--", "")
            return

        latest = records[0]
        weight, bmi, status = latest[2], latest[3], latest[4]

        # BMI 卡片
        color_map = {"偏瘦": "#3498db", "正常": "#27ae60", "偏胖": "#f39c12", "肥胖": "#e74c3c"}
        c = color_map.get(status, "#7a8ba3")
        self.bmi_card.update(f"{bmi}", status, c)

        # 体脂率卡片
        bf, bf_status = calc.estimate_body_fat(bmi, self.current_age, self.current_gender)
        bf_color = "#27ae60" if bf_status == "标准" else "#f39c12" if bf_status == "偏高" else "#3498db"
        self.bf_card.update(f"{bf}%", bf_status, bf_color)

        # 体态卡片
        self.status_card.update(status, "", c)

        # 目标进度卡片
        if self.current_target_weight and self.current_target_weight > 0:
            diff = weight - self.current_target_weight
            if abs(diff) < 0.5:
                self.progress_card.update("已达标", "目标达成!")
            elif diff > 0:
                self.progress_card.update(f"还需减 {diff:.1f}kg", "进行中", "#f39c12")
            else:
                self.progress_card.update(f"还需增 {abs(diff):.1f}kg", "进行中", "#3498db")
        else:
            self.progress_card.update("--", "未设定目标")

        # 统计 tab
        stats = db.get_user_stats(self.current_user_id)
        for key, label in self.stats_labels.items():
            val = stats.get(key, "--")
            if val is not None:
                label.setText(str(val))
            else:
                label.setText("--")

    def clear_dashboard(self):
        self.bmi_card.update("--", "")
        self.bf_card.update("--", "")
        self.status_card.update("--", "")
        self.progress_card.update("--", "")
        self.result_label.setText("BMI: --  状态: --")
        self.result_label.setStyleSheet("font-size:15px; font-weight:bold; padding:0 8px;")
        self.plan_btn.setEnabled(False)

    # ==================== 图表 ====================

    def update_chart(self):
        self.canvas.axes.clear()
        self.canvas.style_axes()

        if self.chart_combo.currentText() == "体重变化曲线":
            records = db.get_user_records(self.current_user_id)
            if records and len(records) > 1:
                records_rev = list(reversed(records))
                try:
                    dates = [datetime.strptime(r[1], "%Y-%m-%d %H:%M") for r in records_rev]
                    weights = [r[2] for r in records_rev]
                    self.canvas.axes.plot(dates, weights, color=self.canvas.colors['primary'],
                                          linewidth=2, marker='o', markersize=5,
                                          label='体重')
                    # 目标体重参考线
                    if self.current_target_weight and self.current_target_weight > 0:
                        self.canvas.axes.axhline(self.current_target_weight,
                                                 color=self.canvas.colors['accent'],
                                                 linestyle='--', linewidth=1.5,
                                                 label=f"目标: {self.current_target_weight}kg")
                    self.canvas.axes.set_title("体重变化趋势", fontweight='bold', fontsize=13, color=self.canvas.colors['text'])
                    self.canvas.axes.legend(frameon=True, facecolor='white', edgecolor='#e2eaf2')
                except Exception:
                    self.canvas.axes.text(0.5, 0.5, '数据格式异常', ha='center', va='center',
                                          transform=self.canvas.axes.transAxes, fontsize=12)
            else:
                self.canvas.axes.text(0.5, 0.5, '至少需要 2 条记录才能绘制趋势图', ha='center', va='center',
                                      transform=self.canvas.axes.transAxes, fontsize=12, color='#7a8ba3')
        else:
            np.random.seed(42)
            male_bmi = np.random.normal(23.5, 3.0, 250)
            female_bmi = np.random.normal(22.5, 3.0, 250)
            data = np.concatenate([male_bmi, female_bmi])

            self.canvas.axes.hist(data, bins=30, alpha=0.65, color=self.canvas.colors['primary'],
                                  edgecolor='white', linewidth=0.5)
            self.canvas.axes.set_title('人群 BMI 分布', fontweight='bold', fontsize=13, color=self.canvas.colors['text'])
            self.canvas.axes.set_xlabel('BMI', fontsize=11)
            self.canvas.axes.set_ylabel('人数', fontsize=11)

            records = db.get_user_records(self.current_user_id)
            if records:
                user_bmi = records[0][3]
                self.canvas.axes.axvline(user_bmi, color=self.canvas.colors['accent'],
                                         linestyle='--', linewidth=2.5,
                                         label=f"您的 BMI: {user_bmi}")
                self.canvas.axes.legend(frameon=True, facecolor='white', edgecolor='#e2eaf2')

        self.canvas.fig.tight_layout()
        self.canvas.draw()
