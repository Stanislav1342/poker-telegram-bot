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
    admin_create_game_players = State()
    admin_create_game_location = State()
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
    keyboard.add(KeyboardButton(text="🗑 Удалить все игры"))  # НОВАЯ КНОПКА
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
    keyboard.add(InlineKeyboardButton(text="❌ Удалить игру", callback_data=f"delete_game_{game_id}"))  # НОВАЯ КНОПКА
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games_manage"))
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
        # Переинициализируем базу данных
        db.init_db()
        
        await message.answer(
            "✅ Таблицы в базе данных созданы/проверены!\n\n"
            "Теперь используйте:\n"
            "/db_tables - посмотреть таблицы\n" 
            "/db_check - проверить состояние БД"
        )
        
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
        # ОБНОВЛЯЕМ данные из базы перед показом статистики
        global players_rating, player_photo_ids
        players_rating = db.get_all_players()
        player_photo_ids = db.get_all_cards()
        
        total_players = len(players_rating)
        total_cards = len(player_photo_ids)
        
        status_text = "🟢 БАЗА ДАННЫХ РАБОТАЕТ\n\n"
        status_text += f"📊 Статистика (актуальная):\n"
        status_text += f"• Игроков в базе: {total_players}\n"
        status_text += f"• Карточек в базе: {total_cards}\n"
        status_text += f"• Подключение к PostgreSQL: ✅ Активно\n\n"
        
        if players_rating:
            status_text += "📋 Топ игроков:\n"
            for i, (name, rating) in enumerate(list(players_rating.items()), 1):
                has_card = "🖼" if name in player_photo_ids else "❌"
                status_text += f"{i}. {name}: {rating} {has_card}\n"
        else:
            status_text += "📋 База игроков пуста\n"
        
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
    
    await message.answer(
        "👑 Панель администратора:",
        reply_markup=get_admin_keyboard()
    )

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
        "Или: Анна Мария 4.8\n\n"
        "Рейтинг по 5-балльной шкале"
    )
    await state.set_state(UserStates.admin_add_player)

@dp.message(UserStates.admin_add_player)
async def process_add_player(message: Message, state: FSMContext):
    try:
        # Разделяем сообщение на части
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Неверный формат. Пример: Иван Рунге 4.4")
            return
        
        # Последняя часть - рейтинг, остальные - имя игрока
        rating_str = parts[-1].replace(',', '.')
        player_name = ' '.join(parts[:-1])
        
        rating = float(rating_str)
        
        if rating < 0 or rating > 5:
            await message.answer("❌ Рейтинг должен быть от 0 до 5")
            return
        
        # Сохраняем в базу данных
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

# Редактирование рейтинга
@dp.message(F.text == "✏️ Изменить рейтинг")
async def update_rating_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not players_rating:
        await message.answer("❌ В базе нет игроков для редактирования")
        return
    
    players_list = "\n".join([f"• {name}" for name in players_rating.keys()])
    await message.answer(
        f"📋 Список игроков:\n{players_list}\n\n"
        "Введите данные в формате:\n"
        "Имя Новый_рейтинг\n\n"
        "Пример: Иван Рунге 4.7\n"
        "Или: Стас 4.2"
    )
    await state.set_state(UserStates.admin_update_rating)

