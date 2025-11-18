import asyncio
import logging
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dotenv import load_dotenv
from database import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для отслеживания уже обработанных запусков
processed_starts = {}

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_player_name = State()
    admin_add_player = State()
    admin_remove_player = State()
    admin_update_rating = State()
    poker_test = State()
    
    # состояния для игр
    admin_create_game_name = State()
    admin_create_game_date = State()
    admin_create_game_players = State()
    admin_create_game_location = State()
    admin_create_game_price = State()
    admin_create_game_host = State()
    admin_broadcast_photo = State()
    admin_remove_player_from_game = State()
    admin_update_game_limit = State()
    
    admin_broadcast_message = State()
    
    user_register_for_game = State()
    user_select_game = State()
    user_cancel_registration = State()

# Загружаем данные из базы при запуске
players_rating = db.get_all_players()
player_photo_ids = db.get_all_cards()

# Данные для теста по покеру
poker_test_questions = [
    {
        "question": "Какая комбинация СТАРШЕ?",
        "options": ["Флеш", "Стрит", "Фулл-хаус", "Каре"],
        "correct": 3,
        "explanation": "Каре > Фулл-хаус > Флеш > Стрит"
    },
    {
        "question": "Сколько карт в комбинации 'Каре'?",
        "options": ["3 карты", "4 карты", "5 карт", "6 карт"],
        "correct": 1,
        "explanation": "Каре - это 4 карты одного достоинства"
    },
    {
        "question": "Что такое 'Флеш'?",
        "options": [
            "5 карт по порядку", 
            "5 карт одной масти", 
            "3 карты одного достоинства", 
            "2 пары"
        ],
        "correct": 1,
        "explanation": "Флеш - 5 карт одной масти"
    },
    {
        "question": "Какая комбинация САМАЯ СТАРШАЯ?",
        "options": ["Флеш-рояль", "Стрит-флеш", "Каре", "Фулл-хаус"],
        "correct": 0,
        "explanation": "Флеш-рояль - самая старшая комбинация"
    },
    {
        "question": "Что такое 'Стрит'?",
        "options": [
            "5 карт разной масти", 
            "5 карт по порядку", 
            "4 карты одного достоинства", 
            "2 карты одного достоинства"
        ],
        "correct": 1,
        "explanation": "Стрит - 5 карт по порядку любой масти"
    }
]

# Переменные для теста
user_test_data = {}

# ★★★ УЛУЧШЕННАЯ ФУНКЦИЯ ДЛЯ НОРМАЛИЗАЦИИ ИМЕН ★★★
def normalize_name(name):
    """Нормализация имени: заменяет ё на е, удаляет лишние пробелы, приводит к нижнему регистру"""
    if not name:
        return ""
    # Заменяем ё на е, приводим к нижнему регистру, удаляем лишние пробелы
    normalized = name.lower().replace('ё', 'е').strip()
    # Удаляем множественные пробелы
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

# ★★★ УЛУЧШЕННАЯ ФУНКЦИЯ ПОИСКА ИГРОКА ★★★
def find_player_by_name(search_name):
    """Умный поиск игрока по имени с учетом разных вариантов написания"""
    if not players_rating:
        return None
    
    search_name = normalize_name(search_name)
    
    # Если поисковый запрос пустой
    if not search_name:
        return None
    
    # Разбиваем поисковый запрос на слова
    search_words = search_name.split()
    
    best_match = None
    best_score = 0
    
    for player_name in players_rating.keys():
        normalized_player = normalize_name(player_name)
        player_words = normalized_player.split()
        
        # Вычисляем score совпадения
        score = 0
        
        # Полное совпадение
        if normalized_player == search_name:
            score = 100
        # Совпадение по всем словам (порядок не важен)
        elif all(any(word in player_word for player_word in player_words) for word in search_words):
            score = 80
        # Совпадение по первому слову
        elif search_words and any(search_words[0] in player_word for player_word in player_words):
            score = 60
        # Частичное совпадение любого слова
        elif any(any(word in player_word for player_word in player_words) for word in search_words):
            score = 40
        
        # Если нашли лучшее совпадение
        if score > best_score:
            best_score = score
            best_match = player_name
    
    # Возвращаем игрока только если score достаточно высокий
    return best_match if best_score >= 40 else None

