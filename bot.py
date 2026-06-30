import asyncio
import logging
import sqlite3
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiohttp import web

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
# Твой токен
BOT_TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAFVxguKLNATg0l7BSnc7yWGhkBqCIygDJo")

# СЮДА НУЖНО ВПИСАТЬ HTTPS-ССЫЛКУ НА ТВОЙ СЕРВЕР (ngrok или Render)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://my-telegram-bot-6hzj.onrender.com")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ==========================================
# БАЗА ДАННЫХ
# ==========================================
def init_db():
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            trigger_time TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def add_reminder(chat_id, user_id, text, trigger_time):
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reminders (chat_id, user_id, text, trigger_time)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, user_id, text, trigger_time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()


def get_due_reminders():
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('SELECT id, chat_id, user_id, text FROM reminders WHERE trigger_time <= ?', (now,))
    reminders = cursor.fetchall()
    conn.close()
    return reminders


def delete_reminder(reminder_id):
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
    conn.commit()
    conn.close()


# ==========================================
# ХЭНДЛЕРЫ БОТА
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Создаем кнопку, открывающую Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ])

    await message.answer(
        "Привет! Я умный бот-напоминалка.\n\n"
        "Нажми на кнопку ниже, чтобы открыть удобный календарь и установить напоминание.",
        reply_markup=keyboard
    )


# ==========================================
# ФОНОВАЯ ЗАДАЧА (Рассылка)
# ==========================================
async def check_reminders_loop(bot: Bot):
    while True:
        try:
            due_reminders = get_due_reminders()
            for r in due_reminders:
                rem_id, chat_id, user_id, text = r

                msg = f"🔔 **НАПОМИНАНИЕ!** 🔔\n\n{text}"
                try:
                    await bot.send_message(chat_id, msg, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Ошибка отправки: {e}")

                delete_reminder(rem_id)
        except Exception as e:
            logging.error(f"Ошибка БД: {e}")

        await asyncio.sleep(10)  # Проверяем каждые 10 секунд


# ==========================================
# ВЕБ-СЕРВЕР (Для Mini App и API)
# ==========================================
async def handle_index(request):
    """Отдает HTML-страницу нашего Mini App"""
    # Вычисляем 100% точный абсолютный путь до файла
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'webapp.html')

    try:
        # Пытаемся прочитать файл вручную и отдать его как HTML
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except FileNotFoundError:
        # Если файла нет, выдаем текст ошибки (status=200, чтобы телеграм не блокировал экран)
        error_msg = f"❌ ОШИБКА: Файл не найден!\n\nБот ищет файл интерфейса по этому пути:\n{file_path}\n\nУбедитесь, что файл существует и называется ровно webapp.html"
        return web.Response(text=error_msg, content_type='text/plain', status=200)


async def handle_api_add_reminder(request):
    """Принимает данные из Mini App и сохраняет в БД"""
    try:
        data = await request.json()

        # Получаем данные от фронтенда
        user_id = data.get('user_id')
        chat_id = data.get('chat_id')
        text = data.get('text')
        timestamp_ms = data.get('timestamp')  # Время в миллисекундах

        if not all([user_id, chat_id, text, timestamp_ms]):
            return web.json_response({"error": "Missing data"}, status=400)

        # Конвертируем JS timestamp в Python datetime
        trigger_time = datetime.fromtimestamp(timestamp_ms / 1000.0)

        # Сохраняем
        add_reminder(chat_id, user_id, text, trigger_time)

        # Сразу отправляем сообщение в чат, что напоминание создано
        await bot.send_message(
            chat_id,
            f"✅ Напоминание «{text}» успешно установлено на {trigger_time.strftime('%d.%m.%Y %H:%M')}!"
        )

        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def web_server():
    app = web.Application()
    # Настраиваем роуты
    app.router.add_get('/', handle_index)
    app.router.add_post('/api/add_reminder', handle_api_add_reminder)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Веб-сервер Mini App запущен на порту {port}")


# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    init_db()
    asyncio.create_task(check_reminders_loop(bot))
    asyncio.create_task(web_server())

    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
