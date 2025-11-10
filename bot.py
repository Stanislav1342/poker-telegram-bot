import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_player_name = State()
    admin_add_player = State()

# База данных игроков (имя: рейтинг)
players_rating = {
    "Рунге": 4850,
    "Мария": 4720, 
    "Петр": 4630,
}

# База данных карточек (имя: file_id фото)
player_photo_ids = {}

# Клавиатура главного меню
def get_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🎯 Мой рейтинг"))
    keyboard.add(KeyboardButton(text="🏆 Общий рейтинг"))
    keyboard.add(KeyboardButton(text="📚 Правила покера"))
    keyboard.add(KeyboardButton(text="🎮 Тест по покеру"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Админ клавиатура
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="➕ Добавить игрока"))
    keyboard.add(KeyboardButton(text="📤 Загрузить карточку"))
    keyboard.add(KeyboardButton(text="📊 Статистика"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = (
        "🎯 Добро пожаловать в покер-клуб HeartPipes!\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# Обработка кнопки "Мой рейтинг"
@dp.message(F.text == "🎯 Мой рейтинг")
async def my_rating_handler(message: Message, state: FSMContext):
    await message.answer("Введите ваше игровое имя:")
    await state.set_state(UserStates.waiting_for_player_name)

# Поиск рейтинга по имени + отправка карточки
@dp.message(UserStates.waiting_for_player_name)
async def process_player_name(message: Message, state: FSMContext):
    player_name = message.text.strip()
    
    # Поиск игрока (регистронезависимый)
    found_player = None
    for name in players_rating:
        if name.lower() == player_name.lower():
            found_player = name
            break
    
    if found_player:
        rating = players_rating[found_player]
        position = get_player_position(found_player)
        
        # Пытаемся отправить карточку
        if found_player in player_photo_ids:
            try:
                await message.answer_photo(
                    player_photo_ids[found_player],
                    caption=f"👤 {found_player}\n🏆 Рейтинг: {rating}\n📍 Место: {position}",
                    reply_markup=get_main_keyboard()
                )
            except Exception as e:
                await message.answer(
                    f"👤 {found_player}\n🏆 Рейтинг: {rating}\n📍 Место: {position}\n"
                    f"❌ Ошибка загрузки карточки",
                    reply_markup=get_main_keyboard()
                )
        else:
            await message.answer(
                f"👤 {found_player}\n🏆 Рейтинг: {rating}\n📍 Место: {position}\n"
                f"ℹ️ Карточка игрока готовится",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.answer(
            f"❌ Игрок '{player_name}' не найден.\n"
            "Проверьте имя или обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

# Обработка кнопки "Общий рейтинг"
@dp.message(F.text == "🏆 Общий рейтинг")
async def full_rating_handler(message: Message):
    rating_text = "🏆 Общий рейтинг игроков:\n\n"
    
    sorted_players = sorted(players_rating.items(), key=lambda x: x[1], reverse=True)
    for i, (name, points) in enumerate(sorted_players, 1):
        rating_text += f"{i}. {name}: {points} очков\n"
    
    await message.answer(rating_text, reply_markup=get_main_keyboard())

# Обработка кнопки "Правила покера"
@dp.message(F.text == "📚 Правила покера")
async def rules_handler(message: Message):
    rules_text = """
🃏 ОСНОВНЫЕ ПРАВИЛА ПОКЕРА:

🎯 **Цель игры**: Собрать лучшую комбинацию из 5 карт

📚 **Комбинации (от старшей к младшей)**:

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
    
    # Клавиатура с кнопкой теста после правил
    test_keyboard = ReplyKeyboardBuilder()
    test_keyboard.add(KeyboardButton(text="🎮 Пройти тест по покеру"))
    test_keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    
    await message.answer(rules_text, reply_markup=test_keyboard.as_markup(resize_keyboard=True))

# Обработка кнопки "Тест по покеру"
@dp.message(F.text == "🎮 Тест по покеру")
@dp.message(F.text == "🎮 Пройти тест по покеру")
async def poker_test_handler(message: Message):
    await message.answer(
        "🎮 Тест по покеру в разработке...\n"
        "Скоро здесь появятся вопросы по правилам покера!",
        reply_markup=get_main_keyboard()
    )

# Админ команды
@dp.message(Command("admin"))
async def admin_handler(message: Message):
    # ⚠️ ЗАМЕНИТЕ 123456789 НА ВАШ TELEGRAM ID!
    admin_ids = [123456789]  
    
    if message.from_user.id in admin_ids:
        await message.answer(
            "👑 Панель администратора:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ Доступ запрещен")

# Добавление игрока (админ)
@dp.message(F.text == "➕ Добавить игрока")
async def add_player_handler(message: Message, state: FSMContext):
    admin_ids = [123456789]  # ⚠️ ЗАМЕНИТЕ НА ВАШ ID!
    if message.from_user.id not in admin_ids:
        return
    
    await message.answer(
        "Введите данные игрока в формате:\n"
        "Имя Рейтинг\n\n"
        "Пример: Рунге 4850"
    )
    await state.set_state(UserStates.admin_add_player)

# Обработка добавления игрока
@dp.message(UserStates.admin_add_player)
async def process_add_player(message: Message, state: FSMContext):
    try:
        data = message.text.split()
        if len(data) != 2:
            await message.answer("❌ Неверный формат. Пример: Рунге 4850")
            return
        
        name = data[0]
        rating = int(data[1])
        
        players_rating[name] = rating
        await message.answer(
            f"✅ Игрок добавлен:\n👤 {name}\n🏆 {rating} очков",
            reply_markup=get_admin_keyboard()
        )
        
    except ValueError:
        await message.answer("❌ Рейтинг должен быть числом. Пример: Рунге 4850")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

# Загрузка карточки игрока (админ)
@dp.message(F.text == "📤 Загрузить карточку")
async def upload_card_handler(message: Message):
    admin_ids = [123456789]  # ⚠️ ЗАМЕНИТЕ НА ВАШ ID!
    if message.from_user.id not in admin_ids:
        return
    
    await message.answer(
        "Отправьте карточку игрока как фото с подписью в формате:\n"
        "Имя_игрока\n\n"
        "Пример подписи к фото: Рунге"
    )

# Обработка загруженной карточки
@dp.message(F.photo)
async def process_player_card(message: Message):
    admin_ids = [123456789]  # ⚠️ ЗАМЕНИТЕ НА ВАШ ID!
    if message.from_user.id not in admin_ids:
        return
    
    if not message.caption:
        await message.answer("❌ Добавьте подпись с именем игрока")
        return
    
    player_name = message.caption.strip()
    
    if player_name not in players_rating:
        await message.answer(
            f"❌ Игрок '{player_name}' не найден в базе.\n"
            f"Сначала добавьте игрока через '➕ Добавить игрока'.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    # Сохраняем file_id фото (хранится на серверах Telegram)
    photo = message.photo[-1]
    player_photo_ids[player_name] = photo.file_id
    
    await message.answer(
        f"✅ Карточка для игрока '{player_name}' успешно загружена!\n"
        f"📸 Теперь игроки смогут получать эту карточку.",
        reply_markup=get_admin_keyboard()
    )

# Команда для просмотра статистики (админ)
@dp.message(F.text == "📊 Статистика")
async def stats_handler(message: Message):
    admin_ids = [123456789]  # ⚠️ ЗАМЕНИТЕ НА ВАШ ID!
    if message.from_user.id not in admin_ids:
        return
    
    total_players = len(players_rating)
    players_with_cards = len(player_photo_ids)
    
    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👤 Всего игроков: {total_players}\n"
        f"🖼 Игроков с карточками: {players_with_cards}\n"
        f"📈 Загружено карточек: {players_with_cards}/{total_players}\n\n"
        f"💾 Данные хранятся в оперативной памяти\n"
        f"🔄 При перезапуске бота нужно перезагрузить карточки"
    )
    
    await message.answer(stats_text, reply_markup=get_admin_keyboard())

# Вспомогательная функция для определения позиции
def get_player_position(player_name):
    sorted_players = sorted(players_rating.items(), key=lambda x: x[1], reverse=True)
    for position, (name, _) in enumerate(sorted_players, 1):
        if name == player_name:
            return position
    return None

# Обработка кнопки "Главное меню"
@dp.message(F.text == "🔙 Главное меню")
async def main_menu_handler(message: Message):
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_keyboard())

# Команда для проверки работы бота
@dp.message(Command("status"))
async def status_handler(message: Message):
    status_text = (
        f"🤖 Бот работает нормально\n"
        f"👤 Игроков в базе: {len(players_rating)}\n"
        f"🖼 Загружено карточек: {len(player_photo_ids)}\n"
        f"⚡️ Используется хранение file_id в памяти"
    )
    await message.answer(status_text)

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен на Railway с хранением file_id в памяти!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())