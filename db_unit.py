import pymysql
from time_unit import get_now_time
from datetime import datetime
import json
import os
import math
from config import total_spaces, MONEY_PER_DAY

#数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "car",
    "charset": "utf8mb4"
}

#停车场总车位数
TOTAL_SPACES = total_spaces

#JSON数据存储目录和文件
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
VEHICLES_FILE = os.path.join(DATA_DIR, "vehicles.json")
INCOME_FILE = os.path.join(DATA_DIR, "income.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")

#数据库连接状态缓存
_db_available = None
_last_check_time = 0
_CHECK_INTERVAL = 30  #30秒重试一次


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def check_db_connection():
    #检查数据库是否可用
    global _db_available, _last_check_time

    now = datetime.now().timestamp()
    #如果最近检查过且可用，直接返回
    if _db_available is True and (now - _last_check_time) < _CHECK_INTERVAL:
        return True

    try:
        conn = pymysql.connect(**DB_CONFIG)
        conn.close()
        _db_available = True
        _last_check_time = now
        print("数据库连接成功")
        return True
    except Exception as e:
        _db_available = False
        _last_check_time = now
        print(f"⚠️ 数据库连接失败，使用JSON文件存储: {e}")
        return False


def get_db_conn():
    #获取数据库连接
    if not check_db_connection():
        return None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"数据库连接异常: {e}")
        return None

def load_json_file(filepath, default=None):
    #加载JSON文件
    ensure_data_dir()
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def save_json_file(filepath, data):
    #保存JSON文件
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
def init_database():
    #初始化数据库/JSON存储
    #尝试数据库初始化
    if check_db_connection():
        try:
            conn = get_db_conn()
            if conn:
                cursor = conn.cursor()
                #检查用户表是否存在
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE,
                        pwd VARCHAR(50)
                    )
                """)
                #检查车辆表是否存在
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS parkvehicle (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        plate_num VARCHAR(20),
                        enter_time DATETIME,
                        car_status INT DEFAULT 0,
                        exit_time DATETIME
                    )
                """)
                #插入默认管理员
                cursor.execute("SELECT COUNT(*) FROM user WHERE name = 'admin'")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO user (name, pwd) VALUES ('admin', '123456')")
                conn.commit()
                cursor.close()
                conn.close()
                print("数据库初始化成功")
                return True, "数据库初始化成功"
        except Exception as e:
            print(f"数据库初始化失败: {e}")

    #JSON存储初始化
    users = load_json_file(USER_FILE, {})
    if "admin" not in users:
        users["admin"] = "123456"
        save_json_file(USER_FILE, users)

    #确保其他文件存在
    load_json_file(VEHICLES_FILE, [])
    load_json_file(INCOME_FILE, {})

    print("JSON存储初始化成功")
    return True, "JSON存储初始化成功"


def verify_user(username, password):
    #验证用户登录
    #尝试数据库
    if check_db_connection():
        try:
            conn = get_db_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, pwd FROM user WHERE name = %s", (username,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result and result[1] == password:
                    return True
        except Exception as e:
            print(f"数据库查询用户失败: {e}")

    #降级到JSON
    users = load_json_file(USER_FILE, {})
    return users.get(username) == password

