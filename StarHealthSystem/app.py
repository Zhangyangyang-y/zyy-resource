import io
import csv
import base64
import os
from datetime import datetime
from functools import wraps

import numpy as np
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, send_file)

import database as db
import calculations as calc

app = Flask(__name__)
app.secret_key = 'star-health-system-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'success': False, 'message': '图片太大，请选择小于20MB的图片。'}), 413


# ===================== 权限装饰器 =====================

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'account_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': '请先登录'})
                return redirect(url_for('welcome'))
            if role and session.get('role') != role:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'message': '权限不足'})
                if session['role'] == 'admin':
                    return redirect(url_for('admin_index'))
                return redirect(url_for('user_dashboard'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ===================== 公共页面 =====================

@app.route('/')
def welcome():
    """欢迎页 / 登陆页"""
    if 'account_id' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_index'))
        return redirect(url_for('user_dashboard'))
    return render_template('welcome.html')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        account = db.verify_login(username, password)
        if account and account['role'] == 'user':
            session['account_id'] = account['id']
            session['role'] = 'user'
            session['display_name'] = account['display_name']
            return redirect(url_for('user_dashboard'))
        return render_template('user_login.html', error='用户名或密码错误')
    return render_template('user_login.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        account = db.verify_login(username, password)
        if account and account['role'] == 'admin':
            session['account_id'] = account['id']
            session['role'] = 'admin'
            session['display_name'] = account['display_name']
            return redirect(url_for('admin_index'))
        return render_template('admin_login.html', error='管理员账号或密码错误')
    return render_template('admin_login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        display_name = request.form.get('display_name', '').strip() or username

        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')
        if password != confirm:
            return render_template('register.html', error='两次密码不一致')
        if len(password) < 4:
            return render_template('register.html', error='密码至少4位')

        success, msg = db.register_account(username, password, display_name)
        if success:
            # 自动登录
            account = db.verify_login(username, password)
            if account:
                session['account_id'] = account['id']
                session['role'] = 'user'
                session['display_name'] = account['display_name']
                return redirect(url_for('user_profile'))
        return render_template('register.html', error=msg)
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))


# ===================== 用户仪表盘 =====================

@app.route('/dashboard')
@login_required(role='user')
def user_dashboard():
    member = db.get_member_by_account(session['account_id'])
    if not member:
        return redirect(url_for('user_profile'))
    mid = member['id']

    records = db.get_member_records(mid)
    latest = records[0] if records else None
    info = dict(member)

    bmi_val = bmi_status = bf_val = bf_status = None
    if latest:
        bmi_val = latest[3]
        bmi_status = latest[4]
        bf_val, bf_status = calc.estimate_body_fat(bmi_val, info['age'], info['gender'])

    stats = db.get_member_stats(mid)

    return render_template('user_dashboard.html', user=info, records=records,
                           latest=latest, bmi_val=bmi_val, bmi_status=bmi_status,
                           bf_val=bf_val, bf_status=bf_status, stats=stats)


@app.route('/profile', methods=['GET', 'POST'])
@login_required(role='user')
def user_profile():
    member = db.get_member_by_account(session['account_id'])

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '男')
        height = request.form.get('height', '').strip()
        age = request.form.get('age', '').strip()
        activity = request.form.get('activity', '中度活动')
        target_weight = request.form.get('target_weight', '').strip()
        target_date = request.form.get('target_date', '').strip()

        if not name or not height:
            return jsonify({'success': False, 'message': '姓名和身高为必填项！'})
        try:
            height = float(height)
        except ValueError:
            return jsonify({'success': False, 'message': '身高请输入有效数字！'})

        if member:
            db.update_member(member['id'], name, gender, height, int(age) if age else 25,
                             activity, float(target_weight) if target_weight else 0, target_date)
            return jsonify({'success': True, 'message': '个人信息已更新！'})
        else:
            ok = db.add_member(name, gender, height, int(age) if age else 25,
                               activity, float(target_weight) if target_weight else 0,
                               target_date, account_id=session['account_id'])
            if ok:
                return jsonify({'success': True, 'message': '个人信息已创建！'})
            return jsonify({'success': False, 'message': '创建失败，姓名可能已存在'})

    info = dict(member) if member else {'name': '', 'gender': '男', 'height': '', 'age': 25,
                                         'activity': '中度活动', 'target_weight': '', 'target_date': ''}
    return render_template('user_form.html', user=info, title='我的资料',
                           is_profile=True, is_new=not member)


# ===================== 管理员首页 =====================

@app.route('/admin')
@login_required(role='admin')
def admin_index():
    members = db.get_all_members()
    total_members = len(members)
    all_stats = {'total_records': 0, 'avg_bmi': 0}
    recent_records = []
    if members:
        record_counts = []
        bmis = []
        for m in members:
            stats = db.get_member_stats(m[0])
            if stats:
                record_counts.append(stats.get('count', 0))
                if stats.get('avg_bmi'):
                    bmis.append(stats['avg_bmi'])
            recs = db.get_member_records(m[0])
            if recs:
                for r in recs[:3]:
                    recent_records.append((m[1], r[1], r[2], r[3], r[4]))
        all_stats['total_records'] = sum(record_counts)
        all_stats['avg_bmi'] = round(np.mean(bmis), 1) if bmis else 0
        recent_records = sorted(recent_records, key=lambda x: x[1], reverse=True)[:10]

    return render_template('index.html', members=members, stats=all_stats,
                           recent_records=recent_records)


# ===================== 成员管理（管理员）=====================

@app.route('/members')
@login_required(role='admin')
def member_list():
    all_members = db.get_all_members()
    member_list = []
    for m in all_members:
        info = db.get_member_full_info(m[0])
        records = db.get_member_records(m[0])
        latest = records[0] if records else None
        member_list.append({
            'id': m[0], 'name': m[1], 'gender': m[2], 'height': m[3],
            'age': info['age'] if info else 25,
            'activity': info['activity'] if info else '中度活动',
            'target_weight': info['target_weight'] if info else 0,
            'record_count': len(records),
            'latest_weight': latest[2] if latest else None,
            'latest_bmi': latest[3] if latest else None,
            'latest_status': latest[4] if latest else None,
        })
    return render_template('members.html', members=member_list)


@app.route('/members/new', methods=['GET', 'POST'])
@login_required(role='admin')
def new_member():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '男')
        height = request.form.get('height', '').strip()
        age = request.form.get('age', '').strip()
        activity = request.form.get('activity', '中度活动')
        target_weight = request.form.get('target_weight', '').strip()
        target_date = request.form.get('target_date', '').strip()

        if not name or not height:
            return jsonify({'success': False, 'message': '姓名和身高为必填项！'})
        try:
            height = float(height)
        except ValueError:
            return jsonify({'success': False, 'message': '身高请输入有效数字！'})

        success = db.add_member(name, gender, height, int(age) if age else 25,
                                activity, float(target_weight) if target_weight else 0, target_date)
        if success:
            return jsonify({'success': True, 'message': f'成员 {name} 创建成功！'})
        return jsonify({'success': False, 'message': '姓名已存在，请使用其他姓名！'})

    return render_template('member_form.html', member=None, title='新建成员')


