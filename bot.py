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
from aiogram.filters import StateFilter 
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).parent

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для отслеживания уже обработанных запусков
processed_starts = {}

players_rating = {}

BOT_COMMANDS = [
    "🏆 Рейтинг покер", "🔫 Рейтинг мафия", "📚 Правила покера", "📜 Правила мафии", "🎮 Игры",
    "📅 Предстоящие игры", "🎮 Записаться на игру", "❌ Отменить запись", "👥 Мои записи", "📋 Списки игроков",
    "🔙 Главное меню", "👑 Админ-панель", "➕ Добавить игрока", "🗑 Удалить игрока",
    "🏆 Управление рейтингами", "🎮 Управление играми", "🗑 Удалить все игры", "📋 Списки всех игроков",
    "📢 Рассылка", "📊 Статистика БД", "➕ Создать игру", "📋 Редактировать игры", "🔙 Админ-панель",
    "🔙 Назад к играм", "/start"
]

# Состояния для FSM
class UserStates(StatesGroup):
    # состояния для игроков
    admin_add_player = State()
    admin_remove_player = State()
    
    # состояния для редактирования игр
    admin_update_game_host = State()
    admin_update_game_time = State()
    admin_update_game_date = State()
    admin_update_game_location = State()
    admin_update_game_limit = State()
    admin_remove_player_from_game = State()
    
    # состояния для создания игры
    admin_create_game_name = State()
    admin_create_game_date = State()
    admin_create_game_players = State()
    admin_create_game_location = State()
    admin_create_game_price = State()
    admin_create_game_host = State()
    admin_add_game_poster = State()
    
    # состояния для рассылки
    admin_broadcast_message = State()
    
    # состояние для записи пользователя
    user_register_for_game = State()
    
    # состояния для рейтингов
    admin_add_poker_rating = State()
    admin_add_mafia_city_rating = State()
    admin_add_mafia_cartel_rating = State()

# Загружаем данные из базы при запуске
players_rating = db.get_all_players()

# Функция для нормализации имен (е/ё)
def normalize_name(name):
    """Нормализация имени: заменяет ё на е и приводит к нижнему регистру"""
    return name.lower().replace('ё', 'е')

