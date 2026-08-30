import json, os, sys, time, threading, tkinter as tk
from tkinter import messagebox
import ctypes
from ctypes import wintypes

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")
user32 = ctypes.windll.user32

VK_F10 = 0x79
VK_F11 = 0x7A
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def get_cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y

def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def double_click_at(x, y):
    click_at(x, y)
    time.sleep(0.08)
    click_at(x, y)

def active_window_title():
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"f10": None, "f11": None, "window_keyword": "Контур"}

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

cfg = load_config()
running = True

def market_active():
    keyword = cfg.get("window_keyword", "Контур").strip().lower()
    return not keyword or keyword in active_window_title().lower()

def hotkey_loop():
    last_press = {"f10": 0.0, "f11": 0.0}
    was_down = {"f10": False, "f11": False}
    double_window = 0.35

    while running:
        if market_active():
            now = time.monotonic()
            for name, vk, key in (
                ("f10", VK_F10, "f10"),
                ("f11", VK_F11, "f11"),
            ):
                down = bool(user32.GetAsyncKeyState(vk) & 0x8000)

                if down and not was_down[name]:
                    point = cfg.get(key)
                    if point:
                        if now - last_press[name] <= double_window:
                            double_click_at(*point)
                            last_press[name] = 0.0
                        else:
                            click_at(*point)
                            last_press[name] = now

                was_down[name] = down
        else:
            was_down["f10"] = False
            was_down["f11"] = False

        time.sleep(0.01)

def train(label, key):
    messagebox.showinfo(
        "Настройка",
        f"Перейди в Контур.Маркет.\n\n"
        f"Наведи мышь на кнопку «{label}» и нажми ЛКМ.\n\n"
        "Координаты сохранятся автоматически."
    )

    def worker():
        was_down = False
        while True:
            down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            if down and not was_down:
                pos = get_cursor_pos()
                cfg[key] = [pos[0], pos[1]]
                save_config()
                root.after(0, refresh)
                root.after(
                    0,
                    lambda p=pos: messagebox.showinfo(
                        "Готово",
                        f"{label}\n\nСохранено: {p[0]}, {p[1]}"
                    )
                )
                return
            was_down = down
            time.sleep(0.01)

    threading.Thread(target=worker, daemon=True).start()

def refresh():
    if cfg.get("f10"):
        p = cfg["f10"]
        f10_var.set(f"F10 → Оплата без сдачи [{p[0]}, {p[1]}]")
    else:
        f10_var.set("F10 → Оплата без сдачи [не настроено]")

    if cfg.get("f11"):
        p = cfg["f11"]
        f11_var.set(f"F11 → Оплата картой [{p[0]}, {p[1]}]")
    else:
        f11_var.set("F11 → Оплата картой [не настроено]")

def save_keyword():
    cfg["window_keyword"] = keyword_var.get().strip()
    save_config()
    messagebox.showinfo("Готово", "Ключевое слово сохранено.")

def close_app():
    global running
    running = False
    root.destroy()

root = tk.Tk()
root.title("Контур.Маркет — горячие клавиши")
root.geometry("600x320")
root.resizable(False, False)

tk.Label(root, text="Контур.Маркет — управление оплатой",
         font=("Arial", 14, "bold")).pack(pady=(16, 12))

f10_var = tk.StringVar()
f11_var = tk.StringVar()

tk.Label(root, textvariable=f10_var, anchor="w").pack(fill="x", padx=20)
tk.Button(root, text="Настроить F10", width=28,
          command=lambda: train("Оплата без сдачи", "f10")).pack(pady=5)

tk.Label(root, textvariable=f11_var, anchor="w").pack(fill="x", padx=20)
tk.Button(root, text="Настроить F11", width=28,
          command=lambda: train("Оплата картой", "f11")).pack(pady=5)

frame = tk.Frame(root)
frame.pack(pady=12)
tk.Label(frame, text="Ключевое слово окна:").grid(row=0, column=0, padx=5)
keyword_var = tk.StringVar(value=cfg.get("window_keyword", "Контур"))
tk.Entry(frame, textvariable=keyword_var, width=20).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Сохранить", command=save_keyword).grid(row=0, column=2, padx=5)

tk.Label(
    root,
    text="1 нажатие = 1 клик   •   2 быстрых нажатия = двойной клик\n"
         "Работает только при активном окне Контур.Маркета.",
    justify="center"
).pack()

refresh()
threading.Thread(target=hotkey_loop, daemon=True).start()
root.protocol("WM_DELETE_WINDOW", close_app)
root.mainloop()