@app.route('/members/<int:mid>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_member(mid):
    info = db.get_member_full_info(mid)
    if not info:
        return redirect(url_for('member_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        gender = request.form.get('gender', '男')
        height = request.form.get('height', '').strip()
        age = request.form.get('age', '').strip()
        activity = request.form.get('activity', '中度活动')
        target_weight = request.form.get('target_weight', '').strip()
        target_date = request.form.get('target_date', '').strip()

        if not name or not height:
            return jsonify({'success': False, 'message': '姓名和身高为必填项！'})
        try:
            height = float(height)
        except ValueError:
            return jsonify({'success': False, 'message': '身高请输入有效数字！'})

        db.update_member(mid, name, gender, height, int(age) if age else 25,
                         activity, float(target_weight) if target_weight else 0, target_date)
        return jsonify({'success': True, 'message': '成员信息已更新！'})

    return render_template('member_form.html', member=dict(info), title='编辑成员')


@app.route('/members/<int:mid>/delete', methods=['POST'])
@login_required(role='admin')
def delete_member(mid):
    db.delete_member(mid)
    return jsonify({'success': True, 'message': '成员已删除'})


@app.route('/members/<int:mid>')
@login_required(role='admin')
def member_detail(mid):
    info = db.get_member_full_info(mid)
    if not info:
        return redirect(url_for('member_list'))
    info = dict(info)
    records = db.get_member_records(mid)

    latest = records[0] if records else None
    bmi_val = bmi_status = bf_val = bf_status = None
    if latest:
        bmi_val = latest[3]
        bmi_status = latest[4]
        bf_val, bf_status = calc.estimate_body_fat(bmi_val, info['age'], info['gender'])

    stats = db.get_member_stats(mid)

    return render_template('member_detail.html', user=info, records=records,
                           latest=latest, bmi_val=bmi_val, bmi_status=bmi_status,
                           bf_val=bf_val, bf_status=bf_status, stats=stats)


# ===================== BMI 计算 =====================

@app.route('/api/calculate', methods=['POST'])
def calculate():
    mid = request.form.get('member_id', type=int) or request.form.get('user_id', type=int)
    if not mid:
        return jsonify({'success': False, 'message': '请先选择成员！'})

    try:
        weight = float(request.form.get('weight', ''))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '请输入有效体重！'})

    info = db.get_member_full_info(mid)
    if not info:
        return jsonify({'success': False, 'message': '成员不存在！'})

    bmi = calc.calc_bmi(weight, info['height'])
    status = calc.get_bmi_status(bmi)
    bf, bf_status = calc.estimate_body_fat(bmi, info['age'], info['gender'])

    if status == "正常":
        plan_type = None
    else:
        plan_type = "减脂" if status in ["偏胖", "肥胖"] else "增重"

    db.add_record(mid, weight, bmi, status, plan_type)

    return jsonify({
        'success': True, 'bmi': bmi, 'status': status,
        'bf': bf, 'bf_status': bf_status, 'plan_type': plan_type, 'weight': weight,
    })


# ===================== 方案生成 =====================

@app.route('/api/plan', methods=['POST'])
def generate_plan():
    mid = request.form.get('member_id', type=int) or request.form.get('user_id', type=int)
    if not mid:
        return jsonify({'success': False, 'message': '请先选择成员！'})

    plan_type = request.form.get('plan_type', '塑形')
    records = db.get_member_records(mid)
    if not records:
        return jsonify({'success': False, 'message': '暂无体重记录！'})

    latest = records[0]
    weight = latest[2]
    current_bmi = latest[3]
    info = db.get_member_full_info(mid)
    bmr = calc.calc_bmr(weight, info['height'], info['age'], info['gender'])
    tdee = calc.calc_tdee(bmr, info['activity'])

    if plan_type == '减脂':
        target_cal = tdee - 400
    elif plan_type == '增重':
        target_cal = tdee + 400
    else:
        target_cal = tdee + 100

    food_plan, nutrition = calc.generate_food_plan(target_cal, age=info['age'])
    status = calc.get_bmi_status(current_bmi)
    exercise_plan = calc.generate_exercise_plan(status, plan_type, weight, age=info['age'])

    return jsonify({
        'success': True, 'target_cal': round(target_cal),
        'nutrition': {'protein': nutrition[0], 'fat': nutrition[1], 'carb': nutrition[2], 'cal': nutrition[3]},
        'food_plan': [{'meal': f[0], 'food': f[1], 'portion': f[2], 'cal': f[3]} for f in food_plan],
        'exercise_plan': [{'name': e[0], 'duration': e[1], 'cal': e[2]} for e in exercise_plan],
    })


# ===================== 历史记录 =====================

@app.route('/api/records/<int:mid>')
def get_records(mid):
    records = db.get_member_records(mid)
    data = []
    for r in records:
        data.append({
            'id': r[0], 'date': r[1], 'weight': r[2], 'bmi': r[3],
            'status': r[4], 'plan_type': r[5] if r[5] else '无',
        })
    return jsonify(data)


@app.route('/api/records/<int:rid>/delete', methods=['POST'])
def delete_record(rid):
    db.delete_record(rid)
    return jsonify({'success': True})


# ===================== 图表数据 =====================

@app.route('/api/chart/weight/<int:mid>')
def chart_weight(mid):
    records = db.get_member_records(mid)
    if len(records) < 2:
        return jsonify({'labels': [], 'values': [], 'target': None})
    records_rev = list(reversed(records))
    labels = [r[1] for r in records_rev]
    values = [r[2] for r in records_rev]
    info = db.get_member_full_info(mid)
    target = info['target_weight'] if info and info['target_weight'] > 0 else None
    return jsonify({'labels': labels, 'values': values, 'target': target})


@app.route('/api/chart/bmi-distribution/<int:mid>')
def chart_bmi_distribution(mid):
    np.random.seed(42)
    male_bmi = np.random.normal(23.5, 3.0, 250)
    female_bmi = np.random.normal(22.5, 3.0, 250)
    population = np.concatenate([male_bmi, female_bmi]).tolist()
    records = db.get_member_records(mid)
    user_bmi = records[0][3] if records else None
    hist, edges = np.histogram(population, bins=30)
    bins = [round((edges[i] + edges[i + 1]) / 2, 1) for i in range(len(edges) - 1)]
    return jsonify({'hist': hist.tolist(), 'bins': bins, 'user_bmi': user_bmi})


# ===================== 导出 =====================

@app.route('/api/export/<int:mid>')
def export_csv(mid):
    records = db.get_member_records(mid)
    if not records:
        return jsonify({'success': False, 'message': '暂无数据可导出！'})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['日期', '体重(kg)', 'BMI', '体态', '计划类型'])
    for r in records:
        writer.writerow([r[1], r[2], r[3], r[4], r[5] if r[5] else ''])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    return send_file(
        mem, mimetype='text/csv', as_attachment=True,
        download_name=f'体态记录_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    )


# ===================== 体态检测（AI）=====================

@app.route('/posture')
@login_required()
def posture_page():
    return render_template('posture.html')


@app.route('/api/posture/analyze', methods=['POST'])
@login_required()
def analyze_posture():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '请上传图片！'})
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': '请选择图片！'})
    img_bytes = file.read()
    return _analyze_posture_bytes(img_bytes)


