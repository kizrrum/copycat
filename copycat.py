import os  # Модуль для работы с операционной системой
import pickle  # Модуль для сериализации и десериализации объектов Python
import time  # Модуль для работы с временем
import threading  # Модуль для работы с потоками
import tkinter as tk  # Модуль для создания графического интерфейса
from pynput import keyboard, mouse  # Модули для отслеживания событий клавиатуры и мыши
import ctypes  # Модуль для работы с C-совместимыми типами данных
import sys  # Модуль для доступа к некоторым параметрам и функциям Python

# Функция для проверки наличия прав администратора
def is_admin():
    if os.name == 'nt':  # Если это Windows
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()  # Проверяем права администратора
        except:
            return False
    elif os.name == 'posix':  # Если это Linux или другая Unix-подобная система
        return os.geteuid() == 0  # Проверяет, запущен ли процесс от имени root
    else:
        return False

# Проверяем, запущена ли программа с правами администратора
if not is_admin():
    if os.name == 'nt':  # Для Windows
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    elif os.name == 'posix':  # Для Linux
        print("Для выполнения этой программы необходимы права суперпользователя. Перезапустите её с использованием 'sudo'.")
    sys.exit()  # Завершаем программу, если нет прав

# compile: nuitka --standalone --onefile --enable-plugin=tk-inter --plugin-enable=pylint-warnings copycat.py
# Команда для компиляции скрипта в исполняемый файл

# Список для хранения событий
events = []
recording = False  # Флаг для проверки, идет ли запись
start_time = None  # Время начала записи

# Набор для отслеживания удерживаемых клавиш
pressed_keys = set()

# Обработчик событий мыши
def on_click(x, y, button, pressed):
    if recording:  # Если идет запись
        elapsed_time = time.time() - start_time  # Вычисляем прошедшее время
        events.append(('click', x, y, button, pressed, elapsed_time))  # Добавляем событие в список

def on_move(x, y):
    if recording:  # Если идет запись
        elapsed_time = time.time() - start_time  # Вычисляем прошедшее время
        events.append(('move', x, y, elapsed_time))  # Добавляем событие в список

# Обработчик событий клавиатуры
def on_press(key):
    global recording, start_time
    if recording:  # Если идет запись
        elapsed_time = time.time() - start_time  # Вычисляем прошедшее время
        
        if hasattr(key, 'char') and key.char:  # Если клавиша имеет символ
            events.append(('key_press', key.char, elapsed_time))  # Добавляем событие нажатия символа
        elif key not in pressed_keys:  # Если клавиша не удерживается
            pressed_keys.add(key)  # Добавляем клавишу в набор удерживаемых
            current_combo = tuple(pressed_keys)  # Создаем кортеж из удерживаемых клавиш
            events.append(('key_combo_press', current_combo, elapsed_time))  # Добавляем событие комбинации клавиш

def on_release(key):
    global recording
    if recording:  # Если идет запись
        elapsed_time = time.time() - start_time  # Вычисляем прошедшее время
        if key in pressed_keys:  # Если клавиша удерживалась
            pressed_keys.remove(key)  # Убираем клавишу из набора удерживаемых
            events.append(('key_release', key, elapsed_time))  # Добавляем событие отпускания клавиши

# Функция для начала записи
def start_recording():
    global recording, start_time, events
    recording = True  # Устанавливаем флаг записи
    start_time = time.time()  # Запоминаем время начала
    events = []  # Очищаем список событий
    text_output.insert(tk.END, "Recording started...\n")  # Выводим сообщение в текстовое поле

# Функция для остановки записи
def stop_recording():
    global recording
    recording = False  # Сбрасываем флаг записи
    text_output.insert(tk.END, "Recording stopped.\n")  # Выводим сообщение в текстовое поле
    with open('events.pkl', 'wb') as f:  # Открываем файл для записи
        pickle.dump(events, f)  # Сохраняем события в файл
    text_output.insert(tk.END, "Events saved to 'events.pkl'.\n")  # Выводим сообщение о сохранении


