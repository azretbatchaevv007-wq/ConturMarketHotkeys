import json, os, time, threading, tkinter as tk
from tkinter import ttk, messagebox
import ctypes
from ctypes import wintypes
from pynput import keyboard, mouse

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ConturMarketHotkeys")
os.makedirs(APP_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

DEFAULT = {"double_window": 0.35, "window_keyword": "Контур", "mappings": []}

def load():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            c = json.load(f)
        for k, v in DEFAULT.items():
            c.setdefault(k, v)
        return c
    except Exception:
        return dict(DEFAULT)

config = load()

def save():
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)

user32 = ctypes.windll.user32
DOWN, UP = 0x0002, 0x0004

def get_title():
    h = user32.GetForegroundWindow()
    if not h:
        return ""
    n = user32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, b, n + 1)
    return b.value

def click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.035)
    user32.mouse_event(DOWN, 0, 0, 0, 0)
    user32.mouse_event(UP, 0, 0, 0, 0)

def double_click(x, y):
    click(x, y)
    time.sleep(0.075)
    click(x, y)

SPECIAL = {
    keyboard.Key.space: "SPACE", keyboard.Key.enter: "ENTER",
    keyboard.Key.tab: "TAB", keyboard.Key.backspace: "BACKSPACE",
    keyboard.Key.delete: "DELETE", keyboard.Key.insert: "INSERT",
    keyboard.Key.home: "HOME", keyboard.Key.end: "END",
    keyboard.Key.page_up: "PAGEUP", keyboard.Key.page_down: "PAGEDOWN",
    keyboard.Key.up: "UP", keyboard.Key.down: "DOWN",
    keyboard.Key.left: "LEFT", keyboard.Key.right: "RIGHT",
    keyboard.Key.esc: "ESC", keyboard.Key.shift: "SHIFT",
    keyboard.Key.shift_l: "SHIFT_L", keyboard.Key.shift_r: "SHIFT_R",
    keyboard.Key.ctrl: "CTRL", keyboard.Key.ctrl_l: "CTRL_L",
    keyboard.Key.ctrl_r: "CTRL_R", keyboard.Key.alt: "ALT",
    keyboard.Key.alt_l: "ALT_L", keyboard.Key.alt_r: "ALT_R",
    keyboard.Key.caps_lock: "CAPSLOCK", keyboard.Key.num_lock: "NUMLOCK",
    keyboard.Key.scroll_lock: "SCROLLLOCK", keyboard.Key.print_screen: "PRINTSCREEN",
    keyboard.Key.pause: "PAUSE", keyboard.Key.menu: "MENU",
}
for i in range(1, 25):
    k = getattr(keyboard.Key, f"f{i}", None)
    if k is not None:
        SPECIAL[k] = f"F{i}"

def readable(k):
    if k in SPECIAL:
        return SPECIAL[k]
    if isinstance(k, keyboard.KeyCode):
        if k.char:
            return k.char.upper()
        if k.vk is not None:
            return f"VK_{int(k.vk)}"
    return str(k).replace("Key.", "").upper()

def identifier(k):
    if isinstance(k, keyboard.KeyCode) and k.vk is not None:
        return f"VK_{int(k.vk)}"
    return readable(k)

def mapping_for(k):
    ident = identifier(k)
    for m in config["mappings"]:
        if m.get("id") == ident:
            return m
    # compatibility with older config
    name = readable(k)
    for m in config["mappings"]:
        if str(m.get("key", "")).upper() == name:
            return m
    return None

pressed = set()
pending = {}
lock = threading.Lock()

def active():
    kw = str(config.get("window_keyword", "")).strip().lower()
    return not kw or kw in get_title().lower()

def delayed_single(ident, mapping, stamp):
    time.sleep(float(config.get("double_window", 0.35)))
    with lock:
        item = pending.get(ident)
        if not item or item["stamp"] != stamp:
            return
        pending.pop(ident, None)
    if active():
        threading.Thread(target=click, args=(mapping["x"], mapping["y"]), daemon=True).start()

def on_press(k):
    ident = identifier(k)
    with lock:
        if ident in pressed:
            return
        pressed.add(ident)

    m = mapping_for(k)
    if not m or not active():
        return

    now = time.monotonic()
    window = float(config.get("double_window", 0.35))

    with lock:
        old = pending.get(ident)
        if old and now - old["stamp"] <= window:
            pending.pop(ident, None)
            threading.Thread(
                target=double_click,
                args=(m["x"], m["y"]),
                daemon=True
            ).start()
            return
        pending[ident] = {"stamp": now}

    threading.Thread(
        target=delayed_single,
        args=(ident, m, now),
        daemon=True
    ).start()

def on_release(k):
    with lock:
        pressed.discard(identifier(k))

kbd = keyboard.Listener(on_press=on_press, on_release=on_release)
kbd.daemon = True
kbd.start()