@app.route('/api/posture/analyze-camera', methods=['POST'])
@login_required()
def analyze_posture_camera():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'success': False, 'message': '未收到图片数据！'})
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    return _analyze_posture_bytes(img_bytes)


def _analyze_posture_bytes(img_bytes):
    """Core posture analysis"""
    try:
        import cv2
        import mediapipe as mp

        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'success': False, 'message': '图片解码失败，请确认是有效的图片文件。'})

        # Resize large images to prevent memory issues and speed up processing
        h, w, _ = img.shape
        max_dim = 1280
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        model_path = os.path.join(os.path.dirname(__file__), 'pose_landmarker_lite.task')
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
        )

        with PoseLandmarker.create_from_options(options) as landmarker:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            result = landmarker.detect(mp_image)

            if not result.pose_landmarks or len(result.pose_landmarks) == 0:
                return jsonify({
                    'success': False,
                    'message': '未检测到人体，请确保照片中清晰可见全身或上半身。'
                })

            landmarks = result.pose_landmarks[0]

            LEFT_EAR, RIGHT_EAR = 7, 8
            LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
            LEFT_HIP, RIGHT_HIP = 23, 24

            def get_pt(idx):
                lm = landmarks[idx]
                return np.array([lm.x * w, lm.y * h])

            def angle_between(p1, p2, p3):
                v1 = p1 - p2
                v2 = p3 - p2
                cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
                return np.degrees(np.arccos(np.clip(cos_a, -1, 1)))

            def shoulder_slope():
                ls = get_pt(LEFT_SHOULDER)
                rs = get_pt(RIGHT_SHOULDER)
                angle = np.degrees(np.arctan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0])))
                return 90 - angle

            left_ear = get_pt(LEFT_EAR)
            right_ear = get_pt(RIGHT_EAR)
            left_shoulder = get_pt(LEFT_SHOULDER)
            right_shoulder = get_pt(RIGHT_SHOULDER)
            mid_ear_x = (left_ear[0] + right_ear[0]) / 2
            mid_shoulder_x = (left_shoulder[0] + right_shoulder[0]) / 2
            mid_shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2

            # Head forward
            ear_shoulder_dist_l = abs(left_ear[0] - left_shoulder[0])
            ear_shoulder_dist_r = abs(right_ear[0] - right_shoulder[0])
            fhp_ratio = ((ear_shoulder_dist_l + ear_shoulder_dist_r) / 2) / w
            fhp_severity = 'severe' if fhp_ratio > 0.14 else ('mild' if fhp_ratio > 0.08 else 'normal')

            # Rounded shoulders
            round_shoulder_ratio = abs(mid_shoulder_x - mid_ear_x) / w
            round_shoulder_severity = 'severe' if round_shoulder_ratio > 0.12 else ('mild' if round_shoulder_ratio > 0.06 else 'normal')

            # Kyphosis
            mid_hip = (get_pt(LEFT_HIP) + get_pt(RIGHT_HIP)) / 2
            shoulder_hip_angle = angle_between(get_pt(LEFT_SHOULDER), np.array([mid_shoulder_x, mid_shoulder_y]), mid_hip)
            kyphosis_deviation = abs(shoulder_hip_angle - 90)
            kyphosis_severity = 'severe' if kyphosis_deviation > 30 else ('mild' if kyphosis_deviation > 15 else 'normal')

            # Uneven shoulders
            slope = shoulder_slope()
            shoulder_severity = 'severe' if slope > 12 else ('mild' if slope > 5 else 'normal')

            # Scoliosis
            shoulder_line = get_pt(LEFT_SHOULDER) - get_pt(RIGHT_SHOULDER)
            hip_line = get_pt(LEFT_HIP) - get_pt(RIGHT_HIP)
            cosine_sim = np.dot(shoulder_line, hip_line) / (np.linalg.norm(shoulder_line) * np.linalg.norm(hip_line) + 1e-6)
            spine_angle = np.degrees(np.arccos(np.clip(cosine_sim, -1, 1)))
            scoliosis_severity = 'severe' if spine_angle > 20 else ('mild' if spine_angle > 10 else 'normal')

            severity_map = {'normal': 0, 'mild': 1, 'severe': 2}
            issues = []
            total_score = 0
            assessments = [
                ('head_forward', '头前伸', fhp_severity),
                ('rounded_shoulders', '圆肩', round_shoulder_severity),
                ('kyphosis', '驼背', kyphosis_severity),
                ('uneven_shoulder', '高低肩', shoulder_severity),
                ('scoliosis', '脊柱侧弯', scoliosis_severity),
            ]
            details = {}
            for key, label, severity in assessments:
                details[key] = {'label': label, 'severity': severity, 'level': severity_map[severity]}
                if severity != 'normal':
                    issues.append(f'{label}({severity})')
                total_score += severity_map[severity]
            overall = max(0, 10 - total_score)
            summary = '体态良好，无明显异常。继续保持！' if not issues else \
                f'检测到以下问题：{"；".join(issues)}。建议咨询专业康复师进行针对性矫正训练。'

            annotated = img.copy()
            connections = mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS
            color = (74, 108, 247)
            for conn in connections:
                x1, y1 = int(landmarks[conn.start].x * w), int(landmarks[conn.start].y * h)
                x2, y2 = int(landmarks[conn.end].x * w), int(landmarks[conn.end].y * h)
                cv2.line(annotated, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            for lm in landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(annotated, (cx, cy), 4, (255, 255, 255), -1)
                cv2.circle(annotated, (cx, cy), 4, color, 1, cv2.LINE_AA)

            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_base64 = base64.b64encode(buffer).decode('utf-8')

            return jsonify({
                'success': True, 'overall_score': overall, 'summary': summary,
                'issues': issues, 'details': details,
                'annotated_image': f'data:image/jpeg;base64,{img_base64}',
                'metrics': {
                    'fhp_ratio': round(fhp_ratio, 3),
                    'round_shoulder_ratio': round(round_shoulder_ratio, 3),
                    'kyphosis_deviation': round(kyphosis_deviation, 1),
                    'shoulder_slope': round(slope, 1),
                    'spine_angle': round(spine_angle, 1),
                },
                'landmarks_detected': len(landmarks),
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'分析出错：{str(e)}'})


# ===================== 数据库初始化 =====================

db.init_db()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
