import os
import pickle
import time
import threading
import tkinter as tk
from pynput import keyboard, mouse
import ctypes
import sys

# --- Проверка прав администратора ---
def is_admin():
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    elif os.name == 'posix':
        return os.geteuid() == 0
    else:
        return False

if not is_admin():
    if os.name == 'nt':
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
            " ".join(sys.argv), None, 1)
    else:
        print("Требуются права суперпользователя. Перезапустите с sudo.")
    sys.exit()

# --- Глобальные переменные ---
events = []
recording = False
replaying = False
start_time = None
stop_flag = False   # один флаг для всего
pressed_keys = set()
loop_var = None
text_output = None

# --- Обработчики событий клавиатуры и мыши ---
def on_click(x, y, button, pressed):
    if recording and not stop_flag:
        elapsed = time.time() - start_time
        events.append(('click', x, y, button, pressed, elapsed))

def on_move(x, y):
    if recording and not stop_flag:
        elapsed = time.time() - start_time
        events.append(('move', x, y, elapsed))

def on_press(key):
    global stop_flag, recording, replaying
    if key == keyboard.Key.f12:
        stop_flag = True
        text_output.insert(tk.END, "🛑 Нажата F12 — останавливаем всё\n")
        text_output.see(tk.END)
        # если шли запись или воспроизведение, завершаем их
        if recording:
            recording = False
            save_events()
        # replay_loop внутри сам завершится при проверке stop_flag

def on_release(key):
    if recording and key in pressed_keys and not stop_flag:
        pressed_keys.remove(key)
        events.append(('key_release', key, time.time() - start_time))

# --- Утилиты ---
def save_events():
    with open('events.pkl', 'wb') as f:
        pickle.dump(events, f)
    text_output.insert(tk.END, "События сохранены в 'events.pkl'.\n")
    text_output.see(tk.END)

# --- Запись ---
def start_recording():
    global recording, start_time, events, stop_flag
    stop_flag = False
    recording = True
    start_time = time.time()
    events.clear()
    text_output.insert(tk.END, "🔴 Запись началась (F12 для остановки)\n")
    text_output.see(tk.END)
    threading.Thread(target=record_loop, daemon=True).start()

def record_loop():
    global recording
    # цикл записи
    while recording and not stop_flag:
        time.sleep(0.01)  # минимальная задержка, события ловятся слушателем
    if recording and stop_flag:
        # если остановили F12
        recording = False
        save_events()

def stop_recording():
    global recording
    if recording:
        recording = False
        text_output.insert(tk.END, "⏹ Остановка записи (кнопка)\n")
        text_output.see(tk.END)
        save_events()

# --- Воспроизведение ---
def replay_events():
    global stop_flag, replaying
    if replaying:
        return
    stop_flag = False
    replaying = True
    text_output.insert(tk.END, "▶ Воспроизведение началось (F12 для стопа)\n")
    text_output.see(tk.END)
    threading.Thread(target=replay_loop, daemon=True).start()

def replay_loop():
    global replaying
    try:
        if not os.path.exists('events.pkl'):
            text_output.insert(tk.END, "Нет файла 'events.pkl'. Сначала запишите события.\n")
            text_output.see(tk.END)
            replaying = False
            return

        with open('events.pkl', 'rb') as f:
            loaded_events = pickle.load(f)

        kb = keyboard.Controller()
        ms = mouse.Controller()

        first_time = loaded_events[0][-1] if loaded_events else 0
        while not stop_flag:
            for event in loaded_events:
                if stop_flag:
                    break
                etype = event[0]
                delay = event[-1]
                time.sleep(max(0, delay - first_time))
                first_time = delay

                if etype == 'move':
                    ms.position = (event[1], event[2])
                elif etype == 'click':
                    ms.position = (event[1], event[2])
                    if event[4]:
                        ms.press(event[3])
                    else:
                        ms.release(event[3])
                elif etype == 'key_press':
                    kb.type(event[1])
                elif etype == 'key_release':
                    kb.release(event[1])
                elif etype == 'key_combo_press':
                    for k in event[1]:
                        kb.press(k)

                text_output.insert(tk.END, f"Воспроизведено: {event}\n")
                text_output.see(tk.END)

            if not loop_var.get() or stop_flag:
                break
            time.sleep(0.1)
    except Exception as e:
        text_output.insert(tk.END, f"Ошибка воспроизведения: {e}\n")
        text_output.see(tk.END)
    finally:
        replaying = False
        text_output.insert(tk.END, "🛑 Воспроизведение остановлено\n")
        text_output.see(tk.END)

# --- Закрытие ---
def on_closing():
    listener.click_listener.stop()
    listener.key_listener.stop()
    root.destroy()

# --- GUI ---
def create_gui():
    global root, text_output, loop_var, listener
    root = tk.Tk()
    root.title("copycat")
    root.configure(bg='#2E2E2E')

    frame = tk.Frame(root, bg='#2E2E2E')
    frame.pack(padx=10, pady=10)

    tk.Button(frame, text="Начать запись", command=start_recording,
              bg='#555555', fg='white').grid(row=0, column=0, padx=5, pady=5)
    tk.Button(frame, text="Остановить запись", command=stop_recording,
              bg='#555555', fg='white').grid(row=0, column=1, padx=5, pady=5)
    tk.Button(frame, text="Воспроизвести", command=replay_events,
              bg='#555555', fg='white').grid(row=0, column=2, padx=5, pady=5)

    loop_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Цикл", variable=loop_var,
                   bg='#2E2E2E', fg='white', selectcolor='#444444')\
       .grid(row=1, column=0, columnspan=3, pady=5)

    tk.Label(frame,
             text="Горячая клавиша: F12 — стоп для записи/воспроизведения",
             bg='#2E2E2E', fg='gray', font=("Arial", 9))\
      .grid(row=2, column=0, columnspan=3, pady=5)

    log_frame = tk.Frame(root, bg='#2E2E2E')
    log_frame.pack(padx=10, pady=10)

    text_output = tk.Text(log_frame, height=10, width=60,
                          bg='#1E1E1E', fg='white', insertbackground='white')
    text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(log_frame, command=text_output.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_output.config(yscrollcommand=scrollbar.set)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # запускаем слушатели
    listener = lambda: None
    listener.click_listener = mouse.Listener(on_click=on_click, on_move=on_move)
    listener.click_listener.daemon = True
    listener.click_listener.start()

    listener.key_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.key_listener.daemon = True
    listener.key_listener.start()

    root.mainloop()

if __name__ == "__main__":
    create_gui()
