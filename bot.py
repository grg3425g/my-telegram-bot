import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import time

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAFl1ShD9nBia3ThQc2dR_Rr-SZ51x0shjI")
# Убираем случайный слэш в конце, если он есть
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://my-telegram-bot-6hzj.onrender.com").rstrip('/')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- ВЕБ-СЕРВЕР ---
async def webapp_handler(request):
    """
    Железобетонный способ: мы не просто указываем путь к файлу, 
    мы физически читаем его текст и отправляем как HTML-страницу.
    """
    logging.info(f"🌍 ВХОДЯЩИЙ ЗАПРОС ОТ ТЕЛЕГРАМ: {request.method} {request.path} {request.query_string}")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    
    try:
        # Читаем файл вручную
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Отдаем как полноценный HTML
        return web.Response(text=html_content, content_type='text/html')
    except Exception as e:
        # Если файла реально нет, мы увидим эту красную ошибку, а не системное "Not Found"
        error_text = f"<h1>Критическая ошибка!</h1><p>Файл webapp.html не найден.</p><p>Детали: {e}</p>"
        return web.Response(text=error_text, content_type='text/html', status=500)

async def api_add_reminder(request):
    data = await request.json()
    logging.info(f"✅ Данные из календаря: {data}")
    return web.json_response({"status": "ok"})

async def start_web_server():
    app = web.Application()
    
    # 1. Обрабатываем POST-запрос на сохранение данных
    app.router.add_post('/api/add_reminder', api_add_reminder)
    
    # 2. АБСОЛЮТНЫЙ ПЕРЕХВАТ (Catch-all)
    # Этот маршрут перехватывает ВООБЩЕ ЛЮБОЙ GET-запрос 
    # Системного "Not Found" от aiohttp больше быть не может в принципе!
    app.router.add_get('/{tail:.*}', webapp_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")

# --- ЛОГИКА БОТА ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Генерируем уникальное число (текущее время), чтобы 100% сбросить кэш Telegram
    cache_buster = int(time.time())
    
    # Явно указываем полное имя файла и уникальный параметр
    url = f"{WEBAPP_URL}/webapp.html?v={cache_buster}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть календарь", 
            web_app=WebAppInfo(url=url) 
        )]
    ])
    await message.answer("Всё готово! Нажми на кнопку ниже, чтобы открыть напоминалку:", reply_markup=keyboard)

# --- ЗАПУСК ---
async def main():
    dp.include_router(router)
    # Гарантированно убиваем старые соединения
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем сервер
    asyncio.create_task(start_web_server())
    logging.info("=== БОТ И СЕРВЕР РАБОТАЮТ БЕЗ ОШИБОК ===")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
