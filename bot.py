import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import time

# --- ЖЕСТКАЯ КОНФИГУРАЦИЯ ---
# Мы больше не доверяем переменным окружения, вписываем ссылку жестко:
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAGeQ8YmMtW78LnNv0_In5NzyHmCDpM1iEY")
WEBAPP_URL = "https://my-telegram-bot-6hzj.onrender.com"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- СИСТЕМА АБСОЛЮТНОГО ПЕРЕХВАТА (MIDDLEWARE) ---
@web.middleware
async def force_html_middleware(request, handler):
    # 1. Если календарь пытается сохранить данные - пропускаем запрос к API
    if request.path == '/api/add_reminder':
        return await handler(request)

    # 2. ДЛЯ ВСЕХ ОСТАЛЬНЫХ ЗАПРОСОВ мы принудительно отдаем HTML
    # Перехватчик срабатывает ДО того, как сервер успеет выдать "Not Found"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except Exception as e:
        return web.Response(text=f"<h1>Ошибка</h1><p>Файл webapp.html не найден на диске: {e}</p>", content_type='text/html', status=500)

async def api_add_reminder(request):
    data = await request.json()
    logging.info(f"Получены данные от календаря: {data}")
    return web.json_response({"status": "ok"})

async def start_web_server():
    # Подключаем нашего "Вышибалу" (перехватчик) ко всему серверу
    app = web.Application(middlewares=[force_html_middleware])
    app.router.add_post('/api/add_reminder', api_add_reminder)
    
    # Делаем пустой маршрут-заглушку, чтобы сервер не ругался при старте. 
    # До него дело всё равно не дойдет, перехватчик сработает раньше.
    async def dummy(request): pass
    app.router.add_get('/', dummy)
    app.router.add_get('/{tail:.*}', dummy)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info("СЕРВЕР-ПЕРЕХВАТЧИК УСПЕШНО ЗАПУЩЕН")

# --- ЛОГИКА БОТА ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Добавляем метку времени, чтобы пробить кэш Telegram
    url = f"{WEBAPP_URL}/?nocache={int(time.time())}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть календарь", 
            web_app=WebAppInfo(url=url) 
        )]
    ])
    await message.answer("Перехватчик установлен! Жми на кнопку:", reply_markup=keyboard)

# --- ЗАПУСК ---
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
