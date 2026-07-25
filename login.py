import tkinter as tk
from tkinter import messagebox
import sys
import os
from db_unit import verify_user


class LoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("停车场收费系统 - 用户登录")
        self.root.geometry("420x340")
        self.root.resizable(False, False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 420) // 2
        y = (screen_height - 340) // 2
        self.root.geometry(f"420x340+{x}+{y}")

        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'car',
            'charset': 'utf8mb4'
        }

        self.color_primary = "#1976D2"
        self.color_success = "#388E3C"
        self.color_warn = "#D32F2F"
        self.color_bg = "#F5F7FA"
        self.root.configure(bg=self.color_bg)
        self.create_login_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.camera_process = None

    def create_login_widgets(self):
        main_card = tk.Frame(self.root, bg="white", bd=0)
        main_card.pack(pady=25, padx=30, fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_card,
            text="停车场收费系统",
            font=("微软雅黑", 19, "bold"),
            fg=self.color_primary,
            bg="white"
        )
        title_label.pack(pady=(20, 4))

        sub_title = tk.Label(
            main_card,
            text="账号登录",
            font=("微软雅黑", 10),
            fg="#757575",
            bg="white"
        )
        sub_title.pack(pady=(0, 25))

        frame_user = tk.Frame(main_card, bg="white")
        frame_user.pack(pady=6)
        tk.Label(
            frame_user,
            text="用户名",
            font=("微软雅黑", 11),
            width=7,
            anchor="e",
            bg="white"
        ).pack(side=tk.LEFT, padx=(0, 12))
        self.username_entry = tk.Entry(
            frame_user,
            font=("微软雅黑", 11),
            width=22,
            bd=1,
            relief="solid",
            highlightcolor=self.color_primary,
            highlightthickness=1
        )
        self.username_entry.pack(side=tk.LEFT)
        self.username_entry.focus()

        frame_pwd = tk.Frame(main_card, bg="white")
        frame_pwd.pack(pady=12)
        tk.Label(
            frame_pwd,
            text="密　码",
            font=("微软雅黑", 11),
            width=7,
            anchor="e",
            bg="white"
        ).pack(side=tk.LEFT, padx=(0, 12))
        self.password_entry = tk.Entry(
            frame_pwd,
            font=("微软雅黑", 11),
            width=22,
            show="*",
            bd=1,
            relief="solid",
            highlightcolor=self.color_primary,
            highlightthickness=1
        )
        self.password_entry.pack(side=tk.LEFT)
        self.username_entry.bind("<Return>", lambda e: self.login())
        self.password_entry.bind("<Return>", lambda e: self.login())

        frame_btn = tk.Frame(main_card, bg="white")
        frame_btn.pack(pady=28)

        btn_login = tk.Button(
            frame_btn,
            text="登 录",
            font=("微软雅黑", 12, "bold"),
            width=10,
            height=1,
            bg=self.color_primary,
            fg="white",
            bd=0,
            relief="flat",
            command=self.login
        )
        btn_login.pack(side=tk.LEFT, padx=8)

        btn_reset = tk.Button(
            frame_btn,
            text="重 置",
            font=("微软雅黑", 12),
            width=10,
            height=1,
            bg="#EEEEEE",
            fg="#333333",
            bd=0,
            relief="flat",
            command=self.reset_input
        )
        btn_reset.pack(side=tk.LEFT, padx=8)

    def reset_input(self):
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.username_entry.focus()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("输入提示", "用户名和密码不能为空！")
            return

        #使用verify_user函数验证
        if verify_user(username, password):
            self.show_success_window_and_launch_camera()
        else:
            messagebox.showerror("登录失败", "用户名或密码错误！")

    def show_success_window_and_launch_camera(self):
        success_window = tk.Toplevel(self.root)
        success_window.title("登录成功")
        success_window.geometry("360x280")
        success_window.resizable(False, False)

        sw = success_window.winfo_screenwidth()
        sh = success_window.winfo_screenheight()
        sx = (sw - 360) // 2
        sy = (sh - 280) // 2
        success_window.geometry(f"360x280+{sx}+{sy}")
        success_window.configure(bg="white")
        success_window.transient(self.root)
        success_window.grab_set()

        tk.Label(
            success_window,
            text="✓",
            font=("微软雅黑", 65),
            fg=self.color_success,
            bg="white"
        ).pack(pady=(22, 8))

        tk.Label(
            success_window,
            text="登录成功！",
            font=("微软雅黑", 16, "bold"),
            fg="#333",
            bg="white"
        ).pack(pady=4)

        tk.Label(
            success_window,
            text="正在启动摄像头应用...",
            font=("微软雅黑", 10),
            fg="#666",
            bg="white"
        ).pack(pady=12)

        self.password_entry.delete(0, tk.END)

        #启动摄像头应用
        self.launch_camera_app()

        self.root.withdraw()

        def enter_system():
            success_window.destroy()
            self.root.destroy()

        tk.Button(
            success_window,
            text="进入系统",
            command=enter_system,
            width=12,
            bg=self.color_success,
            fg="white",
            font=("微软雅黑", 11)
        ).pack(pady=10)

    def launch_camera_app(self):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            camera_script = os.path.join(base_dir, "camera_gui.py")

            if os.path.exists(camera_script):
                import subprocess
                flag = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                self.camera_process = subprocess.Popen(
                    [sys.executable, camera_script],
                    cwd=base_dir,
                    env=os.environ.copy(),
                    creationflags=flag,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                from camera_gui import run_camera_app
                import threading
                t = threading.Thread(target=run_camera_app, daemon=True)
                t.start()

        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动摄像头应用：{str(e)}")

    def on_closing(self):
        if self.camera_process and self.camera_process.poll() is None:
            self.camera_process.terminate()
            self.camera_process = None
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()