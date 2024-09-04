import os
import pickle
import time
import threading
import tkinter as tk
from pynput import keyboard, mouse

# compile: nuitka --standalone --onefile --enable-plugin=tk-inter --plugin-enable=pylint-warnings copycat.py

# Список для хранения событий
events = []
recording = False
start_time = None

# Набор для отслеживания удерживаемых клавиш
pressed_keys = set()

# Обработчик событий мыши
def on_click(x, y, button, pressed):
    if recording:
        elapsed_time = time.time() - start_time
        events.append(('click', x, y, button, pressed, elapsed_time))

def on_move(x, y):
    if recording:
        elapsed_time = time.time() - start_time
        events.append(('move', x, y, elapsed_time))

# Обработчик событий клавиатуры
def on_press(key):
    global recording, start_time
    if recording:
        elapsed_time = time.time() - start_time
        
        if hasattr(key, 'char') and key.char:
            # Запись символа с учетом активной раскладки и модификаторов
            events.append(('key_press', key.char, elapsed_time))
        elif key not in pressed_keys:
            pressed_keys.add(key)
            current_combo = tuple(pressed_keys)
            events.append(('key_combo_press', current_combo, elapsed_time))

def on_release(key):
    global recording
    if recording:
        elapsed_time = time.time() - start_time
        if key in pressed_keys:
            pressed_keys.remove(key)
            events.append(('key_release', key, elapsed_time))

# Функция для начала записи
def start_recording():
    global recording, start_time, events
    recording = True
    start_time = time.time()
    events = []
    text_output.insert(tk.END, "Recording started...\n")

# Функция для остановки записи
def stop_recording():
    global recording
    recording = False
    text_output.insert(tk.END, "Recording stopped.\n")
    with open('events.pkl', 'wb') as f:
        pickle.dump(events, f)
    text_output.insert(tk.END, "Events saved to 'events.pkl'.\n")

# Функция для воспроизведения записанных событий
def replay_events():
    def replay():
        if not os.path.exists('events.pkl'):
            text_output.insert(tk.END, "No events to replay. Record some events first.\n")
            return

        text_output.insert(tk.END, "Replaying events...\n")
        with open('events.pkl', 'rb') as f:
            events = pickle.load(f)

        keyboard_controller = keyboard.Controller()
        mouse_controller = mouse.Controller()

        start_time = events[0][-1]

        for event in events:
            event_type = event[0]
            delay_time = event[-1]
            time.sleep(delay_time - start_time)
            start_time = delay_time

            if event_type == 'move':
                x, y = event[1], event[2]
                mouse_controller.position = (x, y)
            elif event_type == 'click':
                x, y, button, pressed = event[1], event[2], event[3], event[4]
                mouse_controller.position = (x, y)
                if pressed:
                    mouse_controller.press(button)
                else:
                    mouse_controller.release(button)
            elif event_type == 'key_combo_press':
                combo = event[1]
                for key in combo:
                    keyboard_controller.press(key)
            elif event_type == 'key_release':
                key = event[1]
                keyboard_controller.release(key)
            elif event_type == 'key_press':
                char = event[1]
                keyboard_controller.type(char)

            # Выводим действие в текстовое поле
            text_output.insert(tk.END, f"Replayed event: {event}\n")

    # Запуск воспроизведения в отдельном потоке
    threading.Thread(target=replay).start()

def on_closing():
    listener_click.stop()
    keyboard_listener.stop()
    root.destroy()

# Создание GUI с использованием tkinter
def create_gui():
    global root, text_output
    
    root = tk.Tk()
    root.title("copycat")

    # Настройки для темной темы
    root.configure(bg='#2E2E2E')

    frame = tk.Frame(root, bg='#2E2E2E')
    frame.pack(pady=10, padx=10)

    # Кнопка "Start Recording"
    start_button = tk.Button(frame, text="Start Recording", command=start_recording, width=20, bg='#555555', fg='#FFFFFF')
    start_button.grid(row=0, column=0, padx=5, pady=5)

    # Кнопка "Stop Recording"
    stop_button = tk.Button(frame, text="Stop Recording", command=stop_recording, width=20, bg='#555555', fg='#FFFFFF')
    stop_button.grid(row=0, column=1, padx=5, pady=5)

    # Кнопка "Replay Events"
    replay_button = tk.Button(frame, text="Replay Events", command=replay_events, width=20, bg='#555555', fg='#FFFFFF')
    replay_button.grid(row=0, column=2, padx=5, pady=5)

    # Текстовое поле для вывода сообщений
    text_output = tk.Text(root, height=10, width=60, bg='#1E1E1E', fg='#FFFFFF', insertbackground='white')
    text_output.pack(pady=10)

    # Привязка закрытия окна к завершению слушателей
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Запуск основного цикла обработки событий
    root.mainloop()

# Установка слушателей для мыши
listener_click = mouse.Listener(on_click=on_click, on_move=on_move)
listener_click.start()

# Прослушивание клавиш в отдельном потоке
def listen_keyboard():
    global keyboard_listener
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()
    keyboard_listener.join()

# Запуск прослушивания клавиш в отдельном потоке
keyboard_thread = threading.Thread(target=listen_keyboard)
keyboard_thread.start()

# Запуск GUI
create_gui()
