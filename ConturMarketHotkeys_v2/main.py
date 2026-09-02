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
        for k,v in DEFAULT.items(): c.setdefault(k,v)
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

def pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return int(p.x), int(p.y)

def title():
    h = user32.GetForegroundWindow()
    n = user32.GetWindowTextLengthW(h)
    b = ctypes.create_unicode_buffer(n+1)
    user32.GetWindowTextW(h,b,n+1)
    return b.value

def click(x,y):
    user32.SetCursorPos(x,y); time.sleep(.035)
    user32.mouse_event(DOWN,0,0,0,0); user32.mouse_event(UP,0,0,0,0)

def mapping(name):
    return next((m for m in config["mappings"] if m["key"] == name), None)

last = {}
pressed = set()
lock = threading.Lock()

SPECIAL = {
    keyboard.Key.space:"SPACE", keyboard.Key.enter:"ENTER", keyboard.Key.tab:"TAB",
    keyboard.Key.backspace:"BACKSPACE", keyboard.Key.delete:"DELETE",
    keyboard.Key.insert:"INSERT", keyboard.Key.home:"HOME", keyboard.Key.end:"END",
    keyboard.Key.page_up:"PAGEUP", keyboard.Key.page_down:"PAGEDOWN",
    keyboard.Key.up:"UP", keyboard.Key.down:"DOWN", keyboard.Key.left:"LEFT",
    keyboard.Key.right:"RIGHT", keyboard.Key.esc:"ESC",
}
for i in range(1,25):
    SPECIAL[getattr(keyboard.Key, f"f{i}")] = f"F{i}"

def keyname(k):
    if k in SPECIAL: return SPECIAL[k]
    if isinstance(k, keyboard.KeyCode):
        if k.char: return k.char.upper()
        if k.vk: return f"VK_{k.vk}"
    return str(k).replace("Key.","").upper()

def on_press(k):
    name = keyname(k)
    with lock:
        if name in pressed: return
        pressed.add(name)
    m = mapping(name)
    if not m: return
    kw = str(config.get("window_keyword","")).lower().strip()
    if kw and kw not in title().lower(): return
    now=time.monotonic(); old=last.get(name,0)
    dbl=(now-old)<=float(config.get("double_window",.35))
    last[name]=0 if dbl else now
    threading.Thread(target=lambda: (click(m["x"],m["y"]), time.sleep(.075), click(m["x"],m["y"])) if dbl else click(m["x"],m["y"]), daemon=True).start()

def on_release(k):
    with lock: pressed.discard(keyname(k))

kbd = keyboard.Listener(on_press=on_press, on_release=on_release)
kbd.daemon=True; kbd.start()

root=tk.Tk()
root.title("Contur Market Hotkeys")
root.geometry("720x500")
root.resizable(False,False)

ttk.Label(root,text="Контур.Маркет — универсальные горячие клавиши",font=("Segoe UI",15,"bold")).pack(pady=(16,4))
ttk.Label(root,text="Добавляй любые клавиши. Все назначения сохраняются после закрытия.",font=("Segoe UI",10)).pack(pady=(0,12))

tree=ttk.Treeview(root,columns=("key","x","y"),show="headings",height=10)
for c,t,w in [("key","Клавиша",280),("x","X",140),("y","Y",140)]:
    tree.heading(c,text=t); tree.column(c,width=w,anchor="center")
tree.pack(padx=20,fill="x")

def refresh():
    for i in tree.get_children(): tree.delete(i)
    for m in config["mappings"]: tree.insert("", "end", values=(m["key"],m["x"],m["y"]))

def choose_key():
    w=tk.Toplevel(root); w.title("Выбор клавиши"); w.geometry("430x150"); w.transient(root); w.grab_set()
    ttk.Label(w,text="Нажми клавишу, которую хочешь назначить",font=("Segoe UI",12,"bold")).pack(pady=(25,8))
    ttk.Label(w,text="Например F10, F11, буква, цифра, Enter, Space, стрелка и т.д.").pack()
    def ev(e):
        w.destroy(); choose_point(e.keysym)
    w.bind("<KeyPress>",ev); w.focus_force()

def choose_point(key):
    messagebox.showinfo("Координата",f"Клавиша {key.upper()} выбрана.\n\nПерейди в Контур.Маркет, наведи мышь на нужную кнопку и нажми ЛЕВУЮ кнопку мыши.")
    def on_click(x,y,b,p):
        if not p or b != mouse.Button.left: return
        ml.stop()
        name=key.upper()
        config["mappings"]=[m for m in config["mappings"] if m["key"]!=name]
        config["mappings"].append({"key":name,"x":int(x),"y":int(y)})
        save(); root.after(0,refresh)
        root.after(0,lambda:messagebox.showinfo("Готово",f"{name} → X={x}, Y={y}\n\nСохранено в памяти программы."))
    ml=mouse.Listener(on_click=on_click); ml.daemon=True; ml.start()

def selected():
    s=tree.selection()
    return tree.item(s[0],"values")[0] if s else None

def delete():
    n=selected()
    if not n: messagebox.showwarning("Удаление","Выбери строку."); return
    config["mappings"]=[m for m in config["mappings"] if m["key"]!=n]; save(); refresh()

def test():
    n=selected(); m=mapping(n) if n else None
    if m: click(m["x"],m["y"])

buttons=ttk.Frame(root); buttons.pack(pady=12)
ttk.Button(buttons,text="＋ Добавить клавишу",command=choose_key).grid(row=0,column=0,padx=5)
ttk.Button(buttons,text="Тестировать",command=test).grid(row=0,column=1,padx=5)
ttk.Button(buttons,text="Удалить",command=delete).grid(row=0,column=2,padx=5)

box=ttk.LabelFrame(root,text="Дополнительно"); box.pack(fill="x",padx=20,pady=5)
ttk.Label(box,text="Ключевое слово активного окна:").grid(row=0,column=0,padx=8,pady=8)
kw=tk.StringVar(value=config.get("window_keyword","Контур")); ttk.Entry(box,textvariable=kw,width=22).grid(row=0,column=1,padx=8)
ttk.Label(box,text="Двойное нажатие, сек.:").grid(row=1,column=0,padx=8,pady=8)
dw=tk.StringVar(value=str(config.get("double_window",.35))); ttk.Entry(box,textvariable=dw,width=22).grid(row=1,column=1,padx=8)
def settings():
    try: v=float(dw.get().replace(",","."))
    except: messagebox.showerror("Ошибка","Интервал должен быть числом."); return
    config["window_keyword"]=kw.get().strip(); config["double_window"]=v; save()
    messagebox.showinfo("Сохранено","Настройки сохранены.\n\nПамять: "+CONFIG_FILE)
ttk.Button(box,text="Сохранить",command=settings).grid(row=0,column=2,rowspan=2,padx=12)

refresh()
def close():
    save(); kbd.stop(); root.destroy()
root.protocol("WM_DELETE_WINDOW",close)
root.mainloop()
