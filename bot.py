import asyncio
import logging
import os
import json
from urllib.parse import parse_qs
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import time

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN", "8769283823:AAGRVcxSdcGHV70nnogOAjw_a-A4xXRRDjk")
WEBAPP_URL = "https://my-telegram-bot-6hzj.onrender.com"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- ПЕРЕХВАТЧИК (MIDDLEWARE) ---
@web.middleware
async def force_html_middleware(request, handler):
    # 1. ОБХОД CORS (разрешаем браузеру отправлять данные)
    if request.method == 'OPTIONS':
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': '*',
        })
        
    # 2. ЕСЛИ ЭТО СОХРАНЕНИЕ ДАННЫХ - пропускаем к API
    if request.path.startswith('/api/'):
        try:
            response = await handler(request)
            # ОБЯЗАТЕЛЬНО добавляем CORS к успешному ответу, чтобы кнопка не висла
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            logging.error(f"Ошибка API: {e}")
            return web.json_response({"status": "error"}, headers={'Access-Control-Allow-Origin': '*'})

    # 3. ВСЕ ОСТАЛЬНЫЕ ЗАПРОСЫ -> отдаем твой красивый HTML
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'webapp.html')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except Exception as e:
        return web.Response(text=f"Ошибка: {e}", content_type='text/html', status=500)

# --- ПРИЕМ ДАННЫХ ИЗ КАЛЕНДАРЯ ---
async def api_add_reminder(request):
    try:
        raw_data = await request.text()
        logging.info(f"📥 Сырые данные от приложения: {raw_data}")
        
        # Умный парсинг (понимает и JSON, и обычные формы)
        try:
            data = json.loads(raw_data)
        except:
            parsed = parse_qs(raw_data)
            data = {k: v[0] for k, v in parsed.items()}
            
        # Пытаемся найти ID пользователя и текст
        chat_id = data.get('chat_id')
        # Ищем текст по разным возможным названиям переменных из твоего HTML
        text = data.get('text') or data.get('title') or data.get('task') or data.get('message') or 'Без названия'
        
        if chat_id:
            await bot.send_message(
                chat_id=chat_id, 
                text=f"✅ <b>Напоминание установлено!</b>\nЗадача: <i>{text}</i>",
                parse_mode="HTML"
            )
        else:
            logging.warning("⚠️ В данных нет chat_id! Бот не знает, кому отвечать в Телеграм.")
            
    except Exception as e:
        logging.error(f"❌ Ошибка в api_add_reminder: {e}")
        
    return web.json_response({"status": "ok"})

async def start_web_server():
    app = web.Application(middlewares=[force_html_middleware])
    app.router.add_post('/api/add_reminder', api_add_reminder)
    
    # Заглушка, чтобы сервер запустился без ошибок
    async def dummy(request): pass
    app.router.add_get('/', dummy)
    app.router.add_get('/{tail:.*}', dummy)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ЛОГИКА БОТА ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    url = f"{WEBAPP_URL}/?nocache={int(time.time())}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Открыть календарь", web_app=WebAppInfo(url=url))]
    ])
    await message.answer("Привет! Нажми на кнопку ниже, чтобы установить напоминание:", reply_markup=keyboard)

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
