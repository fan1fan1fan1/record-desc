import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date
import json
import os
import sys
import winreg

CONFIG_FILE = "countdown_config.json"
REG_NAME = "DateCountdownTool"

# 窗口宽,窗口高,左右小字字号,中间标题字号,天数数字字号,单位字号
SIZES = [
    (360, 190, 12, 16, 38, 13),  # 小
    (460, 260, 16, 20, 56, 18),  # 中
    (580, 330, 22, 26, 76, 24),  # 大
    (720, 410, 28, 32, 96, 30),  # 超大
]
SIZE_NAMES = ["小", "中", "大", "超大"]
COLOR_LIST = [
    ("黑色", "black"),
    ("白色", "white"),
    ("红色", "#ff4444"),
    ("橙色", "#ffaa00"),
    ("黄色", "#ffff00"),
    ("绿色", "#00ff66"),
    ("青色", "#00ffff"),
    ("蓝色", "#4488ff"),
    ("紫色", "#cc66ff")
]

def is_auto_start():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

def set_auto_start(enable: bool):
    if getattr(sys, 'frozen', False):
        app_path = f'"{sys.executable}"'
    else:
        app_path = f'"{sys.executable}" "{os.path.realpath(__file__)}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
        if enable:
            winreg.SetValueEx(key, REG_NAME,0, winreg.REG_SZ, app_path)
        else:
            winreg.DeleteValue(key, REG_NAME)
        winreg.CloseKey(key)
        messagebox.showinfo("提示", "已开启开机自启" if enable else "已关闭开机自启")
    except Exception as e:
        messagebox.showerror("错误", f"操作失败：{str(e)}")

def toggle_autostart():
    set_auto_start(not is_auto_start())

def get_config_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, CONFIG_FILE)

def load_config():
    path = get_config_path()
    default = {"title": "", "end_date": "", "size":1, "text_color":"white"}
    if os.path.exists(path):
        try:
            with open(path,'r',encoding='utf-8') as f:
                cfg = json.load(f)
                default.update(cfg)
        except Exception:
            pass
    return default

def save_config(cfg):
    path = get_config_path()
    try:
        with open(path,'w',encoding='utf-8') as f:
            json.dump(cfg,f,ensure_ascii=False,indent=2)
    except Exception:
        pass

class CountdownApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self._drag_data = None
        self.size_idx = self.cfg.get("size",1)
        self.text_color = self.cfg.get("text_color","white")
        if not (0 <= self.size_idx < len(SIZES)):
            self.size_idx =1
        self.setup_window()
        self.setup_ui()
        self.apply_size()
        self.apply_text_color()
        self.root.bind("<Button-3>", self.show_menu)
        if not self.cfg.get("title") or not self.cfg.get("end_date"):
            self.root.after(100,lambda:self.open_editor(first_run=True))
        else:
            self.update_display()
        self.refresh_tick()

    def setup_window(self):
        w,h = SIZES[self.size_idx][0], SIZES[self.size_idx][1]
        self.root.geometry(f"{w}x{h}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost",True)
        self.root.configure(bg="#000001")
        self.root.wm_attributes("-transparentcolor","#000001")

    def setup_ui(self):
        # 顶部一行容器：距离(小字) + xxx(大字) + 还有(小字)
        top_container = tk.Frame(self.root, bg="#000001")
        top_container.pack(pady=(25,15))

        self.prefix_var = tk.StringVar(value="距离")
        self.title_var = tk.StringVar()
        self.suffix_var = tk.StringVar(value="还有")

        self.prefix_label = tk.Label(top_container, textvariable=self.prefix_var, bg="#000001", fg="white")
        self.prefix_label.pack(side=tk.LEFT)

        self.name_label = tk.Label(top_container, textvariable=self.title_var, bg="#000001", fg="white")
        self.name_label.pack(side=tk.LEFT, padx=(4,4))

        self.suffix_label = tk.Label(top_container, textvariable=self.suffix_var, bg="#000001", fg="white")
        self.suffix_label.pack(side=tk.LEFT)

        # 天数区域：【数字+天】整体居中
        days_frame = tk.Frame(self.root, bg="#000001")
        days_frame.pack(fill=tk.X)
        days_inner = tk.Frame(days_frame, bg="#000001")
        days_inner.pack(anchor="center")

        self.days_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="天")

        self.days_label = tk.Label(days_inner, textvariable=self.days_var, bg="#000001", fg="white", font=("Microsoft YaHei",56,"bold"))
        self.days_label.pack(side=tk.LEFT)
        self.unit_label = tk.Label(days_inner, textvariable=self.unit_var, bg="#000001", fg="white")
        self.unit_label.pack(side=tk.LEFT, padx=(6,0))

        self.root.bind("<Button-1>",self.on_press)
        self.root.bind("<B1-Motion>",self.on_drag)

    def apply_size(self):
        w,h,small_font,big_name_font,day_font,unit_font = SIZES[self.size_idx]
        cx,cy = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{w}x{h}+{cx}+{cy}")
        # 左右小字，中间名字更大
        self.prefix_label.config(font=("Microsoft YaHei", small_font))
        self.suffix_label.config(font=("Microsoft YaHei", small_font))
        self.name_label.config(font=("Microsoft YaHei", big_name_font))
        self.days_label.config(font=("Microsoft YaHei", day_font, "bold"))
        self.unit_label.config(font=("Microsoft YaHei", unit_font))

    def apply_text_color(self):
        c = self.text_color
        self.prefix_label.config(fg=c)
        self.name_label.config(fg=c)
        self.suffix_label.config(fg=c)
        self.days_label.config(fg=c)
        self.unit_label.config(fg=c)

    def set_size(self, idx):
        self.size_idx = idx
        self.cfg["size"] = idx
        save_config(self.cfg)
        self.apply_size()

    def set_text_color_cb(self, color_code):
        self.text_color = color_code
        self.cfg["text_color"] = color_code
        save_config(self.cfg)
        self.apply_text_color()

    def show_menu(self,event):
        menu = tk.Menu(self.root, tearoff=0)
        size_sub = tk.Menu(menu, tearoff=0)
        color_sub = tk.Menu(menu, tearoff=0)

        menu.add_command(label="编辑倒计时", command=lambda:self.open_editor(False))

        for i,name in enumerate(SIZE_NAMES):
            mark = "✓ " if i==self.size_idx else "    "
            size_sub.add_command(label=f"{mark}{name}", command=lambda i=i:self.set_size(i))
        menu.add_cascade(label=f"字号({SIZE_NAMES[self.size_idx]})", menu=size_sub)

        for name,c in COLOR_LIST:
            tick = "✓ " if c==self.text_color else "    "
            color_sub.add_command(label=f"{tick}{name}", command=lambda col=c:self.set_text_color_cb(col))
        menu.add_cascade(label="文字颜色", menu=color_sub)

        menu.add_separator()
        tick_auto = "☑ " if is_auto_start() else "☐ "
        menu.add_command(label=tick_auto+"开机自启", command=toggle_autostart)
        menu.add_separator()
        menu.add_command(label="退出", command=self.root.quit)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def update_display(self):
        title = self.cfg.get("title","").strip()
        self.title_var.set(title)
        end_str = self.cfg.get("end_date","")
        try:
            target_day = datetime.strptime(end_str,"%Y-%m-%d").date()
            today = date.today()
            diff = (target_day - today).days
            self.days_var.set(str(diff))
        except Exception:
            self.days_var.set("--")

    def refresh_tick(self):
        self.update_display()
        self.root.after(60000, self.refresh_tick)

    def on_press(self,event):
        self._drag_data = (event.x_root, event.y_root)

    def on_drag(self,event):
        if self._drag_data is None:
            return
        dx = event.x_root - self._drag_data[0]
        dy = event.y_root - self._drag_data[1]
        nx = self.root.winfo_x() + dx
        ny = self.root.winfo_y() + dy
        self.root.geometry(f"+{nx}+{ny}")
        self._drag_data = (event.x_root, event.y_root)

    def open_editor(self, first_run):
        win = tk.Toplevel(self.root)
        win.title("编辑倒计时")
        win.geometry("440x220")
        win.configure(bg="#f0f0f0")
        tk.Label(win,text="目标名称",bg="#f0f0f0").pack(pady=(12,2))
        e_name = tk.Entry(win,width=35)
        e_name.insert(0,self.cfg.get("title",""))
        e_name.pack()
        tk.Label(win,text="目标日期 YYYY‑MM‑DD",bg="#f0f0f0").pack(pady=(8,2))
        e_date = tk.Entry(win,width=35)
        e_date.insert(0,self.cfg.get("end_date",""))
        e_date.pack()

        def save_func():
            t = e_name.get().strip()
            d = e_date.get().strip()
            try:
                datetime.strptime(d,"%Y-%m-%d")
            except ValueError:
                messagebox.showerror("错误", "日期格式必须 YYYY-MM-DD")
                return
            self.cfg["title"] = t
            self.cfg["end_date"] = d
            save_config(self.cfg)
            self.update_display()
            win.destroy()
        tk.Button(win,text="保存",command=save_func).pack(pady=15)
        if first_run:
            win.protocol("WM_DELETE_WINDOW", lambda:(win.destroy(), self.root.destroy()))

if __name__ == "__main__":
    root = tk.Tk()
    app = CountdownApp(root)
    root.mainloop()