def load_vehicles():
    #加载车辆数据
    if check_db_connection():
        try:
            conn = get_db_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, plate_num, enter_time, car_status, exit_time 
                    FROM parkvehicle
                """)
                results = cursor.fetchall()
                cursor.close()
                conn.close()

                vehicles = []
                for row in results:
                    vehicles.append({
                        "id": row[0],
                        "plate_num": row[1],
                        "enter_time": str(row[2]) if row[2] else None,
                        "car_status": row[3],
                        "exit_time": str(row[4]) if row[4] else None
                    })
                return vehicles
        except Exception as e:
            print(f"从数据库读取车辆失败: {e}")

    #降级到JSON
    return load_json_file(VEHICLES_FILE, [])


def save_vehicles(vehicles):
    #保存车辆数据到JSON
    save_json_file(VEHICLES_FILE, vehicles)


def sync_vehicles_to_db(vehicles):
    #将车辆数据同步到数据库
    if not check_db_connection():
        return False

    try:
        conn = get_db_conn()
        if not conn:
            return False

        cursor = conn.cursor()
        #清空表
        cursor.execute("TRUNCATE TABLE parkvehicle")

        #插入数据
        for v in vehicles:
            cursor.execute("""
                INSERT INTO parkvehicle (plate_num, enter_time, car_status, exit_time)
                VALUES (%s, %s, %s, %s)
            """, (v["plate_num"], v["enter_time"], v["car_status"], v["exit_time"]))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"同步数据到数据库失败: {e}")
        return False


def get_current_parking_count():
    #获取当前在场车辆数量
    vehicles = load_vehicles()
    return sum(1 for v in vehicles if v.get("car_status") == 0)


def calculate_parking_days(enter_time, exit_time):
    #计算停车天数
    if isinstance(enter_time, str):
        enter_dt = datetime.strptime(enter_time, "%Y-%m-%d %H:%M:%S")
    else:
        enter_dt = enter_time

    if isinstance(exit_time, str):
        exit_dt = datetime.strptime(exit_time, "%Y-%m-%d %H:%M:%S")
    else:
        exit_dt = exit_time

    delta = exit_dt - enter_dt
    total_hours = delta.total_seconds() / 3600
    days = math.floor(total_hours / 24)
    return days if days > 0 else 0


def handle_plate_data(plate_num):
    #处理车牌数据（入场/离场）
    now_time = get_now_time()
    vehicles = load_vehicles()

    #查找该车牌
    existing = None
    existing_index = -1
    for i, v in enumerate(vehicles):
        if v["plate_num"] == plate_num:
            existing = v
            existing_index = i
            break

    if existing is None:
        if get_current_parking_count() >= TOTAL_SPACES:
            return False, f"⚠️ 停车场已满（{TOTAL_SPACES}/{TOTAL_SPACES}），车辆 {plate_num} 无法入场"

        new_id = max([v.get("id", 0) for v in vehicles] + [0]) + 1
        new_vehicle = {
            "id": new_id,
            "plate_num": plate_num,
            "enter_time": now_time,
            "car_status": 0,
            "exit_time": None
        }
        vehicles.append(new_vehicle)

        #尝试数据库
        if check_db_connection():
            try:
                conn = get_db_conn()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO parkvehicle (plate_num, enter_time, car_status, exit_time) VALUES (%s, %s, 0, NULL)",
                        (plate_num, now_time)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    remaining = TOTAL_SPACES - get_current_parking_count()
                    return True, f"新车辆入场，车牌 {plate_num} 已录入（剩余车位：{remaining}）"
            except Exception as e:
                print(f"数据库插入失败，降级到JSON: {e}")

        #降级到JSON
        save_vehicles(vehicles)
        remaining = TOTAL_SPACES - get_current_parking_count()
        return True, f"新车辆入场，车牌 {plate_num} 已录入（剩余车位：{remaining}）"

    else:
        #车辆已存在
        if existing["car_status"] == 0:
            #场内车辆，离场
            existing["car_status"] = 1
            existing["exit_time"] = now_time

            #计算费用
            days = calculate_parking_days(existing["enter_time"], now_time)
            amount = days * MONEY_PER_DAY

            if check_db_connection():
                try:
                    conn = get_db_conn()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE parkvehicle SET car_status=1, exit_time=%s WHERE plate_num=%s",
                            (now_time, plate_num)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

                        if amount > 0:
                            add_income(now_time[:7], amount)

                        current_count = get_current_parking_count()
                        base_msg = f"车辆 {plate_num} 离场（剩余车位：{TOTAL_SPACES - current_count}）"
                        if amount > 0:
                            return True, f"{base_msg}，停车费用 {amount} 元（已记录收入）"
                        return True, f"{base_msg}，停车不足1天免收费"
                except Exception as e:
                    print(f"数据库更新失败，降级到JSON: {e}")

            #降级到JSON
            save_vehicles(vehicles)
            if amount > 0:
                add_income(now_time[:7], amount)

            current_count = get_current_parking_count()
            base_msg = f"车辆 {plate_num} 离场（剩余车位：{TOTAL_SPACES - current_count}）"
            if amount > 0:
                return True, f"{base_msg}，停车费用 {amount} 元（已记录收入）"
            return True, f"{base_msg}，停车不足1天免收费"

        else:
            #已离场，再次入场
            if get_current_parking_count() >= TOTAL_SPACES:
                return False, f"停车场已满（{TOTAL_SPACES}/{TOTAL_SPACES}），车辆 {plate_num} 无法入场"

            #删除旧记录，创建新记录
            vehicles.pop(existing_index)
            new_id = max([v.get("id", 0) for v in vehicles] + [0]) + 1
            new_vehicle = {
                "id": new_id,
                "plate_num": plate_num,
                "enter_time": now_time,
                "car_status": 0,
                "exit_time": None
            }
            vehicles.append(new_vehicle)

            if check_db_connection():
                try:
                    conn = get_db_conn()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM parkvehicle WHERE plate_num=%s", (plate_num,))
                        cursor.execute(
                            "INSERT INTO parkvehicle (plate_num, enter_time, car_status, exit_time) VALUES (%s, %s, 0, NULL)",
                            (plate_num, now_time)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        current_count = get_current_parking_count()
                        return True, f"车辆 {plate_num} 再次入场（剩余车位：{TOTAL_SPACES - current_count}）"
                except Exception as e:
                    print(f"数据库操作失败，降级到JSON: {e}")

            #降级到JSON
            save_vehicles(vehicles)
            current_count = get_current_parking_count()
            return True, f"车辆 {plate_num} 再次入场（剩余车位：{TOTAL_SPACES - current_count}）"


def get_parking_vehicles(limit=0):
    #获取在场车辆列表
    vehicles = load_vehicles()
    parking = [v for v in vehicles if v.get("car_status") == 0]
    parking.sort(key=lambda x: x.get("enter_time", ""), reverse=True)

    if limit > 0:
        parking = parking[:limit]

    vehicle_data = []
    for v in parking:
        vehicle_data.append({
            "plate": v["plate_num"],
            "time": v["enter_time"] if v["enter_time"] else "未知"
        })

    if not vehicle_data:
        vehicle_data = [{"plate": "暂无在场车辆", "time": "--"}]

    return vehicle_data, len([v for v in vehicles if v.get("car_status") == 0])


def get_longest_parking_vehicle():
    #获取停车最久的车辆
    vehicles = load_vehicles()
    parking = [v for v in vehicles if v.get("car_status") == 0]

    if not parking:
        return None

    parking.sort(key=lambda x: x.get("enter_time", ""))
    oldest = parking[0]

    enter_time = oldest["enter_time"]
    if isinstance(enter_time, str):
        enter_dt = datetime.strptime(enter_time, "%Y-%m-%d %H:%M:%S")
    else:
        enter_dt = enter_time

    now = datetime.now()
    duration = now - enter_dt
    total_seconds = int(duration.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        duration_str = f"{days}天{hours}时{minutes}分"
    elif hours > 0:
        duration_str = f"{hours}时{minutes}分"
    else:
        duration_str = f"{minutes}分"

    return {
        "plate": oldest["plate_num"],
        "enter_time": str(enter_time),
        "duration": duration_str,
        "duration_seconds": total_seconds
    }


def del_vehicle(plate_num):
    #删除车辆记录
    vehicles = load_vehicles()
    vehicles = [v for v in vehicles if v["plate_num"] != plate_num]

    if check_db_connection():
        try:
            conn = get_db_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM parkvehicle WHERE plate_num=%s", (plate_num,))
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"数据库删除失败: {e}")

    save_vehicles(vehicles)
    return True


def update_vehicle_status(plate_num, car_status, exit_time=None):
    #更新车辆状态
    vehicles = load_vehicles()
    for v in vehicles:
        if v["plate_num"] == plate_num:
            v["car_status"] = car_status
            if exit_time:
                v["exit_time"] = exit_time
            break

    if check_db_connection():
        try:
            conn = get_db_conn()
            if conn:
                cursor = conn.cursor()
                if exit_time:
                    cursor.execute(
                        "UPDATE parkvehicle SET car_status=%s, exit_time=%s WHERE plate_num=%s",
                        (car_status, exit_time, plate_num)
                    )
                else:
                    cursor.execute(
                        "UPDATE parkvehicle SET car_status=%s WHERE plate_num=%s",
                        (car_status, plate_num)
                    )
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"数据库更新失败: {e}")

    save_vehicles(vehicles)
    return True


def query_vehicle(plate_num=None):
    #查询车辆
    vehicles = load_vehicles()
    if plate_num:
        return [v for v in vehicles if v["plate_num"] == plate_num]
    return vehicles

def load_income_data():
    #加载收入数据
    return load_json_file(INCOME_FILE, {})


def save_income_data(data):
    #保存收入数据
    save_json_file(INCOME_FILE, data)


def add_income(month, amount):
    #添加收入
    data = load_income_data()
    data[month] = data.get(month, 0) + amount
    save_income_data(data)
    return data[month]


def get_income_summary(start_month=None, end_month=None):
    #获取收入摘要
    data = load_income_data()
    if not data:
        return {}

    if start_month and end_month:
        filtered = {}
        for month, amount in data.items():
            if start_month <= month <= end_month:
                filtered[month] = amount
        return filtered
    return data


def get_income_month_range():
    #获取收入数据的月份范围
    data = load_income_data()
    if not data:
        now = datetime.now()
        return now.strftime("%Y-%m"), now.strftime("%Y-%m")

    months = sorted(data.keys())
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    if current_month not in data:
        data[current_month] = 0
        save_income_data(data)

    return months[0], current_month


def get_all_months_between(start_month, end_month):
    #获取两个月份之间的所有月份
    start_year, start_mon = map(int, start_month.split("-"))
    end_year, end_mon = map(int, end_month.split("-"))

    months = []
    year, mon = start_year, start_mon
    while (year < end_year) or (year == end_year and mon <= end_mon):
        months.append(f"{year:04d}-{mon:02d}")
        mon += 1
        if mon > 12:
            mon = 1
            year += 1
    return months


def record_income_on_exit(plate_num, exit_time):
    #离场时记录收入
    vehicles = load_vehicles()
    for v in vehicles:
        if v["plate_num"] == plate_num and v["car_status"] == 1:
            days = calculate_parking_days(v["enter_time"], exit_time)
            amount = days * MONEY_PER_DAY
            if amount > 0:
                month = exit_time[:7]
                add_income(month, amount)
                return True, f"收入 {amount} 元已记录", amount
            return True, "停车不足1天，不收费", 0
    return False, "未找到该车辆", 0


if __name__ == "__main__":
    #测试
    print("=" * 50)
    print("测试数据库/JSON存储适配")
    print("=" * 50)

    ok, msg = init_database()
    print(f"初始化: {ok}, {msg}")

    #测试车辆处理
    print("\n测试车辆处理:")
    ok, msg = handle_plate_data("湘A12345")
    print(f"结果: {ok}, {msg}")

    #查看在场车辆
    vehicles, count = get_parking_vehicles()
    print(f"\n在场车辆 ({count}辆):")
    for v in vehicles:
        print(f"  {v['plate']} - {v['time']}")

    #查看收入
    income = load_income_data()
    print(f"\n收入数据: {income}")