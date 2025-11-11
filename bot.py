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
from database import db  # ✅ Импортируем PostgreSQL базу

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_player_name = State()
    admin_add_player = State()
    admin_remove_player = State()
    poker_test = State()

# Загружаем данные из базы при запуске
players_rating = db.get_all_players()
player_photo_ids = db.get_all_cards()

# Данные для теста по покеру
poker_test_questions = [
    {
        "question": "Какая комбинация СТАРШЕ?",
        "options": ["Флеш", "Стрит", "Фулл-хаус", "Каре"],
        "correct": 3,  # Каре (4-й вариант, индекс 3)
        "explanation": "Каре > Фулл-хаус > Флеш > Стрит"
    },
    {
        "question": "Сколько карт в комбинации 'Каре'?",
        "options": ["3 карты", "4 карты", "5 карт", "6 карт"],
        "correct": 1,  # 4 карты (2-й вариант, индекс 1)
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
        "correct": 1,  # 5 карт одной масти (2-й вариант, индекс 1)
        "explanation": "Флеш - 5 карт одной масти"
    },
    {
        "question": "Какая комбинация САМАЯ СТАРШАЯ?",
        "options": ["Флеш-рояль", "Стрит-флеш", "Каре", "Фулл-хаус"],
        "correct": 0,  # Флеш-рояль (1-й вариант, индекс 0)
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
        "correct": 1,  # 5 карт по порядку (2-й вариант, индекс 1)
        "explanation": "Стрит - 5 карт по порядку любой масти"
    }
]

# Переменные для теста
user_test_data = {}

# Проверка является ли пользователь админом
def is_admin(user_id):
    admin_ids = [1308823467]  # Ваш ID
    return user_id in admin_ids

# Клавиатура главного меню
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🎯 Мой рейтинг"))
    keyboard.add(KeyboardButton(text="🏆 Общий рейтинг"))
    keyboard.add(KeyboardButton(text="📚 Правила покера"))
    keyboard.add(KeyboardButton(text="🎮 Тест по покеру"))
    
    # Добавляем кнопку админа только для администратора
    if is_admin(user_id):
        keyboard.add(KeyboardButton(text="👑 Админ-панель"))
    
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

# Админ клавиатура
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="➕ Добавить игрока"))
    keyboard.add(KeyboardButton(text="🗑 Удалить игрока"))
    keyboard.add(KeyboardButton(text="📤 Загрузить карточку"))
    keyboard.add(KeyboardButton(text="📊 Статистика"))
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

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = (
        "🎯 Добро пожаловать в покер-клуб HeartPipes!\n\n"
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
        await message.answer(
            f"❌ Игрок '{player_name}' не найден.\n"
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
        rating_text += f"{i}. {name}: {points}\n"  # ✅ Убрали "баллов"
    
    await message.answer(rating_text, reply_markup=get_main_keyboard(message.from_user.id))

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
    
    await message.answer(rules_text, reply_markup=get_main_keyboard(message.from_user.id))

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

# Обработка ответов на тест - ИСПРАВЛЕННАЯ ВЕРСИЯ
@dp.message(UserStates.poker_test)
async def process_test_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "❌ Отменить тест":
        await message.answer("Тест отменен", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return
    
    try:
        # Парсим номер ответа (1., 2., 3., 4.)
        answer_text = message.text.strip()
        answer_num = int(answer_text.split('.')[0]) - 1
        
        current_question = user_test_data[user_id]["current_question"]
        question = poker_test_questions[current_question]
        
        # Проверяем что номер ответа в допустимом диапазоне
        if answer_num < 0 or answer_num >= len(question["options"]):
            await message.answer(f"❌ Пожалуйста, выберите вариант от 1 до {len(question['options'])}")
            return
        
        # Проверяем ответ (правильный ответ хранится в question["correct"])
        is_correct = (answer_num == question["correct"])
        
        # Обновляем счетчик
        if is_correct:
            user_test_data[user_id]["score"] += 1
        
        # Сохраняем ответ
        user_test_data[user_id]["answers"].append(is_correct)
        
        # Отправляем объяснение
        if is_correct:
            await message.answer(f"✅ {question['explanation']}")
        else:
            correct_option = question["options"][question["correct"]]
            await message.answer(f"❌ Неправильно. {question['explanation']}\n\nПравильный ответ: {correct_option}")
        
        # Переходим к следующему вопросу
        user_test_data[user_id]["current_question"] += 1
        await asyncio.sleep(2)  # Пауза перед следующим вопросом
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

# Админ команды
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
        "Имя Рейтинг\n\n"
        "Пример: Стас 4.4\n"
        "Или: Стас 4,4\n\n"
        "Рейтинг по 5-балльной шкале"
    )
    await state.set_state(UserStates.admin_add_player)

# Обработка добавления игрока
@dp.message(UserStates.admin_add_player)
async def process_add_player(message: Message, state: FSMContext):
    try:
        data = message.text.split()
        if len(data) != 2:
            await message.answer("❌ Неверный формат. Пример: Стас 4.4")
            return
        
        name = data[0]
        rating_str = data[1].replace(',', '.')
        rating = float(rating_str)
        
        if rating < 0 or rating > 5:
            await message.answer("❌ Рейтинг должен быть от 0 до 5")
            return
        
        # Сохраняем в базу данных
        if db.add_player(name, rating):
            players_rating[name] = rating  # Обновляем кэш
            await message.answer(
                f"✅ Игрок добавлен:\n👤 {name}\n⭐️ Рейтинг: {rating}",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer("❌ Ошибка при добавлении игрока в базу")
        
    except ValueError:
        await message.answer("❌ Рейтинг должен быть числом. Пример: Стас 4.4 или Стас 4,4")
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

# Обработка удаления игрока
@dp.message(UserStates.admin_remove_player)
async def process_remove_player(message: Message, state: FSMContext):
    player_name = message.text.strip()
    
    if db.remove_player(player_name):
        # Обновляем кэш
        if player_name in players_rating:
            del players_rating[player_name]
        
        await message.answer(
            f"✅ Игрок '{player_name}' удален из базы",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            f"❌ Игрок '{player_name}' не найден в базе",
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
    
    # Сохраняем file_id в базу данных
    photo = message.photo[-1]
    if db.save_player_card(player_name, photo.file_id):
        await message.answer(
            f"✅ Карточка для игрока '{player_name}' успешно загружена и сохранена!\n"
            f"📸 Теперь игроки смогут получать эту карточку даже после перезапуска бота.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            f"❌ Ошибка при сохранении карточки в базу данных",
            reply_markup=get_admin_keyboard()
        )

# Команда для просмотра статистики (админ)
@dp.message(F.text == "📊 Статистика")
async def stats_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    total_players = len(players_rating)
    players_with_cards = len(db.get_all_cards())
    
    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👤 Всего игроков: {total_players}\n"
        f"🖼 Игроков с карточками: {players_with_cards}\n"
        f"📈 Загружено карточек: {players_with_cards}/{total_players}\n\n"
        f"💾 Данные сохраняются в PostgreSQL\n"
        f"🔄 Перезапуск бота не удалит данные!"
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
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_keyboard(message.from_user.id))

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Бот запущен с PostgreSQL (psycopg2) и исправленным тестом!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())