@dp.message(UserStates.admin_update_rating)
async def process_update_rating(message: Message, state: FSMContext):
    try:
        # Разделяем сообщение на части
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Неверный формат. Пример: Иван Рунге 4.7")
            return
        
        # Последняя часть - рейтинг, остальные - имя игрока
        rating_str = parts[-1].replace(',', '.')
        search_name = normalize_name(' '.join(parts[:-1]))
        
        # Ищем игрока с учетом е/ё
        found_player = None
        for name in players_rating:
            if normalize_name(name) == search_name:
                found_player = name
                break
        
        if not found_player:
            await message.answer(f"❌ Игрок не найден")
            return
        
        rating = float(rating_str)
        
        if rating < 0 or rating > 5:
            await message.answer("❌ Рейтинг должен быть от 0 до 5")
            return
        
        # Обновляем рейтинг в базе
        if db.update_player_rating(found_player, rating):
            # Обновляем кэш
            players_rating[found_player] = rating
            await message.answer(
                f"✅ Рейтинг обновлен:\n👤 {found_player}\n⭐️ Новый рейтинг: {rating}",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(
                f"❌ Ошибка при обновлении рейтинга",
                reply_markup=get_admin_keyboard()
            )
        
    except ValueError:
        await message.answer("❌ Рейтинг должен быть числом. Пример: Иван Рунге 4.7")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

# Удаление игрока (админ)
@dp.message(F.text == "🗑 Удалить игрока")
async def remove_player_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not players_rating:
        await message.answer("❌ В базе нет игроков для удаления")
        return
    
    players_list = "\n".join([f"• {name}" for name in players_rating.keys()])
    await message.answer(
        f"📋 Список игроков:\n{players_list}\n\n"
        "Введите имя игрока для удаления:"
    )
    await state.set_state(UserStates.admin_remove_player)

@dp.message(UserStates.admin_remove_player)
async def process_remove_player(message: Message, state: FSMContext):
    search_name = normalize_name(message.text.strip())
    
    # Ищем игрока с учетом е/ё
    found_player = None
    for name in players_rating:
        if normalize_name(name) == search_name:
            found_player = name
            break
    
    if found_player and db.remove_player(found_player):
        # Обновляем кэш
        if found_player in players_rating:
            del players_rating[found_player]
        
        await message.answer(
            f"✅ Игрок '{found_player}' удален из базы",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            f"❌ Игрок не найден в базе",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

# Загрузка карточки игрока (админ)
@dp.message(F.text == "📤 Загрузить карточку")
async def upload_card_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "Отправьте карточку игрока как фото с подписью в формате:\n"
        "Имя_игрока\n\n"
        "Пример подписи к фото: Рунге"
    )

# Обработка загруженной карточки
@dp.message(F.photo)
async def process_player_card(message: Message):
    if not is_admin(message.from_user.id):
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
    
    photo = message.photo[-1]
    if db.save_player_card(player_name, photo.file_id):
        # ОБНОВЛЯЕМ кэш карточек сразу после загрузки
        global player_photo_ids
        player_photo_ids = db.get_all_cards()
        
        await message.answer(
            f"✅ Карточка для игрока '{player_name}' успешно загружена!\n"
            f"📸 Теперь игроки смогут получать эту карточку.\n"
            f"🔄 Статистика БД обновлена автоматически.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            f"❌ Ошибка при сохранении карточки в базу данных",
            reply_markup=get_admin_keyboard()
        )

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
        await state.set_state(UserStates.admin_create_game_players)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ\nПример: 15.01.2024 19:30")

@dp.message(UserStates.admin_create_game_players)
async def process_game_players(message: Message, state: FSMContext):
    try:
        max_players = int(message.text.strip())
        
        if max_players <= 0:
            await message.answer("❌ Количество игроков должно быть больше 0")
            return
        
        await state.update_data(max_players=max_players)
        await message.answer(
            "📍 Введите адрес проведения игры:\n\n"
            "Пример: 'ул. Покерная, 123' или 'Покерный клуб Magnum'"
        )
        await state.set_state(UserStates.admin_create_game_location)
        
    except ValueError:
        await message.answer("❌ Введите корректное число игроков")

@dp.message(UserStates.admin_create_game_location)
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
        games_text += f"📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
        games_text += f"📍 {location or 'Адрес не указан'}\n"
        games_text += f"👥 Игроков: {current_players}/{max_players}\n\n"
    
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

# Отмена записи на игру
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

# Обработка отмены записи
@dp.callback_query(F.data.startswith("cancelreg_"))
async def process_cancel_registration(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        # Получаем запись пользователя
        registrations = db.get_user_registrations(user_id)
        player_name = None
        
        for reg in registrations:
            if reg[0] == game_id:
                player_name = reg[4]
                break
        
        if not player_name:
            await callback.message.answer("❌ Запись не найдена")
            return
        
        # Удаляем запись
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

# Мои записи
@dp.message(F.text == "👥 Мои записи")
async def my_registrations_handler(message: Message):
    """Показать игры, на которые записан пользователь"""
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
        
        # Формируем список записей
        registrations_text = "👥 ВАШИ ЗАПИСИ НА ИГРЫ:\n\n"
        
        for reg in registrations:
            game_id, game_name, game_date, location, player_name = reg
            registrations_text += f"🎮 {game_name}\n"
            registrations_text += f"📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
            registrations_text += f"📍 {location or 'Адрес не указан'}\n"
            registrations_text += f"👤 Ваш ник: {player_name}\n\n"
        
        await message.answer(registrations_text, reply_markup=get_games_keyboard())
        
    except Exception as e:
        logging.error(f"❌ Ошибка получения записей пользователя: {e}")
        await message.answer(
            "❌ Ошибка при получении ваших записей",
            reply_markup=get_games_keyboard()
        )

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

# Показ списка игроков на игру (для пользователей)
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

# Обработка показа списка игроков для конкретной игры
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
                game_info += f"{i}. {name}\n"
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

# НОВАЯ ФУНКЦИЯ: Списки всех игроков на всех играх (для админ-панели)
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
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status = game
        registrations = db.get_game_registrations(game_id)
        
        all_players_text += f"🎮 {game_name}\n"
        all_players_text += f"📅 {game_date.strftime('%d.%m.%Y %H:%M')}\n"
        all_players_text += f"📍 {location or 'Адрес не указан'}\n"
        all_players_text += f"👥 Игроков: {len(registrations)}/{max_players}\n"
        
        if registrations:
            all_players_text += "📋 СПИСОК ИГРОКОВ:\n"
            for i, (name, status, rating, user_id) in enumerate(registrations, 1):
                all_players_text += f"{i}. {name}\n"
        else:
            all_players_text += "📭 Пока никто не записался\n"
        
        all_players_text += "\n"
    
    await message.answer(all_players_text)

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

# ========== НОВАЯ СИСТЕМА РАССЫЛКИ ЧЕРЕЗ КНОПКИ ==========

@dp.message(F.text == "📢 Рассылка")
async def broadcast_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    # Создаем инлайн-клавиатуру для выбора типа рассылки
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📢 Всем игрокам", callback_data="broadcast_all"))
    keyboard.add(InlineKeyboardButton(text="🎮 По конкретной игре", callback_data="broadcast_game_select"))
    keyboard.adjust(1)
    
    await message.answer(
        "📢 СИСТЕМА РАССЫЛКИ\n\n"
        "Выберите тип рассылки:",
        reply_markup=keyboard.as_markup()
    )

# Обработка выбора "Всем игрокам"
@dp.callback_query(F.data == "broadcast_all")
async def broadcast_all_handler(callback: types.CallbackQuery, state: FSMContext):
    user_ids = db.get_all_game_registrations()
    
    if not user_ids:
        await callback.message.answer("❌ Нет игроков для рассылки")
        await callback.answer()
        return
    
    await state.update_data(broadcast_type="all", user_ids=user_ids)
    
    await callback.message.answer(
        f"📢 Рассылка ВСЕМ игрокам\n"
        f"👥 Получателей: {len(user_ids)}\n\n"
        "Введите сообщение для рассылки:"
    )
    await state.set_state(UserStates.admin_broadcast_message)
    await callback.answer()

# Обработка выбора "По конкретной игре"
@dp.callback_query(F.data == "broadcast_game_select")
async def broadcast_game_select_handler(callback: types.CallbackQuery):
    games = db.get_upcoming_games()
    
    if not games:
        await callback.message.answer("🎉 Нет активных игр для рассылки")
        await callback.answer()
        return
    
    # Создаем клавиатуру с играми для рассылки
    keyboard = InlineKeyboardBuilder()
    for game in games:
        game_id, game_name, game_date, game_type, max_players, buy_in, location, status = game
        registrations = db.get_game_registrations(game_id)
        current_players = len([r for r in registrations if r[1] == 'registered'])
        
        keyboard.add(InlineKeyboardButton(
            text=f"🎮 {game_name} ({current_players} игр.)",
            callback_data=f"broadcast_game_{game_id}"
        ))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="broadcast_back"))
    keyboard.adjust(1)
    
    await callback.message.answer(
        "📢 Выберите игру для рассылки:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

# Обработка выбора конкретной игры для рассылки
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
        
        await state.update_data(broadcast_type=f"game_{game_id}", user_ids=user_ids)
        
        await callback.message.answer(
            f"📢 Рассылка по игре:\n"
            f"🎮 {game[1]}\n"
            f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Получателей: {len(user_ids)}\n\n"
            "Введите сообщение для рассылки:"
        )
        await state.set_state(UserStates.admin_broadcast_message)
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при выборе игры")
        await callback.answer()

# Кнопка "Назад" в рассылке
@dp.callback_query(F.data == "broadcast_back")
async def broadcast_back_handler(callback: types.CallbackQuery):
    await broadcast_handler(callback.message)
    await callback.answer()

# ========== УДАЛЕНИЕ ВСЕХ ИГР ==========

@dp.message(F.text == "🗑 Удалить все игры")
async def delete_all_games_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    games = db.get_upcoming_games()
    
    if not games:
        await message.answer("🎉 Нет активных игр для удаления")
        return
    
    # Создаем клавиатуру с подтверждением
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

# Подтверждение удаления всех игр
@dp.callback_query(F.data == "confirm_delete_all_games")
async def confirm_delete_all_games_handler(callback: types.CallbackQuery):
    try:
        if db.delete_all_games():
            await callback.message.answer(
                f"✅ Все игры успешно удалены!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await callback.message.answer(
                "❌ Ошибка при удалении всех игр",
                reply_markup=get_admin_keyboard()
            )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"❌ Ошибка удаления всех игр: {e}")
        await callback.message.answer(
            "❌ Ошибка при удалении игр",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

# Отмена удаления всех игр
@dp.callback_query(F.data == "cancel_delete_all_games")
async def cancel_delete_all_games_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "❌ Удаление всех игр отменено",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

# ========== УДАЛЕНИЕ КОНКРЕТНОЙ ИГРЫ ==========

# Обработка удаления конкретной игры
@dp.callback_query(F.data.startswith("delete_game_"))
async def delete_specific_game_handler(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[2])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            await callback.answer()
            return
        
        # Создаем клавиатуру с подтверждением
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

# Подтверждение удаления конкретной игры
@dp.callback_query(F.data.startswith("confirm_delete_game_"))
async def confirm_delete_specific_game_handler(callback: types.CallbackQuery):
    try:
        game_id = int(callback.data.split('_')[3])
        game = db.get_game_by_id(game_id)
        
        if not game:
            await callback.message.answer("❌ Игра не найдена")
            await callback.answer()
            return
        
        # Удаляем игру
        if db.delete_game(game_id):
            await callback.message.answer(
                f"✅ Игра удалена!\n\n"
                f"🎮 {game[1]}\n"
                f"📅 {game[2].strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_admin_games_keyboard()
            )
        else:
            await callback.message.answer(
                "❌ Ошибка при удалении игры",
                reply_markup=get_admin_games_keyboard()
            )
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.message.answer("❌ Ошибка при удалении игры")
        await callback.answer()

# Отмена удаления конкретной игры
@dp.callback_query(F.data.startswith("cancel_delete_game_"))
async def cancel_delete_specific_game_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "❌ Удаление игры отменено",
        reply_markup=get_admin_games_keyboard()
    )
    await callback.answer()

# Кнопка "Назад" в управлении играми
@dp.callback_query(F.data == "back_to_games_manage")
async def back_to_games_manage_handler(callback: types.CallbackQuery):
    await manage_games_handler(callback.message)
    await callback.answer()

# ========== ОБРАБОТКА РАССЫЛКИ ==========

@dp.message(UserStates.admin_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    data = await state.get_data()
    user_ids = data.get('user_ids', [])
    broadcast_type = data.get('broadcast_type', 'manual')
    
    if not user_ids:
        await message.answer("❌ Нет получателей для рассылки")
        await state.clear()
        return
    
    sent_count = 0
    failed_count = 0
    
    # Отправляем сообщение всем пользователям
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, f"📢 ОБЪЯВЛЕНИЕ:\n\n{message.text}")
            sent_count += 1
            # Небольшая задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")
            failed_count += 1
    
    # Формируем отчет
    if broadcast_type == "all":
        report = f"📢 Рассылка ВСЕМ игрокам завершена!\n"
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

# ========== ОСНОВНЫЕ ФУНКЦИИ БОТА ==========

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

🎮 <b>Советую пройти мини-тест по покеру</b> чтобы закрепить знаний о комбинациях!
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
@dp.message(F.text == "🧠 Тест по покеру")
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