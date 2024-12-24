import os
import json
import psutil
import logging
import requests  # Импортируем библиотеку для выполнения HTTP-запросов
import tkinter as tk
from tkinter import messagebox, Tk, Label, Button, Frame, Toplevel, simpledialog, Text, Scrollbar, Entry, VERTICAL, END
from plyer import notification
import matplotlib.pyplot as plt
import GPUtil  # Импортируем библиотеку GPUtil
import wmi  # Импортируем библиотеку WMI для Windows
import asyncio  # Импортируем asyncio для асинхронного программирования

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Хранилище пользователей
users = {}
current_user = None  # Переменная для хранения текущего пользователя

# Загружаем пользователей из файла
def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

# Сохраняем пользователей в файл
def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f)

users = load_users()

def validate_credentials(username, password):
    if len(username) < 3:
        return "Логин должен содержать минимум 3 символа."
    if len(password) < 5 or not any(char.isdigit() for char in password) or not any(char.isupper() for char in password):
        return "Пароль должен содержать минимум 5 символов, 1 заглавную букву и 1 цифру."
    return None

def get_system_info():
    # Получаем информацию о процессоре
    cpu_info = psutil.cpu_freq()
    cpu_usage = psutil.cpu_percent()
    cpu_count = psutil.cpu_count(logical=True)
    cpu_time = psutil.cpu_times()
    
    cpu_details = {
        "manufacturer": "Intel/AMD",  # Замените на фактического производителя, если возможно
        "model": "Unknown Model",  # Замените на фактическую модель, если возможно
        "usage_percent": cpu_usage,
        "speed_ghz": cpu_info.current / 1000,
        "logical_cores": cpu_count,
        "process_count": len(psutil.pids()),
        "time_worked": cpu_time.user + cpu_time.system
    }

    # Получаем информацию о RAM
    ram = psutil.virtual_memory()
    ram_details = {
        "total": ram.total / (1024 ** 3),  # В ГБ
        "used": ram.used / (1024 ** 3),    # В ГБ
        "percent": ram.percent
    }

    # Получаем информацию о диске
    disk = psutil.disk_usage('/')
    disk_details = {
        "total": disk.total / (1024 ** 3),  # В ГБ
        "used": disk.used / (1024 ** 3),    # В ГБ
        "percent": disk.percent
    }

    return cpu_details, ram_details, disk_details

