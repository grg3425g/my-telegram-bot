
import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAFVxguKLNATg0l7BSnc7yWGhkBqCIygDJo")
# ВАЖНО: Убедись, что тут нет слеша / на конце
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://my-telegram-bot-6hzj.onrender.com")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- ВЕБ-СЕРВЕР ---
async def webapp_handler(request):
    """
    Эта функция теперь будет отвечать НА ВСЕ запросы.
    Что бы Telegram ни запросил, мы отдадим ему наш HTML файл.
    """
    logging.info(f"Получен запрос по адресу: {request.path}")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    
    if os.path.exists(file_path):
        return web.FileResponse(file_path)
    else:
        logging.error(f"ФАЙЛ НЕ НАЙДЕН НА ДИСКЕ: {file_path}")
        return web.Response(text=f"Критическая ошибка: Файл webapp.html не найден на сервере.", status=404)

async def api_add_reminder(request):
    data = await request.json()
    logging.info(f"Получены данные: {data}")
    return web.json_response({"status": "ok"})

async def start_web_server():
    app = web.Application()
    
    # Сначала добавляем специфичные маршруты
    app.router.add_post('/api/add_reminder', api_add_reminder)
    
    # А ТЕПЕРЬ МАГИЯ: Любой другой путь (/, /webapp.html, /blablabla) 
    # будет обрабатываться функцией webapp_handler
    app.router.add_route('*', '/{tail:.*}', webapp_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Веб-сервер запущен на порту {port}")

# --- ЛОГИКА БОТА ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Теперь мы отправляем Telegram просто на корневой адрес сервера
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть календарь", 
            # Убрали /webapp.html из ссылки, пускай стучится в корень
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/") 
        )]
    ])
    await message.answer("Привет! Нажми на кнопку ниже:", reply_markup=keyboard)

# --- ЗАПУСК ---
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    logging.info("=== БОТ ГОТОВ ===")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

