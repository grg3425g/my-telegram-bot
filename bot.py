
import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAFVxguKLNATg0l7BSnc7yWGhkBqCIygDJo")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://my-telegram-bot-6hzj.onrender.com")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ==========================================
# ВЕБ-СЕРВЕР (Для Mini App)
# ==========================================
async def webapp_handler(request):
    """Безотказный способ найти и отдать webapp.html"""
    # Получаем точный путь к папке, где лежит этот скрипт (bot.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    
    if os.path.exists(file_path):
        return web.FileResponse(file_path)
    else:
        return web.Response(text=f"❌ ОШИБКА: Файл webapp.html не найден по пути {file_path}", status=404)

async def ping_handler(request):
    """Для поддержания активности 24/7"""
    return web.Response(text="Bot is awake!")

async def web_server():
    app = web.Application()
    # Отдаем интерфейс и по главной ссылке, и по прямому запросу
    app.router.add_get('/', webapp_handler)
    app.router.add_get('/webapp.html', webapp_handler)
    app.router.add_get('/ping', ping_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"✅ Веб-сервер запущен на порту {port}")

# ==========================================
# ЛОГИКА БОТА
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть календарь", 
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/")
        )]
    ])
    await message.answer("Привет! Нажми на кнопку ниже, чтобы открыть напоминалку:", reply_markup=keyboard)

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    # 1. Принудительно убиваем старые вебхуки (исправляет ошибку Conflict/HTTPS)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 2. Запускаем веб-сервер для отдачи HTML
    asyncio.create_task(web_server())
    
    # 3. Запускаем бота
    logging.info("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())



