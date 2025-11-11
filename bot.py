import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
from database import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_player_name = State()
    admin_add_player = State()
    admin_remove_player = State()
    admin_update_rating = State()
    poker_test = State()

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
    keyboard.add(KeyboardButton(text="🎮 Тест по покеру"))
    
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
    keyboard.add(KeyboardButton(text="📊 Статистика БД"))
    keyboard.add(KeyboardButton(text="🔙 Главное меню"))
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

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

@dp.message(Command("db_tables"))
async def db_tables_handler(message: Message):
    """Показать все таблицы в базе данных"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        if tables:
            tables_text = "📋 ТАБЛИЦЫ В БАЗЕ ДАННЫХ:\n\n"
            for table in tables:
                tables_text += f"• {table}\n"
        else:
            tables_text = "📭 В базе данных нет таблиц\n\nИспользуйте /db_init для создания"
        
        await message.answer(tables_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("db_stats"))
async def db_stats_handler(message: Message):
    """Подробная статистика базы данных"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        cursor = db.conn.cursor()
        
        # Количество записей в players
        cursor.execute("SELECT COUNT(*) FROM players")
        players_count = cursor.fetchone()[0]
        
        # Количество записей в player_cards
        cursor.execute("SELECT COUNT(*) FROM player_cards")
        cards_count = cursor.fetchone()[0]
        
        # Размер базы данных
        cursor.execute("SELECT pg_size_pretty(pg_database_size('railway'))")
        db_size = cursor.fetchone()[0]
        
        # Время работы базы
        cursor.execute("SELECT NOW() - pg_postmaster_start_time()")
        uptime = cursor.fetchone()[0]
        
        cursor.close()
        
        stats_text = "📊 ПОДРОБНАЯ СТАТИСТИКА БАЗЫ ДАННЫХ:\n\n"
        stats_text += f"🗃️ Размер базы: {db_size}\n"
        stats_text += f"⏱️ Время работы: {str(uptime).split('.')[0]}\n\n"
        stats_text += f"👤 Игроков в БД: {players_count}\n"
        stats_text += f"🖼 Карточек в БД: {cards_count}\n\n"
        stats_text += f"💾 Игроков в кэше: {len(players_rating)}\n"
        stats_text += f"📸 Карточек в кэше: {len(player_photo_ids)}"
        
        await message.answer(stats_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\n\nВозможно таблицы не созданы. Используйте /db_init")

@dp.message(Command("force_check"))
async def force_check_handler(message: Message):
    """Принудительная проверка и создание таблиц"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Принудительно создаем таблицы
        db.init_db()
        
        # Проверяем что таблицы есть
        cursor = db.conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        # Добавляем тестовую запись
        test_added = db.add_player("ТестовыйИгрок", 4.0)
        
        check_text = "🔍 РЕЗУЛЬТАТ ПРОВЕРКИ:\n\n"
        check_text += f"📋 Таблицы в БД: {tables}\n"
        check_text += f"✅ Тестовый игрок добавлен: {test_added}\n"
        
        if "players" in tables and "player_cards" in tables:
            check_text += "🎉 Таблицы созданы и работают!\n"
        else:
            check_text += "❌ Проблема с созданием таблиц\n"
            
        await message.answer(check_text)
        
    except Exception as e:
        await message.answer(f"❌ Критическая ошибка: {e}")

@dp.message(Command("debug_data"))
async def debug_data_handler(message: Message):
    """Отладочная информация о данных"""
    if not is_admin(message.from_user.id):
        return
    
    debug_text = "🐛 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ:\n\n"
    
    debug_text += "💾 ДАННЫЕ В ПАМЯТИ:\n"
    debug_text += f"• players_rating: {players_rating}\n"
    debug_text += f"• player_photo_ids: {player_photo_ids}\n\n"
    
    # Проверяем подключение к БД
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        db_players_count = cursor.fetchone()[0]
        cursor.close()
        
        debug_text += f"🗄️ ДАННЫЕ В POSTGRESQL:\n"
        debug_text += f"• Игроков в БД: {db_players_count}\n"
        
    except Exception as e:
        debug_text += f"🗄️ POSTGRESQL: ❌ Ошибка - {e}\n"
    
    await message.answer(debug_text)

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
            for i, (name, rating) in enumerate(list(players_rating.items())[:5], 1):
                has_card = "🖼" if name in player_photo_ids else "❌"
                status_text += f"{i}. {name}: {rating} {has_card}\n"
        else:
            status_text += "📋 База игроков пуста\n"
        
        await message.answer(status_text, reply_markup=get_admin_keyboard())
        
    except Exception as e:
        await message.answer(f"🔴 ОШИБКА БАЗЫ ДАННЫХ:\n{str(e)}")

@dp.message(Command("get_rules_photo_id"))
async def get_rules_photo_id_handler(message: Message):
    """Получить file_id фото для правил"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = db.get_player_card("rules_photo")
    if file_id:
        await message.answer(f"🆔 File_ID для фото правил:\n`{file_id}`", parse_mode="Markdown")
    else:
        await message.answer("❌ Фото для правил еще не загружено")

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

# ========== ОСНОВНЫЕ ФУНКЦИИ БОТА ==========

@dp.message(Command("start"))
async def start_handler(message: Message, command: CommandObject):
    # Игнорируем повторные вызовы /start с параметрами
    if command.args:
        return
    
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

# Поиск рейтинга по имени + отправка карточки
@dp.message(UserStates.waiting_for_player_name)
async def process_player_name(message: Message, state: FSMContext):
    search_name = normalize_name(message.text.strip())
    
    found_player = None
    
    # Поиск игрока (регистронезависимый с учетом ё/е)
    # 1. Сначала ищем точное совпадение
    for name in players_rating:
        if normalize_name(name) == search_name:
            found_player = name
            break
    
    # 2. Если точного совпадения нет, ищем по части имени
    if not found_player:
        for name in players_rating:
            # Разбиваем имя на слова и ищем совпадение с любым словом
            name_words = normalize_name(name).split()
            search_words = search_name.split()
            if any(any(sw in nw or nw in sw for nw in name_words) for sw in search_words):
                found_player = name
                break
    
    # 3. Если все еще не нашли, ищем по подстроке
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

🃏 <b>Комбинации (от старшей к младшей):</b>

🎮 <b>Советую пройти мини-тест по покеру</b> чтобы закрепить знания о комбинациях!
"""
    
    try:
        # Используем прямую ссылку на фото
        photo_url = "https://i.pinimg.com/originals/d6/42/a4/d642a4866de6863efcb5b1c60017d562.png"
        
        await message.answer_photo(
            photo_url,
            caption=rules_text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    except Exception as e:
        # Если фото не загружается, отправляем только текст
        await message.answer(
            rules_text, 
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id)
        )

# Обработка кнопки "Тест по покеру"
@dp.message(F.text == "🎮 Тест по покеру")
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

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен с исправлениями е/ё и красивыми правилами!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())