# Функция для воспроизведения записанных событий
def replay_events():
    def replay():
        if not os.path.exists('events.pkl'):  # Проверяем, существует ли файл
            text_output.insert(tk.END, "No events to replay. Record some events first.\n")  # Выводим сообщение, если файл не найден
            return

        text_output.insert(tk.END, "Replaying events...\n")  # Выводим сообщение о начале воспроизведения
        with open('events.pkl', 'rb') as f:  # Открываем файл для чтения
            events = pickle.load(f)  # Загружаем события из файла

        keyboard_controller = keyboard.Controller()  # Создаем контроллер клавиатуры
        mouse_controller = mouse.Controller()  # Создаем контроллер мыши

        start_time = events[0][-1]  # Начальное время первого события

        for event in events:  # Проходим по всем событиям
            event_type = event[0]  # Тип события
            delay_time = event[-1]  # Задержка времени
            time.sleep(delay_time - start_time)  # Ждем до следующего события
            start_time = delay_time

            if event_type == 'move':  # Если событие перемещения мыши
                x, y = event[1], event[2]
                mouse_controller.position = (x, y)  # Устанавливаем позицию мыши
            elif event_type == 'click':  # Если событие клика мыши
                x, y, button, pressed = event[1], event[2], event[3], event[4]
                mouse_controller.position = (x, y)
                if pressed:
                    mouse_controller.press(button)  # Нажимаем кнопку мыши
                else:
                    mouse_controller.release(button)  # Отпускаем кнопку мыши
            elif event_type == 'key_combo_press':  # Если событие комбинации клавиш
                combo = event[1]
                for key in combo:
                    keyboard_controller.press(key)  # Нажимаем каждую клавишу в комбинации
            elif event_type == 'key_release':  # Если событие отпускания клавиши
                key = event[1]
                keyboard_controller.release(key)  # Отпускаем клавишу
            elif event_type == 'key_press':  # Если событие нажатия клавиши
                char = event[1]
                keyboard_controller.type(char)  # Печатаем символ

            # Выводим действие в текстовое поле
            text_output.insert(tk.END, f"Replayed event: {event}\n")

    # Запуск воспроизведения в отдельном потоке
    threading.Thread(target=replay).start()

# Функция для завершения программы при закрытии окна
def on_closing():
    listener_click.stop()  # Останавливаем слушатель мыши
    keyboard_listener.stop()  # Останавливаем слушатель клавиатуры
    root.destroy()  # Закрываем окно

# Создание GUI с использованием tkinter
def create_gui():
    global root, text_output
    
    root = tk.Tk()  # Создаем главное окно
    root.title("copycat")  # Устанавливаем заголовок окна

    # Настройки для темной темы
    root.configure(bg='#2E2E2E')  # Устанавливаем цвет фона

    frame = tk.Frame(root, bg='#2E2E2E')  # Создаем фрейм
    frame.pack(pady=10, padx=10)  # Упаковываем фрейм в окно

    # Кнопка "Start Recording"
    start_button = tk.Button(frame, text="Start Recording", command=start_recording, width=20, bg='#555555', fg='#FFFFFF')
    start_button.grid(row=0, column=0, padx=5, pady=5)  # Размещаем кнопку в сетке

    # Кнопка "Stop Recording"
    stop_button = tk.Button(frame, text="Stop Recording", command=stop_recording, width=20, bg='#555555', fg='#FFFFFF')
    stop_button.grid(row=0, column=1, padx=5, pady=5)  # Размещаем кнопку в сетке

    # Кнопка "Replay Events"
    replay_button = tk.Button(frame, text="Replay Events", command=replay_events, width=20, bg='#555555', fg='#FFFFFF')
    replay_button.grid(row=0, column=2, padx=5, pady=5)  # Размещаем кнопку в сетке

    # Текстовое поле для вывода сообщений
    text_output = tk.Text(root, height=10, width=60, bg='#1E1E1E', fg='#FFFFFF', insertbackground='white')
    text_output.pack(pady=10)  # Упаковываем текстовое поле в окно

    # Привязка закрытия окна к завершению слушателей
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Запуск основного цикла обработки событий
    root.mainloop()

# Установка слушателей для мыши
listener_click = mouse.Listener(on_click=on_click, on_move=on_move)
listener_click.start()  # Запуск слушателя мыши

# Прослушивание клавиш в отдельном потоке
def listen_keyboard():
    global keyboard_listener
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()  # Запуск слушателя клавиатуры
    keyboard_listener.join()  # Ожидание завершения потока

# Запуск прослушивания клавиш в отдельном потоке
keyboard_thread = threading.Thread(target=listen_keyboard)
keyboard_thread.start()  # Запуск потока для слушателя клавиатуры

# Запуск GUI
create_gui()  # Создание и запуск графического интерфейса