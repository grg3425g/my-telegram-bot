import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import time

# --- ЖЕСТКАЯ КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAEwnQ4KoRpZA_ie5aal10y6ph1PwaQAnbM")
WEBAPP_URL = "https://my-telegram-bot-6hzj.onrender.com"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- СИСТЕМА АБСОЛЮТНОГО ПЕРЕХВАТА (MIDDLEWARE) ---
@web.middleware
async def force_html_middleware(request, handler):
    # 1. ОБХОД ЗАЩИТЫ БРАУЗЕРА (CORS)
    # Это чинит "вечное сохранение". Мы разрешаем браузеру отправлять данные.
    if request.method == 'OPTIONS':
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, ngrok-skip-browser-warning',
        })
        
    # 2. Если календарь пытается сохранить данные - пропускаем запрос к API
    if request.path.startswith('/api/'):
        return await handler(request)

    # 3. ДЛЯ ВСЕХ ОСТАЛЬНЫХ ЗАПРОСОВ мы принудительно отдаем HTML
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except Exception as e:
        return web.Response(text=f"<h1>Ошибка</h1><p>Файл не найден: {e}</p>", content_type='text/html', status=500)

async def api_add_reminder(request):
    try:
        data = await request.json()
        logging.info(f"Получены данные от календаря: {data}")
        
        # Отправляем подтверждение пользователю прямо в чат!
        chat_id = data.get('chat_id')
        text = data.get('text')
        if chat_id and text:
            await bot.send_message(
                chat_id=chat_id, 
                text=f"✅ <b>Напоминание установлено!</b>\nЯ напомню тебе: <i>{text}</i>",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Ошибка при обработке API: {e}")
        
    # Обязательно возвращаем заголовки CORS в успешном ответе
    return web.json_response(
        {"status": "ok"}, 
        headers={'Access-Control-Allow-Origin': '*'}
    )

async def start_web_server():
    # Подключаем нашего "Вышибалу" (перехватчик) ко всему серверу
    app = web.Application(middlewares=[force_html_middleware])
    app.router.add_post('/api/add_reminder', api_add_reminder)
    
    # Делаем пустой маршрут-заглушку
    async def dummy(request): pass
    app.router.add_get('/', dummy)
    app.router.add_get('/{tail:.*}', dummy)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info("СЕРВЕР УСПЕШНО ЗАПУЩЕН")

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
    # Убрали фразу про перехватчик, вернули красивое приветствие
    await message.answer("Привет! Нажми на кнопку ниже, чтобы установить напоминание:", reply_markup=keyboard)

# --- ЗАПУСК ---
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