def normalize_name_for_comparison(name):
    """Нормализация имени для сравнения: заменяет ё на е, нижний регистр, убирает пробелы"""
    return name.lower().replace('ё', 'е').strip()

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
    keyboard.add(KeyboardButton(text="🏆 Рейтинг покер"))
    keyboard.add(KeyboardButton(text="🔫 Рейтинг мафия"))
    keyboard.add(KeyboardButton(text="📚 Правила покера"))
    keyboard.add(KeyboardButton(text="📜 Правила мафии"))
    keyboard.add(KeyboardButton(text="🎮 Игры"))
    
    if is_admin(user_id):
        keyboard.add(KeyboardButton(text="👑 Админ-панель"))
    
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для выбора типа мафии (правила)
def get_mafia_rules_selection_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🌆 Городская мафия"))
    keyboard.add(KeyboardButton(text="🃏 Мафия Картель"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Админ клавиатура
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🏆 Управление рейтингами"))
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
    keyboard.add(KeyboardButton(text="📋 Редактировать игры"))
    keyboard.add(KeyboardButton(text="🔙 Админ-панель"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для управления конкретной игрой
# Расширяем клавиатуру управления игрой
def get_game_management_keyboard(game_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список игроков", callback_data=f"list_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="✏️ Изменить лимит", callback_data=f"limit_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="🗑 Удалить игрока", callback_data=f"remove_{game_id}"))
    
    # ★★★ НОВЫЕ КНОПКИ ★★★
    keyboard.add(InlineKeyboardButton(text="🎤 Изменить ведущего", callback_data=f"host_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="🕒 Изменить время", callback_data=f"time_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="📅 Изменить дату", callback_data=f"date_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="📍 Изменить адрес", callback_data=f"location_{game_id}"))
    
    keyboard.add(InlineKeyboardButton(text="❌ Удалить игру", callback_data=f"delete_game_{game_id}"))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Клавиатура для выбора игры
def get_games_selection_keyboard(games, action="select"):
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        # ★★★ УНИКАЛЬНЫЕ СОКРАЩЕНИЯ ★★★
        short_name = get_unique_short_name(game_name)
        
        button_text = f"{short_name} | {game_date.strftime('%d.%m %H:%M')}-{end_time} | {current_players}/{max_players}"
        
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"{action}_{game_id}"
        ))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_unique_short_name(full_name):
    """Уникальные сокращения для наших игр"""
    if "MagnumPokerLeague" in full_name:
        return "Poker"
    elif "Мафия картель" in full_name:
        return "Картель" 
    elif "Городская мафия" in full_name:
        return "Город"
    elif "Мафия" in full_name and "картель" not in full_name:
        return "Мафия"
    else:
        return full_name[:8] + "…"

# Обновленная функция для клавиатуры отмены записи
def get_cancel_registration_keyboard(registrations):
    keyboard = InlineKeyboardBuilder()
    for reg in registrations:
        game_id, game_name, game_date, location, player_name = reg
        
        game = db.get_game_by_id(game_id)
        if game:
            end_time = game[9]
        else:
            end_time = '22:00'
        
        short_name = get_unique_short_name(game_name)
        
        button_text = f"{short_name} | {game_date.strftime('%d.%m %H:%M')}-{end_time} | {player_name}"
        
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"cancelreg_{game_id}_{player_name.replace(' ', '_')}"
        ))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_mafia_rating_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🌆 Рейтинг Городской мафии"))
    keyboard.add(KeyboardButton(text="🃏 Рейтинг Мафии картель"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

def get_admin_ratings_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🏆 Добавить рейтинг покер"))
    keyboard.add(KeyboardButton(text="🗑 Удалить рейтинг покер"))
    keyboard.add(KeyboardButton(text="🔫 Добавить рейтинг мафия"))
    keyboard.add(KeyboardButton(text="✂️ Удалить рейтинг мафия"))
    keyboard.add(KeyboardButton(text="🔙 Админ-панель"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Добавь эту функцию в раздел с другими клавиатурами
def get_cancel_action_keyboard():
    """Клавиатура для отмены действия (процесса записи)"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🚫 Отменить действие"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

def get_cancel_creation_keyboard():
    """Клавиатура для отмены создания игры"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="❌ Отменить создание"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для отмены редактирования
def get_cancel_edit_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="❌ Отменить редактирование"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

def get_finish_adding_keyboard():
    """Клавиатура для завершения добавления рейтингов"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="✅ Афиш больше нет"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

@dp.callback_query(F.data.startswith("cancelreg_"))
async def process_cancel_registration(callback: types.CallbackQuery):
    try:
        # Получаем game_id и player_name из callback_data
        parts = callback.data.split('_')
        game_id = int(parts[1])
        player_name = '_'.join(parts[2:])  # Восстанавливаем ник (может содержать _)
        player_name = player_name.replace('_', ' ')  # Заменяем _ обратно на пробелы
        
        user_id = callback.from_user.id
        
        if db.remove_player_from_game(game_id, player_name):
            game = db.get_game_by_id(game_id)
            await callback.message.answer(
                f"✅ Запись на игру отменена!\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
                f"👤 Игрок: {player_name}",
                reply_markup=get_games_keyboard()
            )
        else:
            await callback.message.answer("❌ Ошибка при отмене записи")
        
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при отмене записи")

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

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
    
    welcome_text = "♥️♣️ Добро пожаловать в Club Magnum ♦️♠️\n\nВыберите действие:"
    await message.answer(welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "📚 Правила покера")
async def rules_handler(message: Message):
    rules_text = """🎯 <b>Краткие правила покера (Техасский Холдем)</b> 🎯

<b>Цель игры:</b> собрать наилучшую покерную комбинацию из 5 карт, используя свои 2 карты и 5 общих карт на столе.

<b>Как играть:</b>
1. Игроки получают по 2 карты (в закрытую)
2. На стол выкладываются 5 общих карт в 3 этапа:
   • Флоп (3 карты)
   • Терн (1 карта) 
   • Ривер (1 карта)
3. После каждого этапа - торги
4. В финале - вскрытие карт и определение победителя

<b>Важно:</b> Вы можете использовать:
• Только свои 2 карты
• Только карты со стола  
• Любую комбинацию своих карт и карт со стола
"""
    
    try:
        photo_url = "https://i.pinimg.com/originals/d6/42/a4/d642a4866de6863efcb5b1c60017d562.png"
        await message.answer_photo(
            photo_url,
            caption=rules_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    except Exception:
        await message.answer(rules_text, parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "📜 Правила мафии")
async def mafia_rules_handler(message: Message):
    await message.answer(
        "🎭 Выберите тип мафии для просмотра правил:",
        reply_markup=get_mafia_rules_selection_keyboard()
    )

@dp.message(F.text == "🌆 Городская мафия")
async def mafia_city_rules_handler(message: Message):
    """Отправка файла с правилами Городской мафии"""
    try:
        # Пробуем разные пути
        possible_paths = [
            BASE_DIR / "rules" / "Правила Magnum&WRM.docx",
            BASE_DIR / "tg bot" / "rules" / "Правила Magnum&WRM.docx",
            Path("/app/rules/Правила Magnum&WRM.docx"),
            Path("rules/Правила Magnum&WRM.docx"),
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists():
                file_path = path
                logging.info(f"✅ Файл найден по пути: {path}")
                break
        
        if not file_path:
            raise FileNotFoundError("Файл не найден ни по одному из путей")
        
        # Отправляем документ
        await message.answer_document(
            types.FSInputFile(file_path),
            caption="📚 <b>Правила Городской мафии</b>\n\n"
                   "Здесь содержатся полные правила игры в Городскую мафию.",
            parse_mode="HTML",
            reply_markup=get_mafia_rules_selection_keyboard()
        )
        
    except FileNotFoundError:
        logging.error("❌ Файл с правилами Городской мафии не найден")
        await message.answer(
            "❌ Файл с правилами Городской мафии временно недоступен.\n"
            "Пожалуйста, обратитесь к администратору.",
            reply_markup=get_mafia_rules_selection_keyboard()
        )
    except Exception as e:
        logging.error(f"❌ Ошибка отправки файла Городской мафии: {e}")
        await message.answer(
            f"❌ Произошла ошибка при отправке файла.\nОшибка: {str(e)}",
            reply_markup=get_mafia_rules_selection_keyboard()
        )

@dp.message(F.text == "🃏 Мафия Картель")
async def mafia_cartel_rules_handler(message: Message):
    """Отправка файла с правилами Мафии Картель"""
    try:
        # Пробуем разные пути
        possible_paths = [
            BASE_DIR / "rules" / "Правила игры.docx",
            BASE_DIR / "tg bot" / "rules" / "Правила игры.docx",
            Path("/app/rules/Правила игры.docx"),
            Path("rules/Правила игры.docx"),
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists():
                file_path = path
                logging.info(f"✅ Файл найден по пути: {path}")
                break
        
        if not file_path:
            raise FileNotFoundError("Файл не найден ни по одному из путей")
        
        # Отправляем документ
        await message.answer_document(
            types.FSInputFile(file_path),
            caption="📚 <b>Правила Мафии Картель</b>\n\n"
                   "Здесь содержатся полные правила игры в Мафию Картель.",
            parse_mode="HTML",
            reply_markup=get_mafia_rules_selection_keyboard()
        )
        
    except FileNotFoundError:
        logging.error("❌ Файл с правилами Мафии Картель не найден")
        await message.answer(
            "❌ Файл с правилами Мафии Картель временно недоступен.\n"
            "Пожалуйста, обратитесь к администратору.",
            reply_markup=get_mafia_rules_selection_keyboard()
        )
    except Exception as e:
        logging.error(f"❌ Ошибка отправки файла Мафии Картель: {e}")
        await message.answer(
            f"❌ Произошла ошибка при отправке файла.\nОшибка: {str(e)}",
            reply_markup=get_mafia_rules_selection_keyboard()
        )

@dp.message(F.text == "🏆 Рейтинг покер")
async def poker_rating_handler(message: Message):
    poker_ratings = db.get_poker_ratings()
    
    if not poker_ratings:
        await message.answer("🏆 Рейтинг покера пока пуст\nАдминистратор еще не добавил рейтинг", 
                           reply_markup=get_main_keyboard(message.from_user.id))
        return
    
    # Создаем медиагруппу для отправки всех фото одним сообщением
    media_group = []
    
    for file_id in poker_ratings.values():  # Используем только file_id, игнорируем player_name
        media_group.append(types.InputMediaPhoto(
            media=file_id,
            caption=""  # Пустая подпись
        ))
    
    # Отправляем медиагруппу (максимум 10 фото за раз в Telegram API)
    try:
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i+10]
            await message.answer_media_group(chunk)
            
    except Exception as e:
        logging.error(f"❌ Ошибка отправки медиагруппы покера: {e}")
        # Если медиагруппа не работает, отправляем по одному
        for file_id in poker_ratings.values():
            try:
                await message.answer_photo(file_id)
                await asyncio.sleep(0.2)
            except Exception as e2:
                logging.error(f"❌ Ошибка отправки фото рейтинга: {e2}")
    
    # ★★★ ДОБАВЛЯЕМ СООБЩЕНИЕ ПОСЛЕ ФОТО ★★★
    await message.answer(
        "🏆 <b>Рейтинг MagnumPokerLeague</b>\n\n" ,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id)
    )
    

@dp.message(F.text == "🔫 Рейтинг мафия")
async def mafia_rating_handler(message: Message):
    await message.answer("🔫 Выберите тип мафии для просмотра рейтинга:", 
                       reply_markup=get_mafia_rating_keyboard())

# Аналогично обновляем для мафии:
@dp.message(F.text == "🌆 Рейтинг Городской мафии")
async def mafia_city_rating_handler(message: Message):
    mafia_city_ratings = db.get_mafia_city_ratings()
    
    if not mafia_city_ratings:  
        await message.answer("🌆 Рейтинг Городская мафия пока пуст\nАдминистратор еще не добавил рейтинг", 
                           reply_markup=get_main_keyboard(message.from_user.id))
        return
    
    # Создаем медиагруппу
    media_group = []
    
    for file_id in mafia_city_ratings.values():
        media_group.append(types.InputMediaPhoto(
            media=file_id,
            caption=""  # Пустая подпись
        ))
    
    try:
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i+10]
            await message.answer_media_group(chunk)
            
    except Exception as e:
        logging.error(f"❌ Ошибка отправки медиагруппы мафии: {e}")
        for file_id in mafia_city_ratings.values():
            try:
                await message.answer_photo(file_id)
                await asyncio.sleep(0.2)
            except Exception as e2:
                logging.error(f"❌ Ошибка отправки фото рейтинга: {e2}")
    
    # Возвращаем клавиатуру после отправки
    await message.answer(
        "🌆 <b>Рейтинг Городская Мафия</b>\n\n" ,
        parse_mode="HTML",
        reply_markup=get_mafia_rating_keyboard()
        )
    
    
@dp.message(F.text == "🃏 Рейтинг Мафии картель")
async def mafia_cartel_rating_handler(message: Message):
    mafia_cartel_ratings = db.get_mafia_cartel_ratings()
    
    if not mafia_cartel_ratings:
        await message.answer("🃏 Рейтинг Мафии Картель пока пуст\nАдминистратор еще не добавил рейтинг", 
                           reply_markup=get_main_keyboard(message.from_user.id))
        return
    
    # Создаем медиагруппу
    media_group = []
    
    for file_id in mafia_cartel_ratings.values():
        media_group.append(types.InputMediaPhoto(
            media=file_id,
            caption=""  # Пустая подпись
        ))
    
    try:
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i+10]
            await message.answer_media_group(chunk)
            
    except Exception as e:
        logging.error(f"❌ Ошибка отправки медиагруппы мафии картель: {e}")
        for file_id in mafia_cartel_ratings.values():
            try:
                await message.answer_photo(file_id)
                await asyncio.sleep(0.2)
            except Exception as e2:
                logging.error(f"❌ Ошибка отправки фото рейтинга: {e2}")
    
    # Возвращаем клавиатуру после отправки
        await message.answer(
        "🃏 <b>Рейтинг Мафия Картель</b>\n\n" ,
        parse_mode="HTML",
        reply_markup=get_mafia_rating_keyboard()
        )

@dp.message(F.text == "🔙 Управление рейтингами")
async def back_to_ratings_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("🏆 Управление рейтингами:", reply_markup=get_admin_ratings_keyboard())

@dp.message(F.text == "🎮 Игры")
async def games_handler(message: Message):
    await message.answer("🎮 Управление играми и записями:", reply_markup=get_games_keyboard())

@dp.message(F.text == "📅 Предстоящие игры")
async def upcoming_games_handler(message: Message):
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 На этой неделе пока нет запланированных игр")
        return
    
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        games_text = f"🌃 {get_russian_weekday(game_date)} {game_date.strftime('%d.%m')}\n"
        games_text += f"{game_name}\n"
        games_text += f"{location}\n"
        games_text += f"🕢 {game_date.strftime('%H:%M')}-{end_time or '22:00'}\n"
        games_text += f"💸 {int(buy_in)} рублей\n"
        games_text += f"🎤 Ведущий: {host or 'Капоне'}\n"
        games_text += f"👥 Игроков: {current_players}/{max_players}\n"
        
        poster_file_id = db.get_game_poster(game_id)
        
        if poster_file_id:
            try:
                await message.answer_photo(
                    poster_file_id,
                    caption=games_text
                )
            except Exception as e:
                logging.error(f"❌ Ошибка отправки афиши для игры {game_id}: {e}")
                await message.answer(games_text)
        else:
            await message.answer(games_text)
        
        await asyncio.sleep(0.1)  # Пауза между сообщениями

def get_games_selection_reply_keyboard(games):
    """Reply-клавиатура для выбора игр с полной информацией"""
    keyboard = ReplyKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        # ★★★ ПОЛНАЯ ИНФОРМАЦИЯ С ПЕРЕНОСАМИ ★★★
        button_text = f"""🎮 {game_name}
📅 {game_date.strftime('%d.%m %H:%M')}-{end_time}
👥 {current_players}/{max_players} игроков"""
        
        keyboard.add(KeyboardButton(text=button_text))
    
    keyboard.add(KeyboardButton(text="🚫 Отменить действие"))
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True)

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

@dp.callback_query(F.data.startswith("register_"))
async def process_game_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        max_players = game[4]
        
        if current_players >= max_players:
            await callback.message.answer(
                f"❌ На эту игру уже набрано максимальное количество игроков ({max_players})\nОбратитесь к админестратору @babzuni777",
                reply_markup=get_games_keyboard()
            )
            await callback.answer()
            return
        
        await state.update_data(game_id=game_id)
        
        # ★★★ ПОКАЗЫВАЕМ ПОЛНУЮ ИНФОРМАЦИЮ ОБ ИГРЕ ★★★
        game_info = f"""🎮 Запись на игру:

🎯 {game[1]}
📅 {get_russian_weekday(game[2])} {game[2].strftime('%d.%m')}
📍 {game[6]}
🕢 {game[2].strftime('%H:%M')}-{game[9]}
💸 {int(game[5])} рублей
🎤 Ведущий: {game[8] or 'Капоне'}
👥 Свободно мест: {max_players - current_players}/{max_players}

👤 Введите ваш игровой никнейм для записи:"""
        
        await callback.message.answer(
            game_info,
            reply_markup=get_cancel_action_keyboard()
        )
        await state.set_state(UserStates.user_register_for_game)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка выбора игры")

@dp.message(UserStates.user_register_for_game)
async def process_game_registration_name(message: Message, state: FSMContext):
    try:
        player_name = message.text.strip()
        
        # ★★★ ОБРАБОТКА ОТМЕНЫ ДЕЙСТВИЯ ★★★
        if player_name == "🚫 Отменить действие":
            await message.answer(
                "✅ Действие отменено",
                reply_markup=get_games_keyboard()
            )
            await state.clear()
            return
        
        # ★★★ ПРОВЕРКА: Запрещаем использовать команды бота в качестве ника ★★★
        if player_name in BOT_COMMANDS:
            await message.answer(
                "❌ Нельзя использовать команды бота в качестве ника!\n\n"
                "👤 Пожалуйста, введите ваш обычный игровой никнейм:",
                reply_markup=get_cancel_action_keyboard()
            )
            return
        
        # ★★★ ПРОВЕРКА: Длина ника ★★★
        if len(player_name) < 2:
            await message.answer(
                "❌ Слишком короткий ник! Минимум 2 символа.\n\n"
                "👤 Пожалуйста, введите ваш игровой никнейм:",
                reply_markup=get_cancel_action_keyboard()
            )
            return

        if len(player_name) > 30:
            await message.answer(
                "❌ Слишком длинный ник! Максимум 30 символов.\n\n"
                "👤 Пожалуйста, введите ваш игровой никнейм:",
                reply_markup=get_cancel_action_keyboard()
            )
            return
        
        data = await state.get_data()
        game_id = data.get('game_id')
        
        if not game_id:
            await message.answer("❌ Ошибка: игра не найдена")
            await state.clear()
            return
        
        # ★★★ ПРОВЕРКА: Уже есть ли такой ник на этой игре (с учетом регистра) ★★★
        registrations = db.get_game_registrations(game_id)
        existing_players = [name for name, status, rating, user_id in registrations]
        
        normalized_input_name = normalize_name_for_comparison(player_name)
        
        duplicate_found = False
        existing_duplicate_name = None
        
        for existing_name in existing_players:
            if normalize_name_for_comparison(existing_name) == normalized_input_name:
                duplicate_found = True
                existing_duplicate_name = existing_name
                break
        
        if duplicate_found:
            await message.answer(
                f"❌ Игрок с ником '{existing_duplicate_name}' уже записан на эту игру.\n\n"
                f"Пожалуйста, выберите другой никнейм для записи:",
                reply_markup=get_cancel_action_keyboard()
            )
            return
        
        # Записываем игрока на игру
        success, result_message = db.register_player_for_game(
            game_id, player_name, message.from_user.id
        )
        
        if success:
            game = db.get_game_by_id(game_id)
            registrations = db.get_game_registrations(game_id)
            current_players = len([r for r in registrations if r[1] == 'registered'])
            
            success_text = (
                f"✅ {result_message}\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m %H:%M')}\n"
                f"👤 Ваш ник: {player_name}\n"
                f"👥 Теперь игроков: {current_players}/{game[4]}"
            )
            await message.answer(success_text, reply_markup=get_games_keyboard())
        else:
            await message.answer(result_message, reply_markup=get_games_keyboard())
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"❌ Ошибка при записи на игру: {e}")
        await message.answer("❌ Произошла ошибка при записи на игру", reply_markup=get_games_keyboard())
        await state.clear()

@dp.message(F.text == "❌ Отменить запись")
async def cancel_registration_handler(message: Message):
    user_id = message.from_user.id
    registrations = db.get_user_registrations(user_id)
    
    if not registrations:
        await message.answer("📭 У вас нет активных записей на игры")
        return
    
    await message.answer(
        "❌ Выберите игру для отмены записи:",
        reply_markup=get_cancel_registration_keyboard(registrations)
    )

@dp.callback_query(F.data.startswith("cancelreg_"))
async def process_cancel_registration(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        registrations = db.get_user_registrations(user_id)
        player_name = None
        
        for reg in registrations:
            if reg[0] == game_id:
                player_name = reg[4]
                break
        
        if not player_name:
            await callback.message.answer("❌ Запись не найдена")
            return
        
        if db.remove_player_from_game(game_id, player_name):
            game = db.get_game_by_id(game_id)
            await callback.message.answer(
                f"✅ Запись на игру отменена!\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
                f"👤 Игрок: {player_name}",
                reply_markup=get_games_keyboard()
            )
        else:
            await callback.message.answer("❌ Ошибка при отмене записи")
        
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при отмене записи")

@dp.message(F.text == "👥 Мои записи")
async def my_registrations_handler(message: Message):
    try:
        user_id = message.from_user.id
        registrations = db.get_user_registrations(user_id)
        
        if not registrations:
            await message.answer(
                "📭 Вы еще не записаны ни на одну игру\n\n"
                "🎮 Используйте кнопку 'Записаться на игру' чтобы присоединиться к игре!",
                reply_markup=get_games_keyboard()
            )
            return
        
        registrations_text = "👥 ВАШИ ЗАПИСИ НА ИГРЫ:\n\n"
        
        for reg in registrations:
            game_id, game_name, game_date, location, player_name = reg
            game = db.get_game_by_id(game_id)
            buy_in = game[5] if game else 1200
            host = game[8] if game else 'Капоне'
            end_time = game[9] if game else '22:00'
            
            registrations_text += f"🌃 {get_russian_weekday(game_date)} {game_date.strftime('%d.%m')}\n"
            registrations_text += f"{game_name} \n"
            registrations_text += f"{location}\n"
            registrations_text += f"🕢 {game_date.strftime('%H:%M')}-{end_time}\n"
            registrations_text += f"💸 {int(buy_in)} рублей\n"
            registrations_text += f"🎤 Ведущий: {host}\n"
            registrations_text += f"👤 Ваш ник: {player_name}\n\n"
        
        await message.answer(registrations_text, reply_markup=get_games_keyboard())
        
    except Exception as e:
        await message.answer("❌ Ошибка при получении ваших записей", reply_markup=get_games_keyboard())

@dp.message(F.text == "📋 Списки игроков")
async def show_game_lists_handler(message: Message):
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр")
        return
    
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        short_name = get_unique_short_name(game_name)
        
        button_text = f"{short_name} | {game_date.strftime('%d.%m %H:%M')}-{end_time} | {current_players}/{max_players}"
        
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"list_{game_id}"
        ))
    keyboard.adjust(1)
    
    await message.answer(
        "📋 Выберите игру для просмотра списка игроков:",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("list_"))
async def show_game_list_handler(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        registrations = db.get_game_registrations(game_id)
        
        game_info = f"🎮 {game[1]}\n"
        game_info += f"🌃 {get_russian_weekday(game[2])} {game[2].strftime('%d.%m')}\n"
        game_info += f"📍 {game[6]}\n"
        game_info += f"🕢 {game[2].strftime('%H:%M')}-{game[9] or '22:00'}\n"
        game_info += f"💸 {int(game[5])} рублей\n"
        game_info += f"🎤 Ведущий: {game[8] or 'Капоне'}\n"
        game_info += f"👥 Игроков: {len(registrations)}/{game[4]}\n\n"
        
        if registrations:
            game_info += "📋 СПИСОК ИГРОКОВ:\n"
            for i, (name, status, rating, user_id) in enumerate(registrations, 1):
                game_info += f"{i}. {name}\n"
        else:
            game_info += "📭 Пока никто не записался"
        
        await callback.message.answer(game_info)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при получении списка игроков")

# ========== АДМИН ПАНЕЛЬ ==========

@dp.message(F.text == "👑 Админ-панель")
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    await message.answer("👑 Панель администратора:", reply_markup=get_admin_keyboard())

@dp.message(F.text == "🎮 Управление играми")
async def admin_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🎮 Управление играми:\n\n"
        "• ➕ Создать игру - создать новую игру\n"
        "• 📋 Редактировать игры - просмотр и управление существующими играми",
        reply_markup=get_admin_games_keyboard()
    )

def get_skip_poster_keyboard():
    """Клавиатура для пропуска афиши"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="⏭ Пропустить"))
    keyboard.add(KeyboardButton(text="❌ Отменить создание"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

@dp.message(F.text == "📋 Редактировать игры")
async def edit_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр для редактирования")
        return
    
    games_text = "🎯 АКТИВНЫЕ ИГРЫ ДЛЯ РЕДАКТИРОВАНИЯ:\n\n"
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        games_text += f"🎮 {game_name}\n"
        games_text += f"📅 {game_date.strftime('%d.%m %H:%M')}\n"
        games_text += f"📍 {location}\n" 
        games_text += f"👥 {current_players}/{max_players} игроков\n"
        games_text += f"💸 {int(buy_in)} руб.\n\n"
    
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        short_name = get_unique_short_name(game_name)
        
        button_text = f"{short_name} | {game_date.strftime('%d.%m %H:%M')}-{end_time} | {current_players}/{max_players}"
        
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"manage_{game_id}"
        ))
    keyboard.adjust(1)
    
    await message.answer(
        games_text + "🛠️ Выберите игру для управления:",
        reply_markup=keyboard.as_markup()
    )

@dp.message(F.text == "➕ Создать игру")
async def create_game_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🎮 Введите название игры:\n\n"
        "Пример: 'MagnumPokerLeague' или 'Городская мафия'\n\n"
        "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
        reply_markup=get_cancel_creation_keyboard()
    )
    await state.set_state(UserStates.admin_create_game_name)

@dp.message(UserStates.admin_create_game_name)
async def process_game_name(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    game_name = message.text.strip()
    if len(game_name) < 2:
        await message.answer(
            "❌ Название игры должно содержать минимум 2 символа\n\n"
            "Пожалуйста, введите название игры:",
            reply_markup=get_cancel_creation_keyboard()
        )
        return
    
    await state.update_data(game_name=game_name)
    await message.answer(
        "📅 Введите дату и время для игры:\n\n"
        "Формат: ДД.ММ ЧЧ:ММ-ЧЧ:ММ\n"
        "Пример: 23.04 18:00-23:30\n\n"
        "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
        reply_markup=get_cancel_creation_keyboard()
    )
    await state.set_state(UserStates.admin_create_game_date)

@dp.message(UserStates.admin_create_game_date)
async def process_game_date(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    try:
        date_time_str = message.text.strip()
        date_part, time_part = date_time_str.split(' ')
        start_time_str, end_time_str = time_part.split('-')
        
        current_year = datetime.now().year
        start_datetime = datetime.strptime(f"{date_part}.{current_year} {start_time_str}", "%d.%m.%Y %H:%M")
        
        await state.update_data(
            game_date=start_datetime,
            end_time=end_time_str
        )
        await message.answer(
            "👥 Введите максимальное количество игроков:\n\n"
            "Пример: 9, 18, 27\n\n"
            "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
            reply_markup=get_cancel_creation_keyboard()
        )
        await state.set_state(UserStates.admin_create_game_players)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Используйте: ДД.ММ ЧЧ:ММ-ЧЧ:ММ\n"
            "Пример: 23.04 18:00-23:30\n\n"
            "Пожалуйста, введите дату и время:",
            reply_markup=get_cancel_creation_keyboard()
        )

@dp.message(UserStates.admin_create_game_players)
async def process_game_players(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    try:
        max_players = int(message.text.strip())
        
        if max_players <= 0:
            await message.answer(
                "❌ Количество игроков должно быть больше 0\n\n"
                "Пожалуйста, введите максимальное количество игроков:",
                reply_markup=get_cancel_creation_keyboard()
            )
            return
        
        await state.update_data(max_players=max_players)
        await message.answer(
            "📍 Введите адрес проведения игры:\n\n"
            "Пример: 'Арабист (Большая Андроньевская 23) Метро: Таганская/Римская/Площадь Ильича'\n\n"
            "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
            reply_markup=get_cancel_creation_keyboard()
        )
        await state.set_state(UserStates.admin_create_game_location)
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число игроков\n\n"
            "Пример: 9, 18, 27\n\n"
            "Пожалуйста, введите максимальное количество игроков:",
            reply_markup=get_cancel_creation_keyboard()
        )

@dp.message(UserStates.admin_create_game_location)
async def process_game_location(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    location = message.text.strip()
    await state.update_data(location=location)
    await message.answer(
        "💸 Введите стоимость участия в рублях:\n\n"
        "Пример: 900, 1200\n\n"
        "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
        reply_markup=get_cancel_creation_keyboard()
    )
    await state.set_state(UserStates.admin_create_game_price)

@dp.message(UserStates.admin_create_game_price)
async def process_game_price(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    try:
        price = int(message.text.strip())
        
        if price <= 0:
            await message.answer(
                "❌ Стоимость должна быть больше 0\n\n"
                "Пожалуйста, введите стоимость участия:",
                reply_markup=get_cancel_creation_keyboard()
            )
            return
        
        await state.update_data(price=price)
        await message.answer(
            "🎤 Введите имя ведущего игры:\n\n"
            "Пример: Капоне, Стас\n\n"
            "❌ Или нажмите 'Отменить создание' чтобы вернуться назад",
            reply_markup=get_cancel_creation_keyboard()
        )
        await state.set_state(UserStates.admin_create_game_host)
        
    except ValueError:
        await message.answer(
            "❌ Введите корректную стоимость (число)\n\n"
            "Пример: 1200, 1500, 2000\n\n"
            "Пожалуйста, введите стоимость участия:",
            reply_markup=get_cancel_creation_keyboard()
        )

@dp.message(UserStates.admin_create_game_host)
async def process_game_host(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    host = message.text.strip()
    await state.update_data(host=host)
    
    await message.answer(
        "🎨 Добавление афиши игры:\n\n"
        "Отправьте фото афиши для этой игры (необязательно)\n\n"
        "Или нажмите 'Пропустить' чтобы продолжить без афиши",
        reply_markup=get_skip_poster_keyboard()
    )
    await state.set_state(UserStates.admin_add_game_poster)

@dp.message(UserStates.admin_add_game_poster)
async def process_game_poster(message: Message, state: FSMContext):
    if message.text == "❌ Отменить создание":
        await message.answer("✅ Создание игры отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    poster_file_id = None
    
    if message.photo:
        poster_file_id = message.photo[-1].file_id
        poster_message = "✅ Афиша игры добавлена"
    elif message.text == "⏭ Пропустить":
        poster_message = "⏭ Афиша не добавлена"
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте фото афиши или нажмите 'Пропустить'",
            reply_markup=get_skip_poster_keyboard()
        )
        return
    
    data = await state.get_data()
    
    game_name = data.get('game_name')
    game_date = data.get('game_date')
    max_players = data.get('max_players')
    location = data.get('location')
    price = data.get('price')
    host = data.get('host')
    end_time = data.get('end_time')
    
    game_id = db.create_game(
        game_name=game_name,
        game_date=game_date,
        max_players=max_players,
        game_type="Texas Holdem",
        buy_in=price,
        location=location,
        host=host,
        end_time=end_time,
        created_by=message.from_user.id
    )
    
    if game_id:
        # Сохраняем афишу если есть
        if poster_file_id:
            db.update_game_poster(game_id, poster_file_id)
        
        await message.answer(
            f"✅ Игра успешно создана!\n{poster_message}\n\n"
            f"🎮 {game_name}\n"
            f"📅 {game_date.strftime('%d.%m')} {game_date.strftime('%H:%M')}-{end_time}\n"
            f"👥 Макс. игроков: {max_players}\n"
            f"📍 {location}\n"
            f"💸 {price} рублей\n"
            f"🎤 Ведущий: {host}",
            reply_markup=get_admin_games_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при создании игры",
            reply_markup=get_admin_games_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("manage_"))
async def manage_game_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        game_info = f"🎮 Управление игрой:\n\n"
        game_info += f"📝 {game[1]}\n"
        game_info += f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
        game_info += f"👥 Игроков: {len(db.get_game_registrations(game_id))}/{game[4]}\n"
        game_info += f"📍 {game[6] or 'Адрес не указан'}\n\n"
        game_info += "🛠️ Выберите действие:"
        
        await callback.message.answer(
            game_info,
            reply_markup=get_game_management_keyboard(game_id)
        )
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при управлении игрой")

@dp.callback_query(F.data.startswith("limit_"))
async def change_game_limit_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"✏️ Изменение лимита игроков:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Текущий лимит: {game[4]} игроков\n\n"
            "Введите новое максимальное количество игроков:"
        )
        await state.set_state(UserStates.admin_update_game_limit)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при изменении лимита")

@dp.message(UserStates.admin_update_game_limit)
async def process_game_limit_update(message: Message, state: FSMContext):
    try:
        new_limit = int(message.text.strip())
        data = await state.get_data()
        game_id = data.get('game_id')
        
        if new_limit <= 0:
            await message.answer("❌ Лимит должен быть больше 0")
            return
        
        if db.update_game_max_players(game_id, new_limit):
            await message.answer(
                f"✅ Лимит игроков обновлен!\n"
                f"👥 Новый лимит: {new_limit} игроков",
                reply_markup=get_admin_games_keyboard()
            )
        else:
            await message.answer("❌ Ошибка при обновлении лимита")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число")

@dp.callback_query(F.data.startswith("remove_"))
async def remove_player_game_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        registrations = db.get_game_registrations(game_id)
        
        if not registrations:
            await callback.message.answer("❌ На этой игре нет записавшихся игроков")
            return
        
        players_list = "\n".join([f"• {name}" for name, status, rating, user_id in registrations])
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"🗑 Удаление игрока с игры:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📋 Записанные игроки:\n{players_list}\n\n"
            "Введите имя игрока для удаления с игры:"
        )
        await state.set_state(UserStates.admin_remove_player_from_game)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при удалении игрока")

@dp.message(UserStates.admin_remove_player_from_game)
async def process_remove_player_from_game(message: Message, state: FSMContext):
    player_name = message.text.strip()
    data = await state.get_data()
    game_id = data.get('game_id')
    
    if db.remove_player_from_game(game_id, player_name):
        await message.answer(
            f"✅ Игрок '{player_name}' удален с игры",
            reply_markup=get_admin_games_keyboard()
        )
    else:
        await message.answer(
            f"❌ Игрок '{player_name}' не найден на игре",
            reply_markup=get_admin_games_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("delete_game_"))
async def delete_specific_game_handler(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[2])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            await callback.answer()
            return
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_game_{game_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_delete_game_{game_id}"))
        keyboard.adjust(2)
        
        await callback.message.answer(
            f"⚠️ ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ИГРУ?\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 {game[6] or 'Адрес не указан'}\n\n"
            f"❌ Это действие нельзя отменить!",
            reply_markup=keyboard.as_markup()
        )
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при удалении игры")
        await callback.answer()

@dp.callback_query(F.data.startswith("confirm_delete_game_"))
async def confirm_delete_specific_game_handler(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[3])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            await callback.answer()
            return
        
        if db.delete_game(game_id):
            await callback.message.answer(
                f"✅ Игра удалена!\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_admin_games_keyboard()
            )
        else:
            await callback.message.answer("❌ Ошибка при удалении игры", reply_markup=get_admin_games_keyboard())
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при удалении игры")
        await callback.answer()

@dp.callback_query(F.data.startswith("cancel_delete_game_"))
async def cancel_delete_specific_game_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление игры отменено", reply_markup=get_admin_games_keyboard())
    await callback.answer()

# 1. ОБРАБОТЧИК ИЗМЕНЕНИЯ ВЕДУЩЕГО
@dp.callback_query(F.data.startswith("host_"))
async def change_game_host_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"🎤 Изменение ведущего:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"🎤 Текущий ведущий: {game[8] or 'Капоне'}\n\n"
            "Введите нового ведущего:\n\n"
            "❌ Или нажмите 'Отменить редактирование'",
            reply_markup=get_cancel_edit_keyboard()
        )
        await state.set_state(UserStates.admin_update_game_host)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при изменении ведущего")

@dp.message(UserStates.admin_update_game_host)
async def process_game_host_update(message: Message, state: FSMContext):
    if message.text == "❌ Отменить редактирование":
        await message.answer("✅ Редактирование отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    new_host = message.text.strip()
    data = await state.get_data()
    game_id = data.get('game_id')
    
    if db.update_game_host(game_id, new_host):
        game = db.get_game_by_id(game_id)
        await message.answer(
            f"✅ Ведущий обновлен!\n\n"
            f"🎮 {game[1]}\n"
            f"🎤 Новый ведущий: {new_host}",
            reply_markup=get_admin_games_keyboard()
        )
    else:
        await message.answer("❌ Ошибка при обновлении ведущего")
    
    await state.clear()

# 2. ОБРАБОТЧИК ИЗМЕНЕНИЯ ВРЕМЕНИ
@dp.callback_query(F.data.startswith("time_"))
async def change_game_time_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"🕒 Изменение времени:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y')}\n"
            f"🕒 Текущее время: {game[2].strftime('%H:%M')}-{game[9]}\n\n"
            "Введите новое время в формате ЧЧ:ММ-ЧЧ:ММ:\n"
            "Пример: 18:00-23:30\n\n"
            "❌ Или нажмите 'Отменить редактирование'",
            reply_markup=get_cancel_edit_keyboard()
        )
        await state.set_state(UserStates.admin_update_game_time)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при изменении времени")

@dp.message(UserStates.admin_update_game_time)
async def process_game_time_update(message: Message, state: FSMContext):
    if message.text == "❌ Отменить редактирование":
        await message.answer("✅ Редактирование отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    try:
        time_str = message.text.strip()
        start_time_str, end_time_str = time_str.split('-')
        
        # Проверяем формат времени
        datetime.strptime(start_time_str, "%H:%M")
        datetime.strptime(end_time_str, "%H:%M")
        
        data = await state.get_data()
        game_id = data.get('game_id')
        
        if db.update_game_time(game_id, start_time_str, end_time_str):
            game = db.get_game_by_id(game_id)
            await message.answer(
                f"✅ Время обновлено!\n\n"
                f"🎮 {game[1]}\n"
                f"🕒 Новое время: {start_time_str}-{end_time_str}",
                reply_markup=get_admin_games_keyboard()
            )
        else:
            await message.answer("❌ Ошибка при обновлении времени")
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Используйте: ЧЧ:ММ-ЧЧ:ММ\n"
            "Пример: 18:00-23:30\n\n"
            "Пожалуйста, введите время:",
            reply_markup=get_cancel_edit_keyboard()
        )

# 3. ОБРАБОТЧИК ИЗМЕНЕНИЯ ДАТЫ
@dp.callback_query(F.data.startswith("date_"))
async def change_game_date_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"📅 Изменение даты:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 Текущая дата: {game[2].strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {game[2].strftime('%H:%M')}-{game[9]}\n\n"
            "Введите новую дату в формате ДД.ММ.ГГГГ:\n"
            "Пример: 25.12.2024\n\n"
            "❌ Или нажмите 'Отменить редактирование'",
            reply_markup=get_cancel_edit_keyboard()
        )
        await state.set_state(UserStates.admin_update_game_date)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при изменении даты")

@dp.message(UserStates.admin_update_game_date)
async def process_game_date_update(message: Message, state: FSMContext):
    if message.text == "❌ Отменить редактирование":
        await message.answer("✅ Редактирование отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    try:
        date_str = message.text.strip()
        new_date = datetime.strptime(date_str, "%d.%m.%Y")
        
        data = await state.get_data()
        game_id = data.get('game_id')
        game = db.get_game_by_id(game_id)
        
        if game:
            # Сохраняем старое время, меняем только дату
            old_datetime = game[2]
            new_datetime = new_date.replace(
                hour=old_datetime.hour,
                minute=old_datetime.minute
            )
            
            if db.update_game_date(game_id, new_datetime):
                await message.answer(
                    f"✅ Дата обновлена!\n\n"
                    f"🎮 {game[1]}\n"
                    f"📅 Новая дата: {new_date.strftime('%d.%m.%Y')}",
                    reply_markup=get_admin_games_keyboard()
                )
            else:
                await message.answer("❌ Ошибка при обновлении даты")
        else:
            await message.answer("❌ Игра не найдена")
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ\n"
            "Пример: 25.12.2024\n\n"
            "Пожалуйста, введите дату:",
            reply_markup=get_cancel_edit_keyboard()
        )

# 4. ОБРАБОТЧИК ИЗМЕНЕНИЯ АДРЕСА
@dp.callback_query(F.data.startswith("location_"))
async def change_game_location_handler(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"📍 Изменение адреса:\n\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 Текущий адрес: {game[6] or 'Не указан'}\n\n"
            "Введите новый адрес:\n\n"
            "❌ Или нажмите 'Отменить редактирование'",
            reply_markup=get_cancel_edit_keyboard()
        )
        await state.set_state(UserStates.admin_update_game_location)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при изменении адреса")

@dp.message(UserStates.admin_update_game_location)
async def process_game_location_update(message: Message, state: FSMContext):
    if message.text == "❌ Отменить редактирование":
        await message.answer("✅ Редактирование отменено", reply_markup=get_admin_games_keyboard())
        await state.clear()
        return
    
    new_location = message.text.strip()
    data = await state.get_data()
    game_id = data.get('game_id')
    
    if db.update_game_location(game_id, new_location):
        game = db.get_game_by_id(game_id)
        await message.answer(
            f"✅ Адрес обновлен!\n\n"
            f"🎮 {game[1]}\n"
            f"📍 Новый адрес: {new_location}",
            reply_markup=get_admin_games_keyboard()
        )
    else:
        await message.answer("❌ Ошибка при обновлении адреса")
    
    await state.clear()

@dp.message(F.text == "🗑 Удалить все игры")
async def delete_all_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр для удаления")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Да, удалить все", callback_data="confirm_delete_all_games"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_all_games"))
    keyboard.adjust(2)
    
    await message.answer(
        f"⚠️ ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ВСЕ ИГРЫ?\n\n"
        f"📊 Будет удалено: {len(games)} игр\n"
        f"🎮 Список игр:\n" + "\n".join([f"• {game[1]}" for game in games]) + "\n\n"
        f"❌ Это действие нельзя отменить!",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data == "confirm_delete_all_games")
async def confirm_delete_all_games_handler(callback: types.CallbackQuery):
    try:
        if db.delete_all_games():
            await callback.message.answer("✅ Все игры успешно удалены!", reply_markup=get_admin_keyboard())
        else:
            await callback.message.answer("❌ Ошибка при удалении всех игр", reply_markup=get_admin_keyboard())
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer("❌ Ошибка при удалении игр", reply_markup=get_admin_keyboard())
        await callback.answer()

@dp.callback_query(F.data == "cancel_delete_all_games")
async def cancel_delete_all_games_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление всех игр отменено", reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.message(F.text == "📢 Рассылка")
async def broadcast_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📢 Всем пользователям бота", callback_data="broadcast_all"))
    keyboard.add(InlineKeyboardButton(text="🎮 По конкретной игре", callback_data="broadcast_game_select"))
    keyboard.add(InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    await message.answer(
        "📢 СИСТЕМА РАССЫЛКИ\n\n"
        "Выберите аудиторию для рассылки:",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data == "broadcast_all")
async def broadcast_all_handler(callback: types.CallbackQuery, state: FSMContext):
    user_ids = db.get_all_bot_users()
    
    if not user_ids:
        await callback.message.answer("❌ Нет пользователей для рассылки")
        await callback.answer()
        return
    
    await state.update_data(
        broadcast_type="all", 
        user_ids=user_ids,
        is_broadcast=True
    )
    
    await callback.message.answer(
        f"📢 Рассылка ВСЕМ пользователям бота\n"
        f"👥 Получателей: {len(user_ids)}\n\n"
        "📤 Отправьте сообщение для рассылки (текст, фото, или фото с текстом):"
    )
    await state.set_state(UserStates.admin_broadcast_message)
    await callback.answer()

@dp.callback_query(F.data == "broadcast_game_select")
async def broadcast_game_select_handler(callback: types.CallbackQuery):
    games = db.get_upcoming_games()
    
    if not games:
        await callback.message.answer("🎉 Нет активных игр для рассылки")
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        short_name = get_unique_short_name(game_name)
        
        button_text = f"{short_name} | {game_date.strftime('%d.%m %H:%M')}-{end_time} | {current_players} 👥"
        
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"broadcast_game_{game_id}"
        ))
    keyboard.add(InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    await callback.message.answer(
        "📢 Выберите игру для рассылки:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("broadcast_game_"))
async def broadcast_specific_game_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        game_id = int(callback.data.split('_')[2])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            await callback.answer()
            return
        
        user_ids = db.get_game_registrations_by_game(game_id)
        
        if not user_ids:
            await callback.message.answer("❌ На этой игре нет записавшихся игроков")
            await callback.answer()
            return
        
        await state.update_data(
            broadcast_type=f"game_{game_id}", 
            user_ids=user_ids,
            is_broadcast=True
        )
        
        await callback.message.answer(
            f"📢 Рассылка по игре:\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Получателей: {len(user_ids)}\n\n"
            "📤 Отправьте сообщение для рассылки (текст, фото, или фото с текстом):"
        )
        await state.set_state(UserStates.admin_broadcast_message)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при выборе игры")
        await callback.answer()

@dp.message(UserStates.admin_broadcast_message)
async def broadcast_content_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if not data.get('is_broadcast'):
        await state.clear()
        return
    
    user_ids = data.get('user_ids', [])
    broadcast_type = data.get('broadcast_type', 'manual')
    
    if not user_ids:
        await message.answer("❌ Нет получателей для рассылки")
        await state.clear()
        return
    
    sent_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            if message.photo:
                photo_file_id = message.photo[-1].file_id
                caption = message.caption if message.caption else ""
                
                await bot.send_photo(user_id, photo=photo_file_id, caption=caption)
            else:
                await bot.send_message(user_id, message.text)
            
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")
            failed_count += 1
    
    if broadcast_type == "all":
        report = f"📢 Рассылка ВСЕМ пользователям бота завершена!\n"
    elif broadcast_type.startswith("game_"):
        game_id = broadcast_type.split('_')[1]
        report = f"📢 Рассылка по игре #{game_id} завершена!\n"
    else:
        report = f"📢 Рассылка завершена!\n"
    
    report += f"✅ Отправлено: {sent_count}\n"
    report += f"❌ Не отправлено: {failed_count}\n"
    report += f"👥 Всего получателей: {len(user_ids)}"
    
    await message.answer(report, reply_markup=get_admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Рассылка отменена", reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.message(F.text == "📋 Списки всех игроков")
async def admin_all_players_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр")
        return
    
    all_players_text = "📋 СПИСКИ ИГРОКОВ НА ВСЕ ИГРЫ:\n\n"
    
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time = game
        registrations = db.get_game_registrations(game_id)
        
        all_players_text += f"🎮 {game_name}\n"
        all_players_text += f"🌃 {get_russian_weekday(game_date)} {game_date.strftime('%d.%m')}\n"
        all_players_text += f"📍 {location}\n"
        all_players_text += f"🕢 {game_date.strftime('%H:%M')}-{end_time or '22:00'}\n"
        all_players_text += f"💸 {int(buy_in)} рублей\n"
        all_players_text += f"🎤 Ведущий: {host or 'Капоне'}\n"
        all_players_text += f"👥 Игроков: {len(registrations)}/{max_players}\n"
        
        if registrations:
            all_players_text += "📋 СПИСОК ИГРОКОВ:\n"
            for i, (name, status, rating, user_id) in enumerate(registrations, 1):
                all_players_text += f"{i}. {name}\n"
        else:
            all_players_text += "📭 Пока никто не записался\n"
        
        all_players_text += "\n"
    
    await message.answer(all_players_text)

@dp.message(F.text == "📊 Статистика БД")
async def db_check_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    try:
        global players_rating
        players_rating = db.get_all_players()
        
        total_players = len(players_rating)
        total_bot_users = len(db.get_all_bot_users())
        
        status_text = "🟢 БАЗА ДАННЫХ РАБОТАЕТ\n\n"
        status_text += f"📊 Статистика:\n"
        status_text += f"• Игроков в базе: {total_players}\n"
        status_text += f"• Пользователей бота: {total_bot_users}\n"
        
        if players_rating:
            status_text += "\n📋 Топ игроков:\n"
            for i, (name, rating) in enumerate(list(players_rating.items())[:10], 1):
                status_text += f"{i}. {name}: {rating}\n"
        
        await message.answer(status_text, reply_markup=get_admin_keyboard())
        
    except Exception as e:
        await message.answer(f"🔴 ОШИБКА БАЗЫ ДАННЫХ:\n{str(e)}")

@dp.message(F.text == "🏆 Управление рейтингами")
async def admin_ratings_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("🏆 Управление рейтингами:", reply_markup=get_admin_ratings_keyboard())

@dp.message(F.text == "🏆 Добавить рейтинг покер")
async def admin_add_poker_rating_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(UserStates.admin_add_poker_rating)
    await state.update_data(rating_type="poker", photos=[])
    
    await message.answer(
        "🏆 Добавление рейтинга покера:\n\n"
        "📤 Отправляйте фото с рейтингами игроков\n"
        "✅ Когда все фото отправлены, нажмите '✅ Афиш больше нет'",
        reply_markup=get_finish_adding_keyboard()
    )

@dp.message(F.text == "🗑 Удалить рейтинг покер")
async def admin_remove_poker_rating_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    poker_ratings = db.get_poker_ratings()
    
    if not poker_ratings:
        await message.answer("🏆 Нет рейтингов покера для удаления")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_all_poker"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_all_poker"))
    keyboard.adjust(2)
    
    await message.answer(
        f"⚠️ ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ РЕЙТИНГ ПОКЕРА?\n\n"
        f"📊 Будет удалено: {len(poker_ratings)} фото\n"
        f"🎯 Это действие нельзя отменить!",
        reply_markup=keyboard.as_markup()
    )

@dp.message(F.text == "🔫 Добавить рейтинг мафия")
async def admin_add_mafia_rating_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🌆 Добавить в Городскую мафию"))
    keyboard.add(KeyboardButton(text="🃏 Добавить в Мафию Картель"))
    keyboard.add(KeyboardButton(text="🔙 Управление рейтингами"))
    keyboard.adjust(2)
    
    await message.answer(
        "🔫 Добавление рейтинга мафии:\n\n"
        "Выберите тип мафии:",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )

@dp.message(F.text == "🌆 Добавить в Городскую мафию")
async def admin_add_mafia_city_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(UserStates.admin_add_mafia_city_rating)
    await state.update_data(rating_type="city", photos=[])
    
    await message.answer(
        "🌆 Добавление рейтинга Городской мафии:\n\n"
        "📤 Отправляйте фото с рейтингами игроков\n"
        "✅ Когда все фото отправлены, нажмите '✅ Афиш больше нет'",
        reply_markup=get_finish_adding_keyboard()
    )

@dp.message(F.text == "🃏 Добавить в Мафию Картель")
async def admin_add_mafia_cartel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(UserStates.admin_add_mafia_cartel_rating)
    await state.update_data(rating_type="cartel", photos=[])
    
    await message.answer(
        "🃏 Добавление рейтинга Мафии Картель:\n\n"
        "📤 Отправляйте фото с рейтингами игроков\n"
        "✅ Когда все фото отправлены, нажмите '✅ Афиш больше нет'",
        reply_markup=get_finish_adding_keyboard()
    )

@dp.message(F.text == "✂️ Удалить рейтинг мафия")
async def admin_remove_mafia_rating_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🌆 Удалить рейтинг Городской мафии"))
    keyboard.add(KeyboardButton(text="🃏 Удалить рейтинг Мафии Картель"))
    keyboard.add(KeyboardButton(text="🔙 Управление рейтингами"))
    keyboard.adjust(2)
    
    await message.answer(
        "✂️ Удаление рейтинга мафии:\n\n"
        "Выберите тип мафии:",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )

@dp.message(
    F.photo,
    StateFilter(
        UserStates.admin_add_poker_rating,
        UserStates.admin_add_mafia_city_rating,
        UserStates.admin_add_mafia_cartel_rating
    )
)
async def process_rating_photo(message: Message, state: FSMContext):
    # Получаем файл фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Генерируем уникальное имя для фото
    data = await state.get_data()
    photos = data.get('photos', [])
    
    # Создаем имя файла на основе timestamp
    import time
    photo_name = f"photo_{int(time.time())}_{len(photos)}"
    
    # Добавляем фото в список
    photos.append((photo_name, file_id))
    await state.update_data(photos=photos)
    
    await message.answer(
        f"✅ Фото #{len(photos)} добавлено\n"
        f"📸 Всего фото: {len(photos)}\n\n"
        "📤 Отправьте следующее фото или нажмите '✅ Афиш больше нет'"
    )

@dp.message(
    F.text == "✅ Афиш больше нет",
    StateFilter(
        UserStates.admin_add_poker_rating,
        UserStates.admin_add_mafia_city_rating,
        UserStates.admin_add_mafia_cartel_rating
    )
)
async def finish_adding_ratings(message: Message, state: FSMContext):
    data = await state.get_data()
    rating_type = data.get('rating_type')
    photos = data.get('photos', [])
    
    if not photos:
        await message.answer("❌ Не добавлено ни одного фото", reply_markup=get_admin_ratings_keyboard())
        await state.clear()
        return
    
    # Сохраняем все фото в БД
    saved_count = 0
    for player_name, file_id in photos:
        success = False
        if rating_type == "poker":
            success = db.save_poker_rating(player_name, file_id)
        elif rating_type == "city":
            success = db.save_mafia_city_rating(player_name, file_id)
        elif rating_type == "cartel":
            success = db.save_mafia_cartel_rating(player_name, file_id)
        
        if success:
            saved_count += 1
    
    # Простое сообщение без лишней информации
    await message.answer(
        f"✅ Добавлено {saved_count} фото",
        reply_markup=get_admin_ratings_keyboard()
    )
    await state.clear()


@dp.message(F.text == "🌆 Удалить рейтинг Городской мафии")
async def admin_remove_mafia_city_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    mafia_city_ratings = db.get_mafia_city_ratings()
    
    if not mafia_city_ratings:
        await message.answer("🌆 Нет рейтингов Городской мафии для удаления")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_all_mafia_city"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_all_mafia_city"))
    keyboard.adjust(2)
    
    await message.answer(
        f"⚠️ ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ РЕЙТИНГ ГОРОДСКОЙ МАФИИ?\n\n"
        f"📊 Будет удалено: {len(mafia_city_ratings)} фото\n"
        f"🎯 Это действие нельзя отменить!",
        reply_markup=keyboard.as_markup()
    )

@dp.message(F.text == "🃏 Удалить рейтинг Мафии Картель")
async def admin_remove_mafia_cartel_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    mafia_cartel_ratings = db.get_mafia_cartel_ratings()
    
    if not mafia_cartel_ratings:
        await message.answer("🃏 Нет рейтингов Мафии Картель для удаления")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_all_mafia_cartel"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_all_mafia_cartel"))
    keyboard.adjust(2)
    
    await message.answer(
        f"⚠️ ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ РЕЙТИНГ МАФИИ КАРТЕЛЬ?\n\n"
        f"📊 Будет удалено: {len(mafia_cartel_ratings)} фото\n"
        f"🎯 Это действие нельзя отменить!",
        reply_markup=keyboard.as_markup()
    )

@dp.message(F.text == "🔙 Главное меню")
async def main_menu_handler(message: Message):
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "🔙 Назад к играм")
async def back_to_games_handler(message: Message):
    await message.answer("Возвращаемся к играм:", reply_markup=get_games_keyboard())

@dp.message(F.text == "🔙 Админ-панель")
async def back_to_admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Возвращаемся в админ-панель:", reply_markup=get_admin_keyboard())

# Обработчики удаления рейтинга покера
@dp.callback_query(F.data == "confirm_delete_all_poker")
async def confirm_delete_all_poker_handler(callback: types.CallbackQuery):
    try:
        # Получаем соединение из db и выполняем SQL
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM poker_ratings")
        db.conn.commit()
        cursor.close()
        
        await callback.message.answer(
            f"✅ Рейтинг покера успешно удален!",
            reply_markup=get_admin_ratings_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"❌ Ошибка удаления рейтинга покера: {e}")
        await callback.message.answer("❌ Ошибка при удалении рейтинга", reply_markup=get_admin_ratings_keyboard())
        await callback.answer()

@dp.callback_query(F.data == "cancel_delete_all_poker")
async def cancel_delete_all_poker_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление рейтинга покера отменено", reply_markup=get_admin_ratings_keyboard())
    await callback.answer()

# Аналогично для mafia_city и mafia_cartel

@dp.callback_query(F.data == "cancel_delete_all_poker")
async def cancel_delete_all_poker_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление рейтинга покера отменено", reply_markup=get_admin_ratings_keyboard())
    await callback.answer()

# Обработчики удаления ВСЕГО рейтинга городской мафии
@dp.callback_query(F.data == "confirm_delete_all_mafia_city")
async def confirm_delete_all_mafia_city_handler(callback: types.CallbackQuery):
    try:
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM mafia_city_ratings")
        db.conn.commit()
        cursor.close()
        
        await callback.message.answer(
            f"✅ Весь рейтинг Городской мафии успешно удален!",
            reply_markup=get_admin_ratings_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"❌ Ошибка удаления рейтинга Городской мафии: {e}")
        await callback.message.answer("❌ Ошибка при удалении рейтинга", reply_markup=get_admin_ratings_keyboard())
        await callback.answer()

@dp.callback_query(F.data == "cancel_delete_all_mafia_city")
async def cancel_delete_all_mafia_city_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление рейтинга Городской мафии отменено", reply_markup=get_admin_ratings_keyboard())
    await callback.answer()

# Обработчики удаления ВСЕГО рейтинга мафии картель
@dp.callback_query(F.data == "confirm_delete_all_mafia_cartel")
async def confirm_delete_all_mafia_cartel_handler(callback: types.CallbackQuery):
    try:
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM mafia_cartel_ratings")
        db.conn.commit()
        cursor.close()
        
        await callback.message.answer(
            f"✅ Весь рейтинг Мафии Картель успешно удален!",
            reply_markup=get_admin_ratings_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"❌ Ошибка удаления рейтинга Мафии Картель: {e}")
        await callback.message.answer("❌ Ошибка при удалении рейтинга", reply_markup=get_admin_ratings_keyboard())
        await callback.answer()

@dp.callback_query(F.data == "cancel_delete_all_mafia_cartel")
async def cancel_delete_all_mafia_cartel_handler(callback: types.CallbackQuery):
    await callback.message.answer("❌ Удаление рейтинга Мафии Картель отменено", reply_markup=get_admin_ratings_keyboard())
    await callback.answer()

async def cleanup_processed_starts():
    while True:
        await asyncio.sleep(60)
        current_time = asyncio.get_event_loop().time()
        global processed_starts
        processed_starts = {uid: time for uid, time in processed_starts.items() if current_time - time < 300}

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен со всеми функциями!")
    
    asyncio.create_task(cleanup_processed_starts())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())