class App:
    # Параметры для Яндекс GPT API
    FOLDER_ID = 'ajenlrabc9mipsq5u1kh'
    API_KEY = 'AQVN167UtibSzzRfBpGnIUKvkG0RDmaxRI3Vr2LM'

    def __init__(self, root):
        self.root = root
        self.root.title("Регистрация")
        self.root.geometry("600x400")
        self.root.resizable(False, False)  # Запрет изменения размера основного окна

        self.main_frame = Frame(self.root, bg='white')
        self.main_frame.pack(padx=10, pady=10)

        self.label = Label(self.main_frame, text="Выберите действие:", bg='white', fg='black', font=('Arial', 14))
        self.label.grid(row=0, column=0, columnspan=2, pady=10)

        # Кнопки для входа и регистрации
        self.login_button = Button(self.main_frame, text="Войти", command=self.login, borderwidth=2, relief="solid", bg='white', fg='black')
        self.login_button.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

        self.register_button = Button(self.main_frame, text="Зарегистрироваться", command=self.register, borderwidth=2, relief="solid", bg='white', fg='black')
        self.register_button.grid(row=1, column=1, padx= 5, pady=5, sticky='ew')

    def update_system_info(self):
        cpu_details, ram_details, disk_details = get_system_info()
        self.system_info = {
            "cpu": cpu_details,
            "ram": ram_details,
            "disk": disk_details
        }

    def search_components(self):
        query = simpledialog.askstring("Поиск комплектующих", "Введите название комплектующего:")
        if query:
            search_url = f"https://yandex.ru/search/?text={query}"  # URL для поиска
            import webbrowser
            webbrowser.open(search_url)

    async def yandex_gpt_async(self, prompt):
        # Формируем тело запроса для API Яндекс GPT
        body = {
            "modelUri": "gpt://b1g5as5ldcaf2l4l7jnb/yandexgpt/latest",  # Указываем модель для GPT
            "completionOptions": {
                "stream": False,  # Запрещаем стриминг, чтобы получить полный ответ сразу
                "temperature": 0.7,  # Уровень креативности
                "maxTokens": 4500  # Максимальное количество токенов в ответе
            },
            "messages": [
                {
                    "role": "user",  # Указываем, что это запрос от пользователя
                    "text": prompt  # Текст запроса
                }
            ]
        }

        # Отправляем запрос в Яндекс API
        response = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {self.API_KEY}",
                "x-folder-id": self.FOLDER_ID
            },
            json=body
        )

        if response.status_code == 200:
            operation_id = response.json().get('id')
        else:
            return f"Error from Yandex API: {response.text}"

        operation_done = False
        max_attempts = 22
        attempts = 0

        while not operation_done and attempts < max_attempts:
            operation_response = requests.get(
                f"https://operation.api.cloud.yandex.net/operations/{operation_id}",
                headers={"Authorization": f"Api-Key {self.API_KEY}"}
            )

            if operation_response.status_code == 200:
                operation_result = operation_response.json()
                operation_done = operation_result.get('done', False)

                if not operation_done:
                    await asyncio.sleep(10)
                    attempts += 1
                else:
                    response = operation_result.get('response', {})
                    alternatives = response.get('alternatives', [])
                    if alternatives:
                        return alternatives[0].get('message', {}).get('text', '')
            else:
                return f"Ошибка ответа: {operation_response.text}"

        return "Операция не завершена успешно"

    def send_message(self, event=None):
        user_message = self.user_input.get()
        if user_message:
            self.chat_text.config(state='normal')
            self.chat_text.insert(END, f"Вы: {user_message}\n")
            self.chat_text.config(state='disabled')
            self.user_input.delete(0, 'end')

            # Получаем ответ от Яндекс GPT
            asyncio.run(self.get_gpt_response(user_message))

    async def get_gpt_response(self, user_message):
        ai_response = await self.yandex_gpt_async(user_message)  # Асинхронный вызов
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, f"ИИ: {ai_response}\n")
        self.chat_text.config(state='disabled')
        self.chat_text.see(END)  # Прокрутка к последнему сообщению

    def login(self):
        global current_user
        username = simpledialog.askstring("Вход", "Введите имя пользователя:")
        password = simpledialog.askstring("Пароль", "Введите пароль:", show='*')

        if username and password:
            if username in users and users[username]['password'] == password:
                current_user = username
                logging.info(f"Пользователь {username} вошел в систему.")
                messagebox.showinfo("Успех", f"Добро пожаловать, {username}!")
                self.show_system_info_interface()
            else:
                messagebox.showerror("Ошибка", "Неправильный логин или пароль.")

    def register(self):
        global current_user
        username = simpledialog.askstring("Регистрация", "Введите имя пользователя:")
        password = simpledialog.askstring("Пароль", "Введите пароль:", show='*')

        if username and password:
            validation_error = validate_credentials(username, password)
            if validation_error:
                messagebox.showerror("Ошибка", validation_error)
            else:
                if username not in users:
                    users[username] = {'password': password}
                    save_users()
                    logging.info(f"Пользователь {username} зарегистрирован.")
                    messagebox.showinfo("Успех", f"Пользователь {username} зарегистрирован!")
                    current_user = username
                    self.show_system_info_interface()
                else:
                    messagebox.showerror("Ошибка", "Пользователь с таким именем уже существует.")

    def show_chat_interface(self):
        chat_window = Toplevel(self.root)
        chat_window.title("Чат с ИИ")
        chat_window.geometry("500x600")  # Увеличиваем высоту окна для размещения кнопок

        chat_frame = Frame(chat_window)
        chat_frame.pack(pady=10)

        # Создаем текстовое поле с прокруткой
        self.chat_text = Text(chat_frame, wrap='word', state='disabled', width=60, height=20, bg='#f0f0f0', fg='black', font=('Arial', 12))
        self.chat_text.pack(side='left', padx=10, pady=10)

        scrollbar = Scrollbar(chat_frame, command=self.chat_text.yview, orient=VERTICAL)
        scrollbar.pack(side='right', fill='y')
        self.chat_text['yscrollcommand'] = scrollbar.set

        self.user_input = Entry(chat_window, width=60, font=('Arial', 12))
        self.user_input.pack(padx=10, pady=10)
        self.user_input.bind("<Return>", self.send_message)

        send_button = Button(chat_window, text="Отправить", command=self.send_message, bg='blue', fg='white', font=('Arial', 12))
        send_button.pack(pady=5)

        # Кнопки для дополнительных функций
        button_frame = Frame(chat_window)
        button_frame.pack(pady=10)

        # Кнопка для обработки естественного языка
        nlp_button = Button(button_frame, text="NLP", command=self.handle_nlp, width=10)
        nlp_button.grid(row=0, column=0, padx=5)

        # Кнопка для истории чата
        history_button = Button(button_frame, text="История", command=self.show_history, width=10)
        history_button.grid(row=0, column=1, padx=5)

        # Кнопка для тем и контекстов
        context_button = Button(button_frame, text="Темы", command=self.change_context, width=10)
        context_button.grid(row=0, column=2, padx=5)

        # Кнопка для поддержки мультимедиа
        multimedia_button = Button(button_frame, text="Мультимедиа", command=self.handle_multimedia, width=10)
        multimedia_button.grid(row=0, column=3, padx=5)

        # Кнопка для эмоциональной реакции
        emotion_button = Button(button_frame, text="Эмоции", command=self.handle_emotions, width=10)
        emotion_button.grid(row=0, column=4, padx=5)

        # Кнопка для интерактивных элементов
        interactive_button = Button(button_frame, text="Интерактивные", command=self.handle_interactive, width=10)
        interactive_button.grid(row=1, column=0, padx=5)

        # Кнопка для персонализации
        personalization_button = Button(button_frame, text="Персонализация", command=self.handle_personalization, width=10)
        personalization_button.grid(row=1, column=1, padx=5)

        # Кнопка для подсказок и рекомендаций
        recommendations_button = Button(button_frame, text="Рекомендации", command=self.show_recommendations, width=10)
        recommendations_button.grid(row=1, column=2, padx=5)

        # Кнопка для обратной связи
        feedback_button = Button(button_frame, text="Обратная связь", command=self.give_feedback, width=10)
        feedback_button.grid(row=1, column=3, padx=5)

        # Кнопка для интеграции с другими сервисами
        integration_button = Button(button_frame, text="Интеграция", command=self.handle_integration, width=10)
        integration_button.grid(row=1, column=4, padx=5)

        # Кнопка для помощи
        help_button = Button(button_frame, text="Помощь", command=self.show_help, width=10)
        help_button.grid(row=2, column=0, padx=5)

        # Кнопка для анонимности и безопасности
        security_button = Button(button_frame, text="Безопасности", command=self.handle_security, width=10)
        security_button.grid(row=2, column=1, padx=5)

        # Кнопка для поддержки нескольких языков
        language_button = Button(button_frame, text="Языки", command=self.handle_languages, width=10)
        language_button.grid(row=2, column=2, padx=5)

        # Обновляем интерфейс, чтобы кнопки были видны
        button_frame.update_idletasks()  # Обновляем компоновку кнопок
        chat_window.update()  # Обновляем окно чата

    # Пример методов для обработки нажатий на кнопки
    def handle_nlp(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Обработка естественного языка активирована.\n")
        self.chat_text.config(state='disabled')

    def show_history(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "История чата:\n")
        self.chat_text.config(state='disabled')

    def change_context(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Темы и контексты изменены.\n")
        self.chat_text.config(state='disabled')

    def handle_multimedia(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Поддержка мультимедиа активирована.\n")
        self.chat_text.config(state='disabled')

    def handle_emotions(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Эмоциональная реакция активирована.\n")
        self.chat_text.config(state='disabled')

    def handle_interactive(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Интерактивные элементы активированы.\n")
        self.chat_text.config(state='disabled')

    def handle_personalization(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Персонализация активирована.\n")
        self.chat_text.config(state='disabled')

    def show_recommendations(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Рекомендации предоставлены.\n")
        self.chat_text.config(state='disabled')

    def give_feedback(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Обратная связь отправлена.\n")
        self.chat_text.config(state='disabled')

    def handle_integration(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Интеграция с сервисами активирована.\n")
        self.chat_text.config(state='disabled')

    def show_help(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Помощь предоставлена.\n")
        self.chat_text.config(state='disabled')

    def handle_security(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Безопасность активирована.\n")
        self.chat_text.config(state='disabled')

    def handle_languages(self):
        self.chat_text.config(state='normal')
        self.chat_text.insert(END, "Поддержка нескольких языков активирована.\n")
        self.chat_text.config(state='disabled')

    def show_system_info_interface(self):
        self.root.title("Информация о системе")
        self.label.config(text="Выберите компонент для получения информации:")
        self.clear_main_interface()

        self.cpu_button = Button(self.main_frame, text="Процессор", command=self.show_cpu_info, borderwidth=2, relief="solid", width=25, height=2, bg='white', fg='black')
        self.cpu_button.grid(row=2, column=0, padx=5, pady=5, sticky='ew')

        self.ram_button = Button(self.main_frame, text="Оперативная память", command=self.show_ram_info, borderwidth=2, relief="solid", width=25, height=2, bg='white', fg='black')
        self.ram_button.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

        self.disk_button = Button(self.main_frame, text="Жесткий диск", command=self.show_disk_info, borderwidth=2, relief="solid", width=25, height=2, bg='white', fg='black')
        self.disk_button.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

        self.gpu_button = Button(self.main_frame, text="Видеокарта", command=self.show_gpu_info, borderwidth=2, relief="solid", width =25, height=2, bg='white', fg='black')
        self.gpu_button.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        self.motherboard_button = Button(self.main_frame, text="Материнская плата", command=self.show_motherboard_info, borderwidth=2, relief="solid", width=25, height=2, bg='white', fg='black')
        self.motherboard_button.grid(row=4, column=1, padx=5, pady=5, sticky='ew')

        self.plot_button = Button(self.main_frame, text="График загрузки", command=self.plot_usage, borderwidth=2, relief="solid", width=25, height=2, bg='white', fg='black')
        self.plot_button.grid(row=4, column=0, padx=5, pady=5, sticky='ew')

        self.logout_button = Button(self.main_frame, text="Выйти", command=self.logout, borderwidth=2, relief="solid", bg='white', fg='black')
        self.logout_button.grid(row=7, column=0, padx=5, pady=5, sticky='ew')

        self.delete_account_button = Button(self.main_frame, text="Удалить учетную запись", command=self.delete_account, borderwidth=2, relief="solid", bg='white', fg='black')
        self.delete_account_button.grid(row=7, column=1, padx=5, pady=5, sticky='ew')

        self.search_button = Button(self.main_frame, text="Поиск комплектующих", command=self.search_components, borderwidth=2, relief="solid", bg='white', fg='black')
        self.search_button.grid(row=8, column=0, padx=5, pady=5, sticky='ew')

        self.chat_button = Button(self.main_frame, text="Чат с ИИ", command=self.show_chat_interface, borderwidth=2, relief="solid", bg='white', fg='black')
        self.chat_button.grid(row=8, column=1, padx=5, pady=5, sticky='ew')

        self.update_system_info()  # Обновление информации о системе

    def clear_main_interface(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_cpu_info(self):
        self.update_system_info()
        cpu_info = self.system_info["cpu"]
        content = (f"Производитель: {cpu_info['manufacturer']}\n"
                   f"Модель: {cpu_info['model']}\n"
                   f"Загрузка: {cpu_info['usage_percent']}%\n"
                   f"Скорость: {cpu_info['speed_ghz']} ГГц\n"
                   f"Количество логических ядер: {cpu_info['logical_cores']}\n"
                   f"Количество процессов: {cpu_info['process_count']}\n"
                   f"Время работы: {cpu_info['time_worked']} сек")
        self.show_info_window("Информация о процессоре", content)

    def show_ram_info(self):
        self.update_system_info()
        ram_info = self.system_info["ram"]
        content = (f"Общий объем: {ram_info['total']:.2f} ГБ\n"
                   f"Используемый объем: {ram_info['used']:.2f} ГБ\n"
                   f"Использование: {ram_info['percent']}%")
        self.show_info_window("Информация об оперативной памяти", content)

    def show_disk_info(self):
        self.update_system_info()
        disk_info = self.system_info["disk"]
        content = (f"Общий объем: {disk_info['total']:.2f} ГБ\n"
                   f"Используемый объем: {disk_info['used']:.2f} ГБ\n"
                   f"Использование: {disk_info['percent']}%")
        self.show_info_window("Информация о жестком диске", content)

    def show_gpu_info(self):
        gpus = GPUtil.getGPUs()
        if not gpus:
            content = "Видеокарты не найдены."
        else:
            gpu_info = gpus[0]  # Получаем информацию о первой видеокарте
            content = (f"Название: {gpu_info.name}\n"
                       f"Загрузка: {gpu_info.load * 100:.2f}%\n"
                       f"Память (использовано/всего): {gpu_info.memoryUsed}MB / {gpu_info.memoryTotal}MB\n"
                       f"Температура: {gpu_info.temperature}°C")
        self.show_info_window("Информация о видеокарте", content)

    def show_motherboard_info(self):
        try:
            c = wmi.WMI()
            motherboard_info = c.Win32_BaseBoard()[0]
            content = (f"Производитель: {motherboard_info.Manufacturer}\n"
                       f"Модель: {motherboard_info.Product}\n"
                       f"Версия: {motherboard_info.Version}")
            self.show_info_window("Информация о материнской плате", content)
        except Exception as e:
            self.show_info_window("Ошибка", f"Не удалось получить информацию: {str(e)}")

    def show_info_window(self, title, content):
        info_window = Toplevel(self.root)
        info_window.title(title)
        info_window.geometry("400x200")  # Устанавливаем фиксированный размер
        info_window.resizable(False, False)  # Запрет изменения размера

        label = Label(info_window, text=content, padx=10, pady=10)
        label.pack()

        close_button = Button(info_window, text="Закрыть", command=info_window.destroy, bg='black', fg='white')
        close_button.pack(pady=5)

    def plot_usage(self):
        cpu_details, ram_details, disk_details = get_system_info()
        labels = ['CPU', 'RAM', 'Disk']
        usages = [cpu_details['usage_percent'], ram_details['percent'], disk_details['percent']]

        plt.bar(labels, usages, color=['blue', 'green', 'red'])
        plt.ylabel('Использование (%)')
        plt.title('Использование ресурсов системы')
        plt.ylim(0, 100)
        plt.show()

        # Уведомление о завершении построения графика
        notification.notify(
            title='График построен',
            message='График использования ресурсов системы был успешно построен.',
            app_name='Системная информация'
        )

    def logout(self):
        global current_user
        current_user = None

        logging.info("Пользователь вышел из системы.")
        messagebox.showinfo("Выход", "Вы вышли из системы.")
        self.clear_main_interface()
        self.label.config(text="Выберите действие:")
        self.show_registration_interface()

    def delete_account(self):
        global current_user
        if current_user:
            del users[current_user]
            save_users()
            logging.info(f"Учетная запись {current_user} была удалена.")
            messagebox.showinfo("Успех", f"Учетная запись {current_user} удалена.")
            current_user = None
            self.clear_main_interface()
            self.label.config(text="Выберите действие:")
            self.show_registration_interface()
        else:
            messagebox.showerror("Ошибка", "Вы не вошли в систему.")

    def show_registration_interface(self):
        self.clear_main_interface()

        self.label.config(text="Регистрация или вход:")
        self.login_button = Button(self.main_frame, text="Войти", command=self.login, borderwidth=2, relief="solid", bg='black', fg='white')
        self.login_button.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

        self.register_button = Button(self.main_frame, text="Зарегистрироваться", command=self.register, borderwidth=2, relief="solid", bg='black', fg='white')
        self.register_button.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()