root = tk.Tk()
root.title("Contur Market Hotkeys")
root.geometry("760x540")
root.resizable(False, False)

ttk.Label(root, text="Контур.Маркет — универсальные горячие клавиши",
          font=("Segoe UI", 15, "bold")).pack(pady=(16, 4))
ttk.Label(root, text="Назначай любые клавиши: буквы, цифры, F-клавиши, Enter, Space, стрелки, NumPad и др.",
          font=("Segoe UI", 10)).pack(pady=(0, 12))

tree = ttk.Treeview(root, columns=("key", "id", "x", "y"), show="headings", height=12)
for c, t, w in [("key", "Клавиша", 240), ("id", "Идентификатор", 180), ("x", "X", 120), ("y", "Y", 120)]:
    tree.heading(c, text=t)
    tree.column(c, width=w, anchor="center")
tree.pack(padx=20, fill="x")

def refresh():
    for i in tree.get_children():
        tree.delete(i)
    for m in config["mappings"]:
        tree.insert("", "end", values=(m.get("key", ""), m.get("id", ""), m.get("x", ""), m.get("y", "")))

def choose_key():
    w = tk.Toplevel(root)
    w.title("Выбор клавиши")
    w.geometry("520x190")
    w.transient(root)
    w.grab_set()
    ttk.Label(w, text="Нажми нужную клавишу", font=("Segoe UI", 12, "bold")).pack(pady=(30, 8))
    ttk.Label(w, text="Поддерживаются буквы, цифры, F1–F24, Enter, Space, стрелки, NumPad и системные клавиши.").pack()
    def ev(e):
        w.grab_release()
        w.destroy()
        choose_point(e.keysym.upper())
    w.bind("<KeyPress>", ev)
    w.focus_force()

def choose_point(display_name):
    messagebox.showinfo(
        "Координата",
        f"Клавиша {display_name} выбрана.\n\n"
        "Перейди в Контур.Маркет, наведи мышь на нужную кнопку и нажми ЛЕВУЮ кнопку мыши."
    )

    def on_click(x, y, b, p):
        if not p or b != mouse.Button.left:
            return
        ml.stop()
        name = display_name.upper()
        # This stores the readable name. A temporary Windows keyboard
        # listener captures the actual VK code during the setup step.
        config["mappings"] = [m for m in config["mappings"] if str(m.get("key", "")).upper() != name]
        config["mappings"].append({
            "key": name,
            "id": name,
            "vk": "",
            "x": int(x),
            "y": int(y)
        })
        save()
        root.after(0, refresh)
        root.after(0, lambda: messagebox.showinfo(
            "Готово", f"{name} → X={x}, Y={y}\n\nНастройка сохранена."
        ))
    ml = mouse.Listener(on_click=on_click)
    ml.daemon = True
    ml.start()

def selected():
    s = tree.selection()
    if not s:
        return None
    name = str(tree.item(s[0], "values")[0])
    for m in config["mappings"]:
        if str(m.get("key", "")) == name:
            return m
    return None

def delete():
    m = selected()
    if not m:
        messagebox.showwarning("Удаление", "Выбери строку.")
        return
    config["mappings"].remove(m)
    save()
    refresh()

def test():
    m = selected()
    if m:
        click(m["x"], m["y"])

buttons = ttk.Frame(root)
buttons.pack(pady=12)
ttk.Button(buttons, text="＋ Добавить клавишу", command=choose_key).grid(row=0, column=0, padx=5)
ttk.Button(buttons, text="Тестировать", command=test).grid(row=0, column=1, padx=5)
ttk.Button(buttons, text="Удалить", command=delete).grid(row=0, column=2, padx=5)

box = ttk.LabelFrame(root, text="Дополнительно")
box.pack(fill="x", padx=20, pady=5)

ttk.Label(box, text="Ключевое слово активного окна:").grid(row=0, column=0, padx=8, pady=8)
kw = tk.StringVar(value=config.get("window_keyword", "Контур"))
ttk.Entry(box, textvariable=kw, width=24).grid(row=0, column=1, padx=8)

ttk.Label(box, text="Двойное нажатие, сек.:").grid(row=1, column=0, padx=8, pady=8)
dw = tk.StringVar(value=str(config.get("double_window", 0.35)))
ttk.Entry(box, textvariable=dw, width=24).grid(row=1, column=1, padx=8)

def settings():
    try:
        value = float(dw.get().replace(",", "."))
        if value <= 0:
            raise ValueError
    except Exception:
        messagebox.showerror("Ошибка", "Интервал должен быть положительным числом.")
        return
    config["window_keyword"] = kw.get().strip()
    config["double_window"] = value
    save()
    messagebox.showinfo("Сохранено", "Настройки сохранены.")

ttk.Button(box, text="Сохранить", command=settings).grid(row=0, column=2, rowspan=2, padx=12)

refresh()

def close():
    save()
    kbd.stop()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", close)
root.mainloop()
