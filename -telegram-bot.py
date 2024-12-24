import logging
import requests
import time
import asyncio
import psutil
import GPUtil
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Вставьте сюда ваш токен
TOKEN = 'Ваш APIKEY Telegram'

# Параметры для Яндекс GPT API
FOLDER_ID = 'Ваш ID'
API_KEY = 'Ваш APIKEY'

# Включаем логирование для отслеживания событий и ошибок
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Устанавливаем уровень логирования на INFO, чтобы видеть общие события
)

# Определите секретное слово
SECRET_WORD = "ADM"

# Список для хранения ID пользователей
user_ids = set()  # Используем множество для уникальности
welcome_message = "Добро пожаловать в бота!"
admin_users = set()  # Множество для хранения ID администраторов

def get_system_components_info():
    # Получаем информацию о процессоре
    cpu_info = psutil.cpu_freq()
    cpu_usage = psutil.cpu_percent()
    cpu_count = psutil.cpu_count(logical=True)

    # Получаем информацию о RAM
    ram = psutil.virtual_memory()

    # Получаем информацию о диске
    disk = psutil.disk_usage('/')

    # Получаем информацию о видеокарте
    gpus = GPUtil.getGPUs()
    gpu_info = gpus[0] if gpus else None

    # Формируем сообщение
    components_info = (
        f"Процессор:\n"
        f"  Загрузка: {cpu_usage}%\n"
        f"  Частота: {cpu_info.current / 1000} ГГц\n"
        f"  Логические ядра: {cpu_count}\n\n"
        f"Оперативная память:\n"
        f"  Всего: {ram.total / (1024 ** 3):.2f} ГБ\n"
        f"  Использовано: {ram.used / (1024 ** 3):.2f} ГБ\n"
        f"  Процент использования: {ram.percent}%\n\n"
        f"Жесткий диск:\n"
        f"  Всего: {disk.total / (1024 ** 3):.2f} ГБ\n"
        f"  Использовано: {disk.used / (1024 ** 3):.2f} ГБ\n"
        f"  Процент использования: {disk.percent}%\n\n"
    )

    if gpu_info:
        components_info += (
            f"Видеокарта:\n"
            f"  Название: {gpu_info.name}\n"
            f"  Загрузка: {gpu_info.load * 100:.2f}%\n"
            f"  Память: {gpu_info.memoryUsed}MB / {gpu_info.memoryTotal}MB\n"
            f"  Температура: {gpu_info.temperature}°C\n"
        )
    else:
        components_info += "Видеокарта: Не найдена.\n"

    return components_info

# Функция для работы с Яндекс GPT (асинхронная версия)
async def yandex_gpt_async(prompt):
    # Формируем тело запроса для API Яндекс GPT
    body = {
        "modelUri": "gpt://b1g5as5ldcaf2l4l7jnb/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,
            "maxTokens": 1000
        },
        ""

        "messages": [

            {
                "role": "system",
                "text": "Ты профессиональный сборщик ПК в России, тебе дают определённую сумму, на которую ты должен собрать ПК. Учитывай баланс между производительностью и стоимостью, а также предназначение компьютера (игры, работа, мультимедиа). Укажи конкретные компоненты, их стоимость и обоснуй свой ответ, также после ответа не пиши ни какое сообщение дальше"
            },

            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    # Отправляем запрос в Яндекс API
    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {API_KEY}",
            "x-folder-id": FOLDER_ID
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
            headers={"Authorization": f"Api-Key {API_KEY}"}
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

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat.id
    user_ids.add(chat_id)  # Добавляем пользователя в базу данных

    # Создаем клавиатуру с кнопками для команд
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="ИИ"),
                KeyboardButton(text="Комплектующие"),
            ],
            [
                KeyboardButton(text="Помощь"),
                KeyboardButton(text="Написать в поддержку"),
            ],
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        'Добро пожаловать в бота сбора обратной связи! Выберите команду:',
        reply_markup=keyboard
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Список доступных команд:\n/start - Начать взаимодействие с ботом\n/help - Получить помощь\n/ask - Задать вопрос ИИ\n/components - Получить информацию о комплектующих")


async def search_components(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Пожалуйста, введите название компонента для поиска.")
        return

    # Пример запроса к API (замените на реальный API)
    response = requests.get(f"https://api.example.com/search?query={query}")

    if response.status_code == 200:
        results = response.json()
        if results:
            message = "Найденные комплектующие:\n"
            for item in results:
                message += f"{item['name']} - {item['price']} руб.\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Комплектующие не найдены.")
    else:
        await update.message.reply_text("Ошибка при обращении к API.")


# Обработчик команды /admin
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.from_user:
        if len(context.args) > 0:
            provided_secret = context.args[0]

            if provided_secret == SECRET_WORD:
                admin_users.add(update.message.from_user.id)
                admin_keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="Управление пользователями"),
                            KeyboardButton(text="Рассылка сообщений"),
                        ],
                        [
                            KeyboardButton(text="Настройки бота"),
                            KeyboardButton(text="Выход из админ-панели"),
                        ],
                    ],
                    resize_keyboard=True
                )
                await update.message.reply_text("Доступ предоставлен! Вы теперь администратор.", reply_markup=admin_keyboard)
            else:
                await update.message.reply_text("Неверное секретное слово. Доступ запрещен.")
        else:
            await update.message.reply_text("Пожалуйста, укажите кодовое слово после команды /admin.")
    else:
        await update.message.reply_text("Не удалось получить информацию о пользователе.")

# Обработчик команды /ask
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = ' '.join(context.args)
    if prompt:
        response = await yandex_gpt_async(prompt)
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Пожалуйста, введите вопрос после команды /ask.")



# Функция для проверки совместимости
async def check_compatibility(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    components = context.args
    if len(components) < 2:
        await update.message.reply_text("Пожалуйста, укажите как минимум два компонента для проверки совместимости.")
        return

    # Пример проверки совместимости (замените на реальную логику)
    compatibility_results = []
    for component in components:
        # Здесь должна быть логика проверки совместимости
        compatibility_results.append(f"{component} совместим.")

    await update.message.reply_text("\n".join(compatibility_results))


# Обработчик команды /components
async def components_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    components_info = "Доступные комплектующие:\n1. Процессоры\n2. Видеокарты\n3. Материнские платы\n4. Оперативная память\n5. Накопители"
    await update.message.reply_text(components_info)

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_ids.add(update.message.chat.id)  # Добавляем пользователя в базу данных
    await update.message.reply_text("Ваше сообщение получено. Используйте команду /ask для взаимодействия с ИИ.")

async def components_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    components_info = get_system_components_info()
    await update.message.reply_text(components_info)

# Основная функция
async def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ask", ask_command))  # Новая команда для вопросов к ИИ
    application.add_handler(CommandHandler("components", components_command))  # Новая команда для информации о комплектующих
    application.add_handler(CommandHandler("check_compatibility", check_compatibility))  # Новая команда для проверки совместимости
    application.add_handler(CommandHandler("search_components", search_components))  # Новая команда для поиска комплектующих
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("components_info", components_info_command))  # Новая команда для информации о комплектующих

    await application.run_polling()

if __name__ == '__main__':
    import nest_asyncio

    nest_asyncio.apply()
    asyncio.run(main())
