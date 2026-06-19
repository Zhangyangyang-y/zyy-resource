import random
from database import get_all_foods, get_all_exercises

def calc_bmi(weight, height_cm):
    height_m = height_cm / 100
    return round(weight / (height_m ** 2), 1)

def get_bmi_status(bmi):
    if bmi < 18.5:
        return "偏瘦"
    elif bmi < 24:
        return "正常"
    elif bmi < 28:
        return "偏胖"
    else:
        return "肥胖"

def calc_bmr(weight, height, age, gender):
    if gender == '男':
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161

def calc_tdee(bmr, activity='中等'):
    factors = {'久坐': 1.2, '轻度': 1.375, '中等': 1.55, '活跃': 1.725, '极活跃': 1.9}
    return bmr * factors.get(activity, 1.55)

def estimate_body_fat(bmi, age, gender):
    """Deurenberg 公式估算体脂率"""
    gender_val = 1 if gender == '男' else 0
    bf = round(1.20 * bmi + 0.23 * age - 10.8 * gender_val - 5.4, 1)
    # 参考范围
    if gender == '男':
        if bf < 10:
            status = "偏低"
        elif bf <= 20:
            status = "标准"
        elif bf <= 25:
            status = "偏高"
        else:
            status = "过高"
    else:
        if bf < 18:
            status = "偏低"
        elif bf <= 28:
            status = "标准"
        elif bf <= 33:
            status = "偏高"
        else:
            status = "过高"
    return bf, status


# ===== 新增：年龄分档 =====
def get_age_group(age):
    if age < 18:
        return '少年'
    elif age < 35:
        return '青年'
    elif age < 55:
        return '中年'
    else:
        return '老年'

def get_age_adjusted_tdee(bmr, age, activity):
    """ 不同年龄段基础代谢微调 """
    if age < 18:
        bmr *= 1.1   # 生长发育额外消耗
    elif age >= 55:
        bmr *= 0.95  # 基础代谢下降
    return calc_tdee(bmr, activity)

