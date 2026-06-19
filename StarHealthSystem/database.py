import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "star_health.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ── 1. 迁移旧表：users → members ──
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    has_old_users = c.fetchone() is not None

    if has_old_users:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'")
        if not c.fetchone():
            c.execute("ALTER TABLE users RENAME TO members")

    # ── 2. 创建 members 表 ──
    c.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        gender TEXT NOT NULL,
        height REAL NOT NULL,
        age INTEGER NOT NULL DEFAULT 25,
        activity TEXT NOT NULL DEFAULT '中度活动',
        target_weight REAL DEFAULT 0,
        target_date TEXT,
        account_id INTEGER,
        created_at TEXT NOT NULL
    )''')

    # ── 3. 兼容旧表字段 ──
    c.execute("PRAGMA table_info(members)")
    cols = {col[1] for col in c.fetchall()}
    for col, sql in [
        ('account_id', "ALTER TABLE members ADD COLUMN account_id INTEGER"),
        ('age', "ALTER TABLE members ADD COLUMN age INTEGER NOT NULL DEFAULT 25"),
        ('activity', "ALTER TABLE members ADD COLUMN activity TEXT NOT NULL DEFAULT '中度活动'"),
        ('target_weight', "ALTER TABLE members ADD COLUMN target_weight REAL DEFAULT 0"),
        ('target_date', "ALTER TABLE members ADD COLUMN target_date TEXT"),
    ]:
        if col not in cols:
            c.execute(sql)

    # ── 4. 迁移 records 表：user_id → member_id ──
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
    if c.fetchone():
        c.execute("PRAGMA table_info(records)")
        rec_cols = {col[1] for col in c.fetchall()}
        if 'user_id' in rec_cols and 'member_id' not in rec_cols:
            c.execute('''CREATE TABLE records_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                bmi REAL NOT NULL,
                status TEXT NOT NULL,
                plan_type TEXT,
                recorded_at TEXT NOT NULL
            )''')
            c.execute("INSERT INTO records_new (id, member_id, weight, bmi, status, plan_type, recorded_at) "
                      "SELECT id, user_id, weight, bmi, status, plan_type, recorded_at FROM records")
            c.execute("DROP TABLE records")
            c.execute("ALTER TABLE records_new RENAME TO records")
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            weight REAL NOT NULL,
            bmi REAL NOT NULL,
            status TEXT NOT NULL,
            plan_type TEXT,
            recorded_at TEXT NOT NULL
        )''')

    # ── 5. 创建 accounts 表（登录账号）──
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        display_name TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )''')

    # 种子默认管理员（首次启动时创建）
    c.execute("SELECT COUNT(*) FROM accounts WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO accounts (username, password_hash, role, display_name, created_at) VALUES (?,?,?,?,?)",
                  ('zyy', generate_password_hash('1234'), 'admin', '管理员',
                   datetime.now().strftime('%Y-%m-%d %H:%M')))
    else:
        # 将旧的 admin 账号更新为 zyy/1234
        c.execute("UPDATE accounts SET username='zyy', password_hash=?, display_name='管理员' WHERE role='admin' AND username='admin'",
                  (generate_password_hash('1234'),))

    # ── 6. 食物 & 运动种子数据（不变）──
    c.execute('''CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cal_per_100g REAL NOT NULL,
        protein REAL NOT NULL,
        fat REAL NOT NULL,
        carb REAL NOT NULL,
        category TEXT NOT NULL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        met REAL NOT NULL,
        type TEXT NOT NULL)''')

    c.execute("SELECT COUNT(*) FROM foods")
    if c.fetchone()[0] == 0:
        foods = [
            ('米饭', 116, 2.6, 0.3, 25.9, '主食'),
            ('馒头', 223, 7.0, 1.1, 44.2, '主食'),
            ('面条', 137, 4.5, 0.5, 28.5, '主食'),
            ('燕麦', 367, 13.5, 6.7, 66.3, '主食'),
            ('红薯', 86, 1.6, 0.1, 20.1, '主食'),
            ('鸡胸肉', 133, 31.0, 1.2, 0.0, '肉类'),
            ('鸡蛋', 144, 13.3, 8.8, 2.8, '肉类'),
            ('牛肉', 125, 22.3, 3.6, 0.2, '肉类'),
            ('猪瘦肉', 143, 20.3, 6.2, 1.5, '肉类'),
            ('三文鱼', 139, 17.2, 7.8, 0.0, '肉类'),
            ('西兰花', 36, 4.1, 0.6, 4.3, '蔬菜'),
            ('菠菜', 28, 3.0, 0.6, 2.8, '蔬菜'),
            ('番茄', 20, 0.9, 0.2, 4.0, '蔬菜'),
            ('胡萝卜', 39, 1.0, 0.2, 8.8, '蔬菜'),
            ('苹果', 54, 0.2, 0.2, 13.5, '水果'),
            ('香蕉', 93, 1.4, 0.2, 22.0, '水果'),
            ('橙子', 48, 0.8, 0.2, 11.1, '水果'),
            ('全脂牛奶', 61, 3.2, 3.2, 4.8, '乳制品'),
            ('酸奶', 72, 2.5, 2.7, 9.3, '乳制品'),
            ('坚果(混合)', 607, 20.0, 53.0, 16.0, '零食'),
            ('橄榄油', 899, 0.0, 99.9, 0.0, '油脂'),
            ('豆腐', 81, 8.1, 3.7, 4.2, '豆制品')
        ]
        c.executemany("INSERT INTO foods (name, cal_per_100g, protein, fat, carb, category) VALUES (?,?,?,?,?,?)", foods)

    c.execute("SELECT COUNT(*) FROM exercises")
    if c.fetchone()[0] == 0:
        exercises = [
            ('慢跑', 7.0, '有氧'), ('快走', 4.5, '有氧'), ('游泳', 8.0, '有氧'),
            ('跳绳', 10.0, '有氧'), ('骑行', 6.0, '有氧'), ('深蹲', 5.0, '力量'),
            ('俯卧撑', 4.0, '力量'), ('引体向上', 5.5, '力量'), ('卧推', 4.5, '力量'),
            ('硬拉', 6.0, '力量'), ('瑜伽', 2.5, '柔韧'), ('HIIT', 12.0, '有氧')
        ]
        c.executemany("INSERT INTO exercises (name, met, type) VALUES (?,?,?)", exercises)

    conn.commit()
    conn.close()


# ==================== 账号系统 ====================

def verify_login(username, password):
    """验证登录，成功返回 account dict，失败返回 None"""
    conn = get_connection()
    account = conn.execute(
        "SELECT id, username, password_hash, role, display_name FROM accounts WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    if account and check_password_hash(account['password_hash'], password):
        return dict(account)
    return None


def get_account_by_id(aid):
    conn = get_connection()
    acct = conn.execute("SELECT id, username, role, display_name FROM accounts WHERE id=?", (aid,)).fetchone()
    conn.close()
    return dict(acct) if acct else None


def register_account(username, password, display_name):
    """注册新用户账号，返回 (success, message)"""
    try:
        conn = get_connection()
        pw_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO accounts (username, password_hash, role, display_name, created_at) VALUES (?,?,?,?,?)",
            (username, pw_hash, 'user', display_name, datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        conn.commit()
        conn.close()
        return True, '注册成功'
    except sqlite3.IntegrityError:
        return False, '用户名已存在'


def get_member_by_account(account_id):
    """根据账号ID获取关联的 member 记录"""
    conn = get_connection()
    member = conn.execute("SELECT * FROM members WHERE account_id=?", (account_id,)).fetchone()
    conn.close()
    return dict(member) if member else None


def link_member_to_account(member_id, account_id):
    conn = get_connection()
    conn.execute("UPDATE members SET account_id=? WHERE id=?", (account_id, member_id))
    conn.commit()
    conn.close()


# ==================== 成员操作（原用户操作）====================

def get_all_members():
    conn = get_connection()
    members = conn.execute("SELECT id, name, gender, height FROM members ORDER BY id").fetchall()
    conn.close()
    return members


def get_member_by_id(mid):
    conn = get_connection()
    member = conn.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
    conn.close()
    return member


def add_member(name, gender, height, age, activity, target_weight, target_date, account_id=None):
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO members (name, gender, height, age, activity, target_weight, target_date, account_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (name, gender, height, int(age) if age else 25, activity,
             float(target_weight) if target_weight else 0, target_date, account_id,
             datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def update_member(mid, name, gender, height, age, activity, target_weight, target_date):
    conn = get_connection()
    conn.execute(
        "UPDATE members SET name=?, gender=?, height=?, age=?, activity=?, target_weight=?, target_date=? WHERE id=?",
        (name, gender, float(height), int(age) if age else 25, activity,
         float(target_weight) if target_weight else 0, target_date, mid)
    )
    conn.commit()
    conn.close()
    return True


def delete_member(mid):
    conn = get_connection()
    conn.execute("DELETE FROM records WHERE member_id=?", (mid,))
    conn.execute("DELETE FROM members WHERE id=?", (mid,))
    conn.commit()
    conn.close()


def get_member_full_info(mid):
    conn = get_connection()
    member = conn.execute(
        "SELECT id, name, gender, height, age, activity, target_weight, target_date FROM members WHERE id=?", (mid,)
    ).fetchone()
    conn.close()
    return dict(member) if member else None


def get_member_stats(mid):
    conn = get_connection()
    row = conn.execute("""
        SELECT COUNT(*) as count,
               ROUND(AVG(bmi),1) as avg_bmi,
               ROUND(MIN(bmi),1) as min_bmi,
               ROUND(MAX(bmi),1) as max_bmi,
               ROUND(AVG(weight),1) as avg_weight,
               ROUND(MIN(weight),1) as min_weight,
               ROUND(MAX(weight),1) as max_weight
        FROM records WHERE member_id=?
    """, (mid,)).fetchone()
    latest = conn.execute(
        "SELECT weight, bmi, recorded_at FROM records WHERE member_id=? ORDER BY recorded_at DESC LIMIT 1",
        (mid,)
    ).fetchone()
    earliest = conn.execute(
        "SELECT weight FROM records WHERE member_id=? ORDER BY recorded_at ASC LIMIT 1",
        (mid,)
    ).fetchone()
    conn.close()
    stats = dict(row) if row else {}
    if latest:
        stats['latest_weight'] = latest[0]
        stats['latest_bmi'] = latest[1]
        stats['latest_date'] = latest[2]
    if earliest:
        stats['first_weight'] = earliest[0]
        stats['weight_change'] = round(latest[0] - earliest[0], 1) if latest else 0
    return stats


# ==================== 记录操作（不变，字段名为 member_id）====================

def add_record(member_id, weight, bmi, status, plan_type):
    conn = get_connection()
    conn.execute(
        "INSERT INTO records (member_id, weight, bmi, status, plan_type, recorded_at) VALUES (?,?,?,?,?,?)",
        (member_id, weight, bmi, status, plan_type, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    conn.close()


def get_member_records(member_id):
    conn = get_connection()
    records = conn.execute(
        "SELECT id, recorded_at, weight, bmi, status, plan_type FROM records WHERE member_id=? ORDER BY recorded_at DESC",
        (member_id,)
    ).fetchall()
    conn.close()
    return records


def delete_record(record_id):
    conn = get_connection()
    conn.execute("DELETE FROM records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()


# ==================== 食物和运动库 ====================

def get_all_foods():
    conn = get_connection()
    foods = conn.execute("SELECT name, cal_per_100g, protein, fat, carb, category FROM foods").fetchall()
    conn.close()
    return foods


def get_all_exercises():
    conn = get_connection()
    exercises = conn.execute("SELECT name, met, type FROM exercises").fetchall()
    conn.close()
    return exercises


# ── 向后兼容别名（桌面端旧接口）──

def get_all_users():
    return get_all_members()


def get_user_full_info(uid):
    return get_member_full_info(uid)


def get_user_stats(uid):
    return get_member_stats(uid)


def get_user_records(uid):
    return get_member_records(uid)


def add_user(name, gender, height, age, activity, target_weight, target_date):
    return add_member(name, gender, height, age, activity, target_weight, target_date)


def update_user(mid, name, gender, height, age, activity, target_weight, target_date):
    return update_member(mid, name, gender, height, age, activity, target_weight, target_date)


def delete_user(mid):
    return delete_member(mid)