# Проверка является ли пользователь админом
def is_admin(user_id):
    admin_ids = [1308823467]
    return user_id in admin_ids

# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДНЯ НЕДЕЛИ НА РУССКОМ
def get_russian_weekday(date):
    """Возвращает день недели на русском языке"""
    days = {
        'Monday': 'ПОНЕДЕЛЬНИК',
        'Tuesday': 'ВТОРНИК', 
        'Wednesday': 'СРЕДА',
        'Thursday': 'ЧЕТВЕРГ',
        'Friday': 'ПЯТНИЦА',
        'Saturday': 'СУББОТА',
        'Sunday': 'ВОСКРЕСЕНЬЕ'
    }
    english_day = date.strftime('%A')
    return days.get(english_day, english_day)

# Клавиатура главного меню
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🎯 Мой рейтинг"))
    keyboard.add(KeyboardButton(text="🏆 Общий рейтинг"))
    keyboard.add(KeyboardButton(text="📚 Правила покера"))
    keyboard.add(KeyboardButton(text="🧠 Тест по покеру"))
    keyboard.add(KeyboardButton(text="🎮 Игры"))
    
    if is_admin(user_id):
        keyboard.add(KeyboardButton(text="👑 Админ-панель"))
    
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup(resize_keyboard=True)

