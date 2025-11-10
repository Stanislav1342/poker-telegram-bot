import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден! Проверьте переменные окружения.")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных игроков
players_rating = {
    "Иван": 4850,
    "Мария": 4720, 
    "Петр": 4630,
    "Анна": 4580,
    "Сергей": 4520
}

@dp.message(Command("start"))
async def start_handler(message: Message):
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    await message.answer(
        "🎯 Добро пожаловать в покер-клуб HeartPipes!\n\n"
        "Доступные команды:\n"
        "/rating - общий рейтинг\n"
        "/my_rating - ваш рейтинг\n" 
        "/rules - правила покера"
    )

@dp.message(Command("rating"))
async def rating_handler(message: Message):
    logger.info(f"Пользователь {message.from_user.id} запросил рейтинг")
    rating_text = "🏆 Топ игроков:\n\n"
    for i, (name, points) in enumerate(sorted(players_rating.items(), 
                                            key=lambda x: x[1], reverse=True), 1):
        rating_text += f"{i}. {name}: {points} очков\n"
    
    await message.answer(rating_text)

@dp.message(Command("my_rating"))
async def my_rating_handler(message: Message):
    user_name = message.from_user.first_name
    logger.info(f"Пользователь {user_name} запросил свой рейтинг")
    
    # Поиск пользователя в рейтинге
    for name in players_rating:
        if name.lower() in user_name.lower() or user_name.lower() in name.lower():
            await message.answer(f"{name}, ваш рейтинг: {players_rating[name]} очков")
            return
    
    await message.answer("Вас нет в рейтинге. Обратитесь к администратору.")

@dp.message(Command("rules"))
async def rules_handler(message: Message):
    logger.info(f"Пользователь {message.from_user.id} запросил правила")
    rules = """
🃏 Основные комбинации покера (от старшей к младшей):

1. ♠️ Флеш-рояль - A, K, Q, J, 10 одной масти
2. 📚 Стрит-флеш - 5 карт одной масти по порядку  
3. 🎯 Каре - 4 карты одного достоинства
4. 🏠 Фулл-хаус - 3+2 карты одного достоинства
5. 💧 Флеш - 5 карт одной масти
6. 📏 Стрит - 5 карт по порядку любой масти
7. 🔥 Тройка - 3 карты одного достоинства
8. 🪙 Две пары - 2+2 карты одного достоинства
9. 👑 Пара - 2 карты одного достоинства
10. 📊 Старшая карта
"""
    await message.answer(rules)

@dp.message(F.text)
async def echo_handler(message: Message):
    await message.answer("Используйте команды: /start, /rating, /rules")

async def main():
    logger.info("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())