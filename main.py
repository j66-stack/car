import sys
import tkinter as tk
from db_unit import init_database
from login import LoginApp
import traceback


def init_system():
    #初始化系统（数据库或JSON存储）
    print("=" * 50)
    print("正在初始化停车场收费系统...")
    print("=" * 50)

    success, msg = init_database()
    if not success:
        print(f"{msg}")
        print("系统将使用JSON文件存储模式运行")
        print(f"数据将保存在 data/ 目录下")
    else:
        print(f"{msg}")
        print("默认管理员账号：admin / 123456")

    #显示存储模式
    from db_unit import check_db_connection
    if check_db_connection():
        print("存储模式：MySQL数据库")
    else:
        print("存储模式：JSON文件")

    print("\n系统初始化完成！")
    print("=" * 50)
    return True


def launch_login():
    #启动登录界面
    try:
        root = tk.Tk()
        app = LoginApp(root)
        root.mainloop()
    except Exception as e:
        print(f"启动登录界面失败：{e}")
        input("按回车键退出...")
        sys.exit(1)


def main():
    try:
        if not init_system():
            return
        print("\n启动登录界面...")
        launch_login()
    except Exception as e:
        with open("error.log", "w", encoding="utf-8") as f:
            f.write(f"main.py 崩溃: {str(e)}\n")
            traceback.print_exc(file=f)
        print(f"程序崩溃: {e}")
        print("错误详情已写入 error.log")
        input("按回车键退出...")


if __name__ == "__main__":
    main()