# ===== 修改：饮食计划支持年龄参数 =====
def generate_food_plan(target_cal, age=None):
    """
    根据目标热量生成三餐，age 参数预留，用于未来调整营养素比例。
    当前版本仅传递年龄信息，实际配餐可在此基础上修改。
    """
    all_foods = get_all_foods()
    categories = {}
    for f in all_foods:
        cat = f['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    plan = []
    meal_names = ['早餐', '午餐', '晚餐']
    meal_cals = [target_cal * 0.3, target_cal * 0.4, target_cal * 0.3]
    total_protein = total_fat = total_carb = total_cal = 0

    # 早餐适合的主食（燕麦、馒头、红薯，不要米饭）
    breakfast_staples = [f for f in categories.get('主食', []) if f['name'] in ('燕麦', '馒头', '红薯', '面条')]

    for i, meal_cal in enumerate(meal_cals):
        remaining = meal_cal
        is_breakfast = (i == 0)

        # 主食：早餐限定种类，午晚餐正常
        if is_breakfast and breakfast_staples:
            staple = random.choice(breakfast_staples)
        else:
            staple = random.choice(categories.get('主食', [{'name':'米饭','cal_per_100g':116,'protein':2.6,'fat':0.3,'carb':25.9}]))
        staple_g = random.randint(80, 150) if is_breakfast else random.randint(100, 200)
        staple_cal = staple['cal_per_100g'] * staple_g / 100
        plan.append((meal_names[i], staple['name'], f"{staple_g}g", round(staple_cal)))
        remaining -= staple_cal
        total_protein += staple['protein'] * staple_g / 100
        total_fat += staple['fat'] * staple_g / 100
        total_carb += staple['carb'] * staple_g / 100

        # 蛋白质：早餐偏乳制品/鸡蛋，午晚餐正常
        if is_breakfast:
            breakfast_protein = categories.get('乳制品', []) + [f for f in categories.get('肉类', []) if f['name'] in ('鸡蛋',)]
            if not breakfast_protein:
                breakfast_protein = categories.get('肉类', []) + categories.get('豆制品', [])
            protein_source = random.choice(breakfast_protein)
        else:
            protein_source = random.choice(categories.get('肉类', []) + categories.get('豆制品', []) + categories.get('乳制品', []))
        prot_g = random.randint(60, 120) if is_breakfast else random.randint(80, 150)
        prot_cal = protein_source['cal_per_100g'] * prot_g / 100
        plan.append((meal_names[i], protein_source['name'], f"{prot_g}g", round(prot_cal)))
        remaining -= prot_cal
        total_protein += protein_source['protein'] * prot_g / 100
        total_fat += protein_source['fat'] * prot_g / 100
        total_carb += protein_source['carb'] * prot_g / 100

        # 蔬菜：早餐跳过（早上一般不炒菜），午晚餐正常
        if not is_breakfast:
            veg = random.choice(categories.get('蔬菜', [{'name':'西兰花','cal_per_100g':36,'protein':4.1,'fat':0.6,'carb':4.3}]))
            veg_g = random.randint(100, 200)
            veg_cal = veg['cal_per_100g'] * veg_g / 100
            plan.append((meal_names[i], veg['name'], f"{veg_g}g", round(veg_cal)))
            remaining -= veg_cal
            total_protein += veg['protein'] * veg_g / 100
            total_fat += veg['fat'] * veg_g / 100
            total_carb += veg['carb'] * veg_g / 100
        else:
            # 早餐加一份水果
            fruit = random.choice(categories.get('水果', [{'name':'苹果','cal_per_100g':54,'protein':0.2,'fat':0.2,'carb':13.5}]))
            fruit_g = random.randint(80, 150)
            fruit_cal = fruit['cal_per_100g'] * fruit_g / 100
            plan.append((meal_names[i], fruit['name'], f"{fruit_g}g", round(fruit_cal)))
            remaining -= fruit_cal
            total_protein += fruit['protein'] * fruit_g / 100
            total_fat += fruit['fat'] * fruit_g / 100
            total_carb += fruit['carb'] * fruit_g / 100

        if remaining > 50 and not is_breakfast:
            snack = random.choice(categories.get('水果', []) + categories.get('零食', []))
            snack_g = min(int(remaining / (snack['cal_per_100g']/100)), 100)
            snack_cal = snack['cal_per_100g'] * snack_g / 100
            plan.append((meal_names[i], snack['name'], f"{snack_g}g", round(snack_cal)))
            total_protein += snack['protein'] * snack_g / 100
            total_fat += snack['fat'] * snack_g / 100
            total_carb += snack['carb'] * snack_g / 100

    total_cal = sum(item[3] for item in plan)
    nutrition = (round(total_protein, 1), round(total_fat, 1), round(total_carb, 1), round(total_cal))
    return plan, nutrition

# ===== 修改：运动计划支持年龄参数 =====
def generate_exercise_plan(status, plan_type, weight, age=None):
    """
    根据体态和年龄生成运动计划。
    年龄影响运动强度、类型偏向。
    """
    exercises = get_all_exercises()
    age_group = get_age_group(age) if age else '青年'
    plan = []

    # 根据年龄选择偏好
    if age_group == '少年':
        # 趣味性、跳跃类、有氧为主，避免大重量
        prefer_cardio = True
        avoid_heavy = True
    elif age_group == '中年':
        # 增加核心和柔韧，适当力量
        prefer_cardio = False
        avoid_heavy = False
        flex_needed = True
    elif age_group == '老年':
        # 低强度有氧 + 柔韧 + 轻量力量
        prefer_cardio = True
        avoid_heavy = True
        flex_needed = True
    else:  # 青年
        prefer_cardio = False
        avoid_heavy = False
        flex_needed = False

    if status == '偏瘦':
        strength = [e for e in exercises if e['type'] == '力量']
        # 少年/老年避免大重量
        if avoid_heavy:
            strength = [e for e in strength if '深蹲' not in e['name'] and '硬拉' not in e['name']]
        for _ in range(4):
            ex = random.choice(strength)
            duration = random.randint(20, 40)
            cal = weight * ex['met'] * duration / 60
            plan.append((ex['name'], f"{duration}分钟", round(cal)))
        if age_group == '少年':
            # 增加一个趣味运动
            plan.append(('跳绳', "15分钟", round(weight * 10 * 0.25)))
    elif status in ('偏胖', '肥胖') or plan_type == '减脂':
        cardio = [e for e in exercises if e['type'] == '有氧']
        strength = [e for e in exercises if e['type'] == '力量']
        if avoid_heavy:
            strength = [e for e in strength if '深蹲' not in e['name'] and '硬拉' not in e['name']]
        for _ in range(3):
            ex = random.choice(cardio)
            duration = random.randint(30, 60)
            cal = weight * ex['met'] * duration / 60
            plan.append((ex['name'], f"{duration}分钟", round(cal)))
        ex = random.choice(strength)
        duration = random.randint(20, 30)
        cal = weight * ex['met'] * duration / 60
        plan.append((ex['name'], f"{duration}分钟", round(cal)))
        if flex_needed:
            flex = [e for e in exercises if e['type'] == '柔韧']
            if flex:
                ex = random.choice(flex)
                duration = random.randint(15, 30)
                cal = weight * ex['met'] * duration / 60
                plan.append((ex['name'], f"{duration}分钟", round(cal)))
    else:  # 塑形
        strength = [e for e in exercises if e['type'] == '力量']
        if avoid_heavy:
            strength = [e for e in strength if '深蹲' not in e['name'] and '硬拉' not in e['name']]
        for _ in range(4):
            ex = random.choice(strength)
            duration = random.randint(30, 50)
            cal = weight * ex['met'] * duration / 60
            plan.append((ex['name'], f"{duration}分钟", round(cal)))
        flex = [e for e in exercises if e['type'] == '柔韧']
        if flex and (flex_needed or age_group == '中年'):
            ex = random.choice(flex)
            duration = random.randint(15, 30)
            cal = weight * ex['met'] * duration / 60
            plan.append((ex['name'], f"{duration}分钟", round(cal)))
    return plan