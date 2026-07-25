from datetime import datetime

def get_now_time():
    #获取时间
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")