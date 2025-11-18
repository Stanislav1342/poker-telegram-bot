import asyncio
import logging
import os
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
    
    # новые состояния для игр
    admin_create_game_name = State()
    admin_create_game_date = State()
    admin_create_game_details = State()
    admin_remove_player_from_game = State()
    admin_update_game_limit = State()
    admin_broadcast_message = State()
    user_register_for_game = State()
    user_select_game = State()

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

# Функция для нормализации имен (е/ё)
def normalize_name(name):
    """Нормализация имени: заменяет ё на е и приводит к нижнему регистру"""
    return name.lower().replace('ё', 'е')

# Проверка является ли пользователь админом
def is_admin(user_id):
    admin_ids = [1308823467]
    return user_id in admin_ids

# Клавиатура главного меню
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🎯 Мой рейтинг"))
    keyboard.add(KeyboardButton(text="🏆 Общий рейтинг"))
    keyboard.add(KeyboardButton(text="🎮 Игры"))
    keyboard.add(KeyboardButton(text="📚 Правила покера"))
    keyboard.add(KeyboardButton(text="🎯 Тест по покеру"))
    
    if is_admin(user_id):
        keyboard.add(KeyboardButton(text="👑 Админ-панель"))
    
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Админ клавиатура
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="➕ Добавить игрока"))
    keyboard.add(KeyboardButton(text="✏️ Изменить рейтинг"))
    keyboard.add(KeyboardButton(text="🗑 Удалить игрока"))
    keyboard.add(KeyboardButton(text="📤 Загрузить карточку"))
    keyboard.add(KeyboardButton(text="🎮 Управление играми"))
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
    keyboard.add(KeyboardButton(text="👥 Списки записей"))
    keyboard.add(KeyboardButton(text="🔙 Админ-панель"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Клавиатура для управления конкретной игрой
def get_game_management_keyboard(game_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список игроков", callback_data=f"list_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="✏️ Изменить лимит", callback_data=f"limit_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="🗑 Удалить игрока", callback_data=f"remove_{game_id}"))
    keyboard.add(InlineKeyboardButton(text="❌ Отменить игру", callback_data=f"cancel_{game_id}"))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Клавиатура для выбора игры
def get_games_selection_keyboard(games, action="select"):
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status = game
        keyboard.add(InlineKeyboardButton(
            text=f"{game_name} ({game_date.strftime('%d.%m %H:%M')})",
            callback_data=f"{action}_{game_id}"
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

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@dp.message(Command("start"))
async def start_handler(message: Message, command: CommandObject):
    # Игнорируем повторные вызовы /start с параметрами
    if command.args:
        return
    
    user_id = message.from_user.id
    current_time = message.date.timestamp()
    
    # Проверяем, не обрабатывали ли мы недавно этот start
    if user_id in processed_starts:
        last_time = processed_starts[user_id]
        # Если прошло меньше 3 секунд - игнорируем повторный вызов
        if current_time - last_time < 3:
            return
    
    # Сохраняем время обработки
    processed_starts[user_id] = current_time
    
    welcome_text = (
        "♥️♣️ Добро пожаловать в MagnumPoker ♦️♠️\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

# ========== СИСТЕМА ИГР ==========

@dp.message(F.text == "🎮 Игры")
async def games_handler(message: Message):
    await message.answer("🎮 Управление играми и записями:", reply_markup=get_games_keyboard())

@dp.message(F.text == "🎮 Управление играми")
async def admin_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("👑 Админ-панель игр:", reply_markup=get_admin_games_keyboard())

# Создание игры (админ)
@dp.message(F.text == "➕ Создать игру")
async def create_game_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🎮 Введите название игры:\n\n"
        "Пример: 'Турнир по Техасскому Холдему' или 'Кэш-игра NL100'"
    )
    await state.set_state(UserStates.admin_create_game_name)

@dp.message(UserStates.admin_create_game_name)
async def process_game_name(message: Message, state: FSMContext):
    game_name = message.text.strip()
    if len(game_name) < 2:
        await message.answer("❌ Название игры должно содержать минимум 2 символа")
        return
    
    await state.update_data(game_name=game_name)
    await message.answer(
        "📅 Введите дату и время для игры:\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 15.01.2024 19:30"
    )
    await state.set_state(UserStates.admin_create_game_date)

@dp.message(UserStates.admin_create_game_date)
async def process_game_date(message: Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        game_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        
        await state.update_data(game_date=game_date)
        await message.answer(
            "👥 Введите максимальное количество игроков:\n\n"
            "Пример: 9, 18, 27"
        )
        await state.set_state(UserStates.admin_create_game_details)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ\nПример: 15.01.2024 19:30")

@dp.message(UserStates.admin_create_game_details)
async def process_game_details(message: Message, state: FSMContext):
    try:
        max_players = int(message.text.strip())
        data = await state.get_data()
        game_name = data.get('game_name')
        game_date = data.get('game_date')
        
        if max_players <= 0:
            await message.answer("❌ Количество игроков должно быть больше 0")
            return
        
        await message.answer(
            "📍 Введите адрес проведения игры:\n\n"
            "Пример: 'ул. Покерная, 123' или 'Покерный клуб Magnum'"
        )
        await state.update_data(max_players=max_players)
        
    except ValueError:
        await message.answer("❌ Введите корректное число игроков")

@dp.message(UserStates.admin_create_game_details)
async def process_game_location(message: Message, state: FSMContext):
    location = message.text.strip()
    data = await state.get_data()
    game_name = data.get('game_name')
    game_date = data.get('game_date')
    max_players = data.get('max_players')
    
    # Создаем игру
    game_id = db.create_game(
        game_name=game_name,
        game_date=game_date,
        max_players=max_players,
        game_type="Texas Holdem",
        buy_in=0.00,
        location=location,
        created_by=message.from_user.id
    )
    
    if game_id:
        await message.answer(
            f"✅ Игра успешно создана!\n\n"
            f"🎮 {game_name}\n"
            f"📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Макс. игроков: {max_players}\n"
            f"📍 {location}",
            reply_markup=get_admin_games_keyboard()
        )
    else:
        await message.answer("❌ Ошибка при создании игры")
    
    await state.clear()

# Показ предстоящих игр
@dp.message(F.text == "📅 Предстоящие игры")
async def upcoming_games_handler(message: Message):
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 На этой неделе пока нет запланированных игр")
        return
    
    games_text = "📅 ПРЕДСТОЯЩИЕ ИГРЫ:\n\n"
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        games_text += f"🎮 {game_name}\n"
        games_text += f"   📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
        games_text += f"   👥 {current_players}/{max_players} игроков\n"
        games_text += f"   📍 {location or 'Адрес не указан'}\n\n"
    
    await message.answer(games_text)

# Запись на игру
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

# Обработка выбора игры
@dp.callback_query(F.data.startswith("register_"))
async def process_game_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        await state.update_data(game_id=game_id)
        await callback.message.answer(
            f"🎮 Запись на игру:\n"
            f"📝 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Введите ваш игровой никнейм:"
        )
        await state.set_state(UserStates.waiting_for_player_name)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка выбора игры")

# Обновляем обработчик имени для работы с записями на игры
@dp.message(UserStates.waiting_for_player_name)
async def process_player_name(message: Message, state: FSMContext):
    player_name = message.text.strip()
    state_data = await state.get_data()
    game_id = state_data.get('game_id')
    
    # Если это запись на игру
    if game_id:
        success, result_message = db.register_player_for_game(game_id, player_name, message.from_user.id)
        
        if success:
            # Обновляем информацию об игре
            game = db.get_game_by_id(game_id)
            registrations = db.get_game_registrations(game_id)
            current_players = len([r for r in registrations if r[1] == 'registered'])
            max_players = game[4]
            
            await message.answer(
                f"{result_message}\n\n"
                f"🎮 {game[1]}\n"
                f"👤 Ваш ник: {player_name}\n"
                f"👥 Записано: {current_players}/{max_players} игроков",
                reply_markup=get_games_keyboard()
            )
        else:
            await message.answer(result_message, reply_markup=get_games_keyboard())
        
        await state.clear()
        return
    
    # Старая логика поиска рейтинга
    search_name = normalize_name(player_name)
    
    found_player = None
    
    # Поиск игрока (регистронезависимый с учетом ё/е)
    for name in players_rating:
        if normalize_name(name) == search_name:
            found_player = name
            break
    
    # Если точного совпадения нет, ищем по части имени
    if not found_player:
        for name in players_rating:
            name_words = normalize_name(name).split()
            search_words = search_name.split()
            if any(any(sw in nw or nw in sw for nw in name_words) for sw in search_words):
                found_player = name
                break
    
    # Если все еще не нашли, ищем по подстроке
    if not found_player:
        for name in players_rating:
            if search_name in normalize_name(name):
                found_player = name
                break
    
    if found_player:
        rating = players_rating[found_player]
        position = get_player_position(found_player)
        
        # ОБНОВЛЯЕМ данные карточек перед показом
        file_id = db.get_player_card(found_player)
        if file_id:
            try:
                await message.answer_photo(
                    file_id,
                    caption=f"👤 {found_player}\n⭐️ Рейтинг: {rating}\n📍 Место: {position}",
                    reply_markup=get_main_keyboard(message.from_user.id)
                )
            except Exception as e:
                await message.answer(
                    f"👤 {found_player}\n⭐️ Рейтинг: {rating}\n📍 Место: {position}\n"
                    f"❌ Ошибка загрузки карточки",
                    reply_markup=get_main_keyboard(message.from_user.id)
                )
        else:
            await message.answer(
                f"👤 {found_player}\n⭐️ Рейтинг: {rating}\n📍 Место: {position}\n"
                f"ℹ️ Карточка игрока готовится",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
    else:
        # Показываем похожих игроков для помощи
        similar_players = []
        for name in players_rating:
            if search_name and (search_name in normalize_name(name) or any(word.startswith(search_name) for word in normalize_name(name).split())):
                similar_players.append(name)
        
        if similar_players:
            similar_text = "\n".join([f"• {name}" for name in similar_players[:3]])
            await message.answer(
                f"❌ Игрок '{message.text.strip()}' не найден.\n\n"
                f"💡 Возможно вы искали:\n{similar_text}\n\n"
                "Попробуйте ввести другое имя или обратитесь к администратору.",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
        else:
            await message.answer(
                f"❌ Игрок '{message.text.strip()}' не найден.\n"
                "Проверьте имя или обратитесь к администратору.",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
    
    await state.clear()

# Показ списка игроков на игру
@dp.message(F.text == "📋 Списки игроков")
async def show_game_lists_handler(message: Message):
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр")
        return
    
    await message.answer(
        "📋 Выберите игру для просмотра списка игроков:",
        reply_markup=get_games_selection_keyboard(games, "list")
    )

# Обработка показа списка игроков
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
        game_info += f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
        game_info += f"📍 {game[6] or 'Адрес не указан'}\n"
        game_info += f"👥 Игроков: {len(registrations)}/{game[4]}\n\n"
        
        if registrations:
            game_info += "📋 СПИСОК ИГРОКОВ:\n"
            for i, (name, status, rating, user_id) in enumerate(registrations, 1):
                rating_text = f"⭐ {rating}" if rating else "⚪"
                status_icon = "✅" if status == 'registered' else "⏳"
                game_info += f"{i}. {name} {rating_text} {status_icon}\n"
        else:
            game_info += "📭 Пока никто не записался"
        
        await callback.message.answer(game_info)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при получении списка игроков")

# ========== АДМИН-УПРАВЛЕНИЕ ИГРАМИ ==========

@dp.message(F.text == "📋 Управление играми")
async def manage_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр")
        return
    
    games_text = "📅 АКТИВНЫЕ ИГРЫ:\n\n"
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        games_text += f"🎮 {game_name}\n"
        games_text += f"📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
        games_text += f"👥 {current_players}/{max_players} игроков\n"
        games_text += f"📍 {location or 'Адрес не указан'}\n\n"
    
    await message.answer(
        games_text + "🛠️ Выберите игру для управления:",
        reply_markup=get_games_selection_keyboard(games, "manage")
    )

# Обработка управления игрой
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

# Изменение лимита игроков
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

# Удаление игрока с игры
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
        # Отправляем уведомление игроку, если есть user_id
        registrations = db.get_game_registrations(game_id)
        user_id_to_notify = None
        for name, status, rating, user_id in registrations:
            if name == player_name and user_id:
                user_id_to_notify = user_id
                break
        
        if user_id_to_notify:
            try:
                game = db.get_game_by_id(game_id)
                await bot.send_message(
                    user_id_to_notify,
                    f"❌ ВАС УДАЛИЛИ С ИГРЫ\n\n"
                    f"🎮 {game[1]}\n"
                    f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Администратор удалил вас с этой игры."
                )
            except Exception as e:
                logging.error(f"❌ Ошибка отправки уведомления пользователю {user_id_to_notify}: {e}")
        
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

# Отмена игры
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_specific_game_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        game_id = int(callback.data.split('_')[1])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            return
        
        if db.cancel_game(game_id):
            # Рассылка уведомлений всем записавшимся
            registrations = db.get_game_registrations(game_id)
            user_ids = [user_id for name, status, rating, user_id in registrations if user_id]
            
            cancelled_count = 0
            for user_id in user_ids:
                try:
                    await bot.send_message(
                        user_id,
                        f"❌ ИГРА ОТМЕНЕНА\n\n"
                        f"🎮 {game[1]}\n"
                        f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n\n"
                        f"Игра была отменена администратором."
                    )
                    cancelled_count += 1
                except Exception as e:
                    logging.error(f"❌ Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            await callback.message.answer(
                f"✅ Игра отменена!\n"
                f"📨 Уведомления отправлены: {cancelled_count}/{len(user_ids)} игрокам",
                reply_markup=get_admin_games_keyboard()
            )
        else:
            await callback.message.answer("❌ Ошибка при отмене игры")
        
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при отмене игры")

# ========== ОСТАЛЬНЫЕ ФУНКЦИИ ==========

# Обработка кнопки "Мой рейтинг"
@dp.message(F.text == "🎯 Мой рейтинг")
async def my_rating_handler(message: Message, state: FSMContext):
    await message.answer("Введите ваше игровое имя:")
    await state.set_state(UserStates.waiting_for_player_name)

# Обработка кнопки "Общий рейтинг"
@dp.message(F.text == "🏆 Общий рейтинг")
async def full_rating_handler(message: Message):
    rating_text = "🏆 Общий рейтинг игроков:\n\n"
    
    sorted_players = sorted(players_rating.items(), key=lambda x: x[1], reverse=True)
    for i, (name, points) in enumerate(sorted_players, 1):
        rating_text += f"{i}. {name}: {points}\n"
    
    await message.answer(rating_text, reply_markup=get_main_keyboard(message.from_user.id))

# Обработка кнопки "Правила покера"
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

🎮 <b>Советую пройти мини-тест по покеру</b> чтобы закрепить знания о комбинациях!
"""
    
    try:
        photo_url = "https://i.pinimg.com/originals/d6/42/a4/d642a4866de6863efcb5b1c60017d562.png"
        
        await message.answer_photo(
            photo_url,
            caption=rules_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    except Exception as e:
        await message.answer(
            rules_text, 
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )

# Обработка кнопки "Тест по покеру"
@dp.message(F.text == "🎯 Тест по покеру")
async def poker_test_handler(message: Message, state: FSMContext):
    user_test_data[message.from_user.id] = {
        "current_question": 0,
        "score": 0,
        "answers": []
    }
    await send_question(message, state)

async def send_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_question = user_test_data[user_id]["current_question"]
    
    if current_question >= len(poker_test_questions):
        await finish_test(message, state)
        return
    
    question = poker_test_questions[current_question]
    question_text = f"❓ Вопрос {current_question + 1}/{len(poker_test_questions)}:\n\n{question['question']}"
    
    await message.answer(question_text, reply_markup=get_test_keyboard(current_question))
    await state.set_state(UserStates.poker_test)

# Обработка ответов на тест
@dp.message(UserStates.poker_test)
async def process_test_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "❌ Отменить тест":
        await message.answer("Тест отменен", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return
    
    try:
        answer_text = message.text.strip()
        answer_num = int(answer_text.split('.')[0]) - 1
        
        current_question = user_test_data[user_id]["current_question"]
        question = poker_test_questions[current_question]
        
        if answer_num < 0 or answer_num >= len(question["options"]):
            await message.answer(f"❌ Пожалуйста, выберите вариант от 1 до {len(question['options'])}")
            return
        
        is_correct = (answer_num == question["correct"])
        
        if is_correct:
            user_test_data[user_id]["score"] += 1
        
        user_test_data[user_id]["answers"].append(is_correct)
        
        if is_correct:
            await message.answer(f"✅ {question['explanation']}")
        else:
            correct_option = question["options"][question["correct"]]
            await message.answer(f"❌ Неправильно. {question['explanation']}\n\nПравильный ответ: {correct_option}")
        
        user_test_data[user_id]["current_question"] += 1
        await asyncio.sleep(2)
        await send_question(message, state)
        
    except (ValueError, IndexError):
        await message.answer(f"❌ Пожалуйста, выберите вариант ответа (1, 2, 3 или 4) нажав на кнопку")

async def finish_test(message: Message, state: FSMContext):
    user_id = message.from_user.id
    score = user_test_data[user_id]["score"]
    total = len(poker_test_questions)
    
    result_text = (
        f"🎉 Тест завершен!\n\n"
        f"📊 Ваш результат: {score}/{total}\n"
        f"📈 Процент правильных ответов: {score/total*100:.1f}%\n\n"
    )
    
    if score == total:
        result_text += "🏆 Отлично! Вы отлично знаете правила покера!"
    elif score >= total * 0.7:
        result_text += "👍 Хорошо! Вы хорошо разбираетесь в покере!"
    else:
        result_text += "📚 Есть куда расти! Повторите правила покера."
    
    await message.answer(result_text, reply_markup=get_main_keyboard(user_id))
    await state.clear()

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
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_keyboard(message.from_user.id))

# Обработка кнопки "Назад к играм"
@dp.message(F.text == "🔙 Назад к играм")
async def back_to_games_handler(message: Message):
    await message.answer("Возвращаемся к играм:", reply_markup=get_games_keyboard())

# Обработка кнопки "Админ-панель"
@dp.message(F.text == "🔙 Админ-панель")
async def back_to_admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Возвращаемся в админ-панель:", reply_markup=get_admin_keyboard())

async def cleanup_processed_starts():
    """Очистка старых записей в processed_starts"""
    while True:
        await asyncio.sleep(60)
        current_time = asyncio.get_event_loop().time()
        global processed_starts
        processed_starts = {uid: time for uid, time in processed_starts.items() 
                          if current_time - time < 300}

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен с исправленной системой игр!")
    
    asyncio.create_task(cleanup_processed_starts())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())