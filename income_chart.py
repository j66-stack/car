import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from db_unit import get_income_summary, get_all_months_between, load_income_data
import tkinter as tk
from tkinter import ttk, messagebox

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


def show_income_chart(start_month=None, end_month=None):
    #显示收入统计折线图
    data = get_income_summary()

    if not data:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "暂无收入数据", ha='center', va='center', fontsize=20, color='gray')
        ax.set_title("停车场月度收入统计", fontsize=16)
        plt.tight_layout()
        plt.show()
        return

    #确定月份范围
    all_months = sorted(data.keys())
    if start_month is None or end_month is None:
        start_month = all_months[0]
        end_month = datetime.now().strftime("%Y-%m")

    current = datetime.now().strftime("%Y-%m")
    if end_month > current:
        end_month = current

    months = get_all_months_between(start_month, end_month)
    values = [data.get(month, 0) for month in months]

    if all(v == 0 for v in values):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"{start_month} 至 {end_month} 期间暂无收入", ha='center', va='center', fontsize=20, color='gray')
        ax.set_title("停车场月度收入统计", fontsize=16)
        plt.tight_layout()
        plt.show()
        return

    #绘制折线图
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(months, values, marker='o', linewidth=2, markersize=6, color='#1976D2')
    ax.fill_between(months, values, alpha=0.2, color='#1976D2')

    for i, (month, val) in enumerate(zip(months, values)):
        if val > 0:
            ax.annotate(f'{val:.0f}元', (month, val),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', fontsize=9)

    ax.set_title(f"停车场月度收入统计（{start_month} ~ {end_month}）", fontsize=16, fontweight='bold')
    ax.set_xlabel("月份", fontsize=12)
    ax.set_ylabel("收入（元）", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, alpha=0.3, linestyle='--')

    if max(values) > 0:
        ax.set_ylim(bottom=0, top=max(values) * 1.2)

    plt.tight_layout()
    plt.show()


def show_income_data_table(start_month=None, end_month=None):
    data = get_income_summary()

    if not data:
        messagebox.showinfo("提示", "暂无收入数据")
        return

    all_months = sorted(data.keys())
    if start_month is None or end_month is None:
        start_month = all_months[0]
        end_month = datetime.now().strftime("%Y-%m")

    current = datetime.now().strftime("%Y-%m")
    if end_month > current:
        end_month = current

    months = get_all_months_between(start_month, end_month)

    #构建表格文本
    total_income = 0
    lines = []
    lines.append("=" * 50)
    lines.append(f"{'月份':<15} {'收入（元）':<15}")
    lines.append("=" * 50)

    for month in months:
        amount = data.get(month, 0)
        total_income += amount
        lines.append(f"{month:<15} {amount:<15.2f}")

    lines.append("=" * 50)
    lines.append(f"{'合计':<15} {total_income:<15.2f}")
    lines.append("=" * 50)

    #创建显示窗口
    win = tk.Toplevel()
    win.title("收入数据明细")
    win.geometry("400x450")
    win.resizable(False, False)

    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width - 400) // 2
    y = (screen_height - 450) // 2
    win.geometry(f"400x450+{x}+{y}")

    tk.Label(win, text="收入数据明细", font=("微软雅黑", 14, "bold")).pack(pady=10)

    #使用 Text 组件显示表格
    text_widget = tk.Text(win, font=("Courier New", 11), bg="#F5F7FA", wrap=tk.NONE)
    text_widget.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

    #添加滚动条
    scrollbar = tk.Scrollbar(text_widget)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=text_widget.yview)

    #插入文本
    for line in lines:
        text_widget.insert(tk.END, line + "\n")

    text_widget.config(state=tk.DISABLED)

    #关闭按钮
    tk.Button(win, text="关闭", command=win.destroy,
              width=12, bg="#1976D2", fg="white", font=("微软雅黑", 10)).pack(pady=10)


def show_income_chart_with_selection():
    data = load_income_data()
    all_months = sorted(data.keys()) if data else []

    root = tk.Tk()
    root.title("收入统计 - 选择时间范围")
    root.geometry("450x400")
    root.resizable(False, False)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 450) // 2
    y = (screen_height - 400) // 2
    root.geometry(f"450x400+{x}+{y}")

    main_frame = tk.Frame(root, padx=30, pady=25)
    main_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(main_frame, text="📈 收入统计", font=("微软雅黑", 18, "bold")).pack(pady=(0, 15))

    #快捷选择
    tk.Label(main_frame, text="快捷选择：", font=("微软雅黑", 11)).pack(anchor=tk.W)

    btn_frame = tk.Frame(main_frame)
    btn_frame.pack(pady=5, fill=tk.X)

    def select_all():
        if all_months:
            start = all_months[0]
            end = datetime.now().strftime("%Y-%m")
            root.destroy()
            show_income_chart(start, end)
        else:
            messagebox.showinfo("提示", "暂无收入数据")

    def select_year():
        now = datetime.now()
        end = now.strftime("%Y-%m")
        start_year = now.year - 1
        start_month = f"{start_year:04d}-{now.month:02d}"
        root.destroy()
        show_income_chart(start_month, end)

    tk.Button(btn_frame, text="全部数据", command=select_all, width=12,
              bg="#1976D2", fg="white", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="近12个月", command=select_year, width=12,
              bg="#388E3C", fg="white", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)

    #自定义范围
    tk.Label(main_frame, text="\n自定义范围：", font=("微软雅黑", 11)).pack(anchor=tk.W, pady=(15, 5))

    range_frame = tk.Frame(main_frame)
    range_frame.pack(fill=tk.X)

    tk.Label(range_frame, text="从").pack(side=tk.LEFT)
    start_var = tk.StringVar()
    start_combo = ttk.Combobox(range_frame, textvariable=start_var, values=all_months, width=10, state="readonly")
    start_combo.pack(side=tk.LEFT, padx=5)

    if all_months:
        start_combo.set(all_months[0])

    tk.Label(range_frame, text="至").pack(side=tk.LEFT, padx=5)

    end_var = tk.StringVar()
    end_combo = ttk.Combobox(range_frame, textvariable=end_var, values=all_months, width=10, state="readonly")
    end_combo.pack(side=tk.LEFT, padx=5)

    current_month = datetime.now().strftime("%Y-%m")
    if all_months:
        end_combo.set(current_month if current_month in all_months else all_months[-1])

    #按钮区域
    btn_action_frame = tk.Frame(main_frame)
    btn_action_frame.pack(pady=20, anchor=tk.W)

    def show_chart():
        start = start_var.get()
        end = end_var.get()
        if not start or not end:
            messagebox.showwarning("提示", "请选择起始和结束月份")
            return
        if start > end:
            messagebox.showwarning("提示", "起始月份不能晚于结束月份")
            return
        root.destroy()
        show_income_chart(start, end)

    def show_table():
        start = start_var.get()
        end = end_var.get()
        if not start or not end:
            messagebox.showwarning("提示", "请选择起始和结束月份")
            return
        if start > end:
            messagebox.showwarning("提示", "起始月份不能晚于结束月份")
            return
        show_income_data_table(start, end)

    tk.Button(btn_action_frame, text="显示图表", command=show_chart,
              width=12, bg="#1976D2", fg="white", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)

    tk.Button(btn_action_frame, text="显示数据", command=show_table,  #新增按钮
              width=12, bg="#FF6F00", fg="white", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)

    root.mainloop()


if __name__ == "__main__":
    show_income_chart_with_selection()