# Админ клавиатура
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="➕ Добавить игрока"))
    keyboard.add(KeyboardButton(text="✏️ Изменить рейтинг"))
    keyboard.add(KeyboardButton(text="🗑 Удалить игрока"))
    keyboard.add(KeyboardButton(text="📤 Загрузить карточку"))
    keyboard.add(KeyboardButton(text="🎮 Управление играми"))
    keyboard.add(KeyboardButton(text="🗑 Удалить все игры"))
    keyboard.add(KeyboardButton(text="📋 Списки всех игроков"))
    keyboard.add(KeyboardButton(text="📢 Рассылка"))
    keyboard.add(KeyboardButton(text="📊 Статистика БД"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для игр
def get_games_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="📅 Предстоящие игры"))
    keyboard.add(KeyboardButton(text="🎮 Записаться на игру"))
    keyboard.add(KeyboardButton(text="❌ Отменить запись"))
    keyboard.add(KeyboardButton(text="👥 Мои записи"))
    keyboard.add(KeyboardButton(text="📋 Списки игроков"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Админ-панель для игр
def get_admin_games_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="➕ Создать игру"))
    keyboard.add(KeyboardButton(text="📋 Управление играми"))
    keyboard.add(KeyboardButton(text="🔙 Админ-панель"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для управления конкретной игрой
def get_game_management_keyboard(game_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список игроков", callback_data=f"list_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="✏️ Изменить лимит", callback_data=f"limit_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="🗑 Удалить игрока", callback_data=f"remove_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="❌ Удалить игру", callback_data=f"delete_game_{game_id}"))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Клавиатура для выбора игры
def get_games_selection_keyboard(games, action="select"):
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        keyboard.add(InlineKeyboardButton(
            text=f"{game_name} ({game_date.strftime('%d.%m %H:%M')})",
            callback_data=f"{action}_{game_id}"
        ))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Клавиатура для отмены записи
def get_cancel_registration_keyboard(registrations):
    keyboard = InlineKeyboardBuilder()
    for reg in registrations:
        game_id, game_name, game_date, location, player_name = reg
        keyboard.add(InlineKeyboardButton(
            text=f"{game_name} ({game_date.strftime('%d.%m %H:%M')})",
            callback_data=f"cancelreg_{game_id}"
        ))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Клавиатура для теста
def get_test_keyboard(question_index):
    keyboard = ReplyKeyboardBuilder()
    question = poker_test_questions[question_index]
    for i, option in enumerate(question["options"]):
        keyboard.add(KeyboardButton(text=f"{i+1}. {option}"))
    keyboard.add(KeyboardButton(text="❌ Отменить тест"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

# ========== КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ БАЗОЙ ДАННЫХ ==========

@dp.message(Command("db_init"))
async def db_init_handler(message: Message):
    """Создание таблиц в базе данных"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        db.init_db()
        await message.answer("✅ Таблицы в базе данных созданы/проверены!")
    except Exception as e:
        await message.answer(f"❌ Ошибка создания таблиц: {e}")

@dp.message(Command("db_check"))
@dp.message(F.text == "📊 Статистика БД")
async def db_check_handler(message: Message):
    """Проверка состояния базы данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    try:
        global players_rating, player_photo_ids
        players_rating = db.get_all_players()
        player_photo_ids = db.get_all_cards()
        
        total_players = len(players_rating)
        total_cards = len(player_photo_ids)
        total_bot_users = len(db.get_all_bot_users())
        
        status_text = "🟢 БАЗА ДАННЫХ РАБОТАЕТ\n\n"
        status_text += f"📊 Статистика:\n"
        status_text += f"• Игроков в базе: {total_players}\n"
        status_text += f"• Карточек в базе: {total_cards}\n"
        status_text += f"• Пользователей бота: {total_bot_users}\n"
        
        if players_rating:
            status_text += "\n📋 Топ игроков:\n"
            for i, (name, rating) in enumerate(list(players_rating.items())[:10], 1):
                has_card = "🖼" if name in player_photo_ids else "❌"
                status_text += f"{i}. {name}: {rating} {has_card}\n"
        
        await message.answer(status_text, reply_markup=get_admin_keyboard())
        
    except Exception as e:
        await message.answer(f"🔴 ОШИБКА БАЗЫ ДАННЫХ:\n{str(e)}")

# ========== ОСНОВНЫЕ АДМИН КОМАНДЫ ==========

@dp.message(Command("admin"))
@dp.message(F.text == "👑 Админ-панель")
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    await message.answer("👑 Панель администратора:", reply_markup=get_admin_keyboard())

# Добавление игрока (админ)
@dp.message(F.text == "➕ Добавить игрока")
async def add_player_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "Введите данные игрока в формате:\n"
        "Имя Фамилия Рейтинг\n\n"
        "Пример: Иван Рунге 4.4\n"
        "Или: Стас 4.2\n"
        "Рейтинг по 5-балльной шкале"
    )
    await state.set_state(UserStates.admin_add_player)

@dp.message(UserStates.admin_add_player)
async def process_add_player(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Неверный формат. Пример: Иван Рунге 4.4")
            return
        
        rating_str = parts[-1].replace(',', '.')
        player_name = ' '.join(parts[:-1])
        
        rating = float(rating_str)
        
        if rating < 0 or rating > 5:
            await message.answer("❌ Рейтинг должен быть от 0 до 5")
            return
        
        if db.add_player(player_name, rating):
            players_rating[player_name] = rating
            await message.answer(
                f"✅ Игрок добавлен:\n👤 {player_name}\n⭐️ Рейтинг: {rating}",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer("❌ Ошибка при добавлении игрока в базу")
        
    except ValueError:
        await message.answer("❌ Рейтинг должен быть числом. Пример: Иван Рунге 4.4")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

# ========== ИСПРАВЛЕННЫЙ ОБРАБОТЧИК ДЛЯ "МОЙ РЕЙТИНГ" ==========

@dp.message(F.text == "🎯 Мой рейтинг")
async def my_rating_handler(message: Message, state: FSMContext):
    if not players_rating:
        await message.answer("📋 В базе пока нет игроков")
        return
    
    await message.answer("Введите ваше игровое имя:")
    await state.set_state(UserStates.waiting_for_player_name)

@dp.message(UserStates.waiting_for_player_name)
async def process_player_name(message: Message, state: FSMContext):
    """Обработка ввода имени игрока для просмотра рейтинга"""
    try:
        player_name = message.text.strip()
        
        if not player_name:
            await message.answer("❌ Введите имя игрока")
            return
        
        # ★★★ ИСПОЛЬЗУЕМ УМНЫЙ ПОИСК ★★★
        found_player = find_player_by_name(player_name)
        
        if not found_player:
            await message.answer(
                f"❌ Игрок '{player_name}' не найден в базе.\n\n"
                f"📋 Доступные игроки:\n" + 
                "\n".join([f"• {name}" for name in players_rating.keys()]) +
                f"\n\n💡 Попробуйте ввести имя частично",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
            await state.clear()
            return
        
        player_rating = players_rating[found_player]
        
        # Получаем позицию в рейтинге
        position = get_player_position(found_player)
        
        # Получаем карточку игрока если есть
        player_card = db.get_player_card(found_player)
        
                # Формируем текст ответа
        rating_text = (
            f"👤 {found_player}\n"
            f"⭐️ Рейтинг: {player_rating}\n"
            f"🏆 Место в рейтинге: {position}\n"
        )
        
        # Отправляем карточку если есть, иначе просто текст
        if player_card:
            try:
                await message.answer_photo(
                    player_card,
                    caption=rating_text,
                    reply_markup=get_main_keyboard(message.from_user.id)
                )
            except Exception as e:
                logging.error(f"❌ Ошибка отправки карточки: {e}")
                await message.answer(
                    f"{rating_text}\n"
                    f"⚠️ Карточка временно недоступна",
                    reply_markup=get_main_keyboard(message.from_user.id)
                )
        else:
            await message.answer(
                f"{rating_text}\n"
                f"ℹ️ Карточка игрока готовится",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки имени игрока: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске игрока",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        await state.clear()

def get_player_position(player_name):
    """Определение позиции игрока в рейтинге"""
    try:
        sorted_players = sorted(players_rating.items(), key=lambda x: x[1], reverse=True)
        for position, (name, _) in enumerate(sorted_players, 1):
            if name == player_name:
                return position
        return None
    except Exception as e:
        logging.error(f"❌ Ошибка определения позиции: {e}")
        return None

# ========== ИСПРАВЛЕННЫЙ ОБРАБОТЧИК ДЛЯ ЗАПИСИ НА ИГРУ ==========

@dp.message(F.text == "🎮 Записаться на игру")
async def register_game_handler(message: Message, state: FSMContext):
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Пока нет игр для записи")
        return
    
    await message.answer(
        "🎮 Выберите игру для записи:",
        reply_markup=get_games_selection_keyboard(games, "register")
    )
    await state.set_state(UserStates.user_select_game)

@dp.callback_query(F.data.startswith("register_"))
async def process_game_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        # Проверяем есть ли свободные места
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        max_players = game[4]
        
        if current_players >= max_players:
            await callback.message.answer(
                f"❌ На эту игру уже набрано максимальное количество игроков ({max_players})",
                reply_markup=get_games_keyboard()
            )
            await callback.answer()
            return
        
        await state.update_data(game_id=game_id)
        
        if not players_rating:
            await callback.message.answer(
                "❌ В базе нет игроков. Обратитесь к администратору.",
                reply_markup=get_games_keyboard()
            )
            await callback.answer()
            return
        
        players_list = "\n".join([f"• {name}" for name in players_rating.keys()])
        
        await callback.message.answer(
            f"🎮 Запись на игру:\n\n"
            f"🌃 {get_russian_weekday(game[2])} {game[2].strftime('%d.%m')}\n"
            f"{game[1]} 🃏\n"
            f"{game[6]}\n"
            f"🕢 {game[2].strftime('%H:%M')}-{game[9] or '22:00'}\n"
            f"💸 {int(game[5])} рублей\n"
            f"🎤 Ведущий: {game[8] or 'Капоне'}\n"
            f"👥 Свободно мест: {max_players - current_players}/{max_players}\n\n"
            f"👤 Введите ваш игровой никнейм:\n\n"
            f"📋 Доступные игроки:\n{players_list}\n\n"
            f"💡 Можно ввести имя частично или в любом регистре",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отменить запись")]],
                resize_keyboard=True
            )
        )
        await state.set_state(UserStates.user_register_for_game)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка выбора игры")

@dp.message(UserStates.user_register_for_game)
async def process_game_registration_name(message: Message, state: FSMContext):
    """Обработка имени игрока для записи на игру"""
    try:
        if message.text == "❌ Отменить запись":
            await message.answer("Запись отменена", reply_markup=get_games_keyboard())
            await state.clear()
            return
        
        player_name = message.text.strip()
        data = await state.get_data()
        game_id = data.get('game_id')
        
        if not game_id:
            await message.answer("❌ Ошибка: игра не найдена")
            await state.clear()
            return
        
        # ★★★ ИСПОЛЬЗУЕМ УМНЫЙ ПОИСК ★★★
        found_player = find_player_by_name(player_name)
        
        if not found_player:
            await message.answer(
                f"❌ Игрок '{player_name}' не найден в базе.\n\n"
                f"📞 Обратитесь к администратору для добавления в базу: @babzuni777",
                reply_markup=get_games_keyboard()
            )
            await state.clear()
            return
        
        # Записываем игрока на игру
        success, result_message = db.register_player_for_game(
            game_id, found_player, message.from_user.id
        )
        
        if success:
            # Получаем актуальную информацию об игре
            game = db.get_game_by_id(game_id)
            registrations = db.get_game_registrations(game_id)
            current_players = len([r for r in registrations if r[1] == 'registered'])
            
            success_text = (
                f"✅ {result_message}\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
                f"👤 Ваш ник: {found_player}\n"
                f"👥 Теперь игроков: {current_players}/{game[4]}"
            )
            await message.answer(success_text, reply_markup=get_games_keyboard())
        else:
            await message.answer(result_message, reply_markup=get_games_keyboard())
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"❌ Ошибка записи на игру: {e}")
        await message.answer(
            "❌ Произошла ошибка при записи на игру",
            reply_markup=get_games_keyboard()
        )
        await state.clear()

# ========== ОСТАЛЬНЫЕ ФУНКЦИИ (без изменений) ==========

@dp.message(Command("start"))
async def start_handler(message: Message, command: CommandObject):
    if command.args:
        return
    
    user_id = message.from_user.id
    current_time = message.date.timestamp()
    
    if user_id in processed_starts:
        last_time = processed_starts[user_id]
        if current_time - last_time < 3:
            return
    
    processed_starts[user_id] = current_time
    
    db.save_bot_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    welcome_text = "♥️♣️ Добро пожаловать в MagnumPoker ♦️♠️\n\nВыберите действие:"
    await message.answer(welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "🏆 Общий рейтинг")
async def full_rating_handler(message: Message):
    if not players_rating:
        await message.answer("📋 В базе пока нет игроков")
        return
    
    rating_text = "🏆 Общий рейтинг игроков:\n\n"
    sorted_players = sorted(players_rating.items(), key=lambda x: x[1], reverse=True)
    for i, (name, points) in enumerate(sorted_players, 1):
        rating_text += f"{i}. {name}: {points}\n"
    
    await message.answer(rating_text, reply_markup=get_main_keyboard(message.from_user.id))

# ... остальные обработчики без изменений ...

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен с улучшенной системой поиска игроков!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())