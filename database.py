import os
import logging
import pg8000

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        if self.conn:
            self.init_db()
    
    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            # Используем внешний хост Railway
            host = "switchyard.proxy.rlwy.net"
            port = 55878
            username = "postgres"
            password = "MiqwIxJxtnQoJaVLTEWsZcnobHWKOOqO"
            database = "railway"
            
            logging.info(f"🔄 Подключаемся к {host}:{port}")
            
            self.conn = pg8000.connect(
                user=username,
                password=password,
                host=host,
                port=port,
                database=database,
                timeout=30
            )
            logging.info("✅ Подключение к PostgreSQL установлено")
        except Exception as e:
            logging.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
    
    def init_db(self):
        """Инициализация таблиц"""
        try:
            if not self.conn:
                return
            
            cursor = self.conn.cursor()
            
            # ★★★ НОВАЯ ТАБЛИЦА: пользователи бота ★★★
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    rating REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица карточек игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_cards (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(100) UNIQUE NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ★★★ ОБНОВЛЯЕМ ТАБЛИЦУ GAMES - ДОБАВЛЯЕМ ПОЛЯ ★★★
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id SERIAL PRIMARY KEY,
                    game_name VARCHAR(200) NOT NULL DEFAULT 'Покерная игра',
                    game_date TIMESTAMP NOT NULL,
                    game_type VARCHAR(50) DEFAULT 'Texas Holdem',
                    max_players INTEGER NOT NULL,
                    buy_in DECIMAL(10,2) DEFAULT 0.00,
                    location VARCHAR(200),
                    status VARCHAR(20) DEFAULT 'upcoming',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ★★★ ДОБАВЛЯЕМ КОЛОНКУ HOST ЕСЛИ ЕЁ НЕТ ★★★
            try:
                cursor.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS host VARCHAR(100) DEFAULT 'Капоне'")
            except Exception as e:
                logging.info(f"ℹ️ Колонка host уже существует: {e}")
            
            # ★★★ ДОБАВЛЯЕМ КОЛОНКУ END_TIME ЕСЛИ ЕЁ НЕТ ★★★
            try:
                cursor.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS end_time VARCHAR(10) DEFAULT '22:00'")
            except Exception as e:
                logging.info(f"ℹ️ Колонка end_time уже существует: {e}")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_registrations (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
                    player_name VARCHAR(100) NOT NULL,
                    user_id BIGINT,
                    status VARCHAR(20) DEFAULT 'registered',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(game_id, player_name)
                )
            ''')
            
            self.conn.commit()
            cursor.close()
            logging.info("✅ Таблицы в PostgreSQL инициализированы")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
    
    def save_bot_user(self, user_id, username=None, first_name=None, last_name=None):
        """Сохранение информации о пользователе бота"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO bot_users (user_id, username, first_name, last_name) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name
            ''', (user_id, username, first_name, last_name))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения пользователя бота: {e}")
            return False
    
    def get_all_bot_users(self):
        """Получение всех пользователей бота"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT user_id FROM bot_users')
            user_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return user_ids
        except Exception as e:
            logging.error(f"❌ Ошибка получения всех пользователей бота: {e}")
            return []

    # ★★★ МЕТОДЫ ДЛЯ ИГРОКОВ ★★★
    def add_player(self, name, rating):
        """Добавление игрока"""
        try:
            if not self.conn:
                return False
            
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO players (name, rating) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET rating = EXCLUDED.rating",
                (name, rating)
            )
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка добавления игрока: {e}")
            return False
    
    def update_player_rating(self, name, new_rating):
        """Обновление рейтинга игрока"""
        try:
            if not self.conn:
                return False
            
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE players SET rating = %s WHERE name = %s",
                (new_rating, name)
            )
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления рейтинга: {e}")
            return False
    
    def remove_player(self, name):
        """Удаление игрока"""
        try:
            if not self.conn:
                return False
            
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM player_cards WHERE player_name = %s", (name,))
            cursor.execute("DELETE FROM players WHERE name = %s", (name,))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игрока: {e}")
            return False
    
    def get_all_players(self):
        """Получение всех игроков"""
        try:
            if not self.conn:
                return {}
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, rating FROM players ORDER BY rating DESC")
            players = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return players
        except Exception as e:
            logging.error(f"❌ Ошибка получения игроков: {e}")
            return {}
    
    def save_player_card(self, player_name, file_id):
        """Сохранение карточки игрока"""
        try:
            if not self.conn:
                return False
            
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO player_cards (player_name, file_id) VALUES (%s, %s) ON CONFLICT (player_name) DO UPDATE SET file_id = EXCLUDED.file_id",
                (player_name, file_id)
            )
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения карточки: {e}")
            return False
    
    def get_player_card(self, player_name):
        """Получение карточки игрока"""
        try:
            if not self.conn:
                return None
            
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT file_id FROM player_cards WHERE player_name = %s", 
                (player_name,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"❌ Ошибка получения карточки: {e}")
            return None
    
    def get_all_cards(self):
        """Получение всех карточек"""
        try:
            if not self.conn:
                return {}
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT player_name, file_id FROM player_cards")
            cards = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return cards
        except Exception as e:
            logging.error(f"❌ Ошибка получения карточек: {e}")
            return {}

    # ★★★ ОБНОВЛЕННЫЙ МЕТОД СОЗДАНИЯ ИГРЫ ★★★
    def create_game(self, game_name, game_date, max_players, game_type, buy_in, location, host=None, end_time=None, created_by=None):
        """Создание новой игры"""
        try:
            logging.info(f"🔄 Создание игры: {game_name}, {game_date}, {max_players}, {buy_in}, {location}, {host}, {end_time}")
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO games (game_name, game_date, max_players, game_type, buy_in, location, host, end_time, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (game_name, game_date, max_players, game_type, buy_in, location, host, end_time, created_by))
            game_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            logging.info(f"✅ Игра создана с ID: {game_id}")
            return game_id
        except Exception as e:
            logging.error(f"❌ Ошибка создания игры: {e}")
            return None

    def register_player_for_game(self, game_id, player_name, user_id):
        """Запись игрока на игру"""
        try:
            # Проверяем есть ли место на игре
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM game_registrations 
                WHERE game_id = %s AND status = 'registered'
            ''', (game_id,))
            current_players = cursor.fetchone()[0]
            
            cursor.execute('SELECT max_players FROM games WHERE id = %s', (game_id,))
            max_players = cursor.fetchone()[0]
            
            if current_players >= max_players:
                cursor.close()
                return False, "❌ На эту игру уже набрано максимальное количество игроков"
            
            # Записываем игрока
            cursor.execute('''
                INSERT INTO game_registrations (game_id, player_name, user_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (game_id, player_name) DO UPDATE SET status = 'registered'
            ''', (game_id, player_name, user_id))
            
            self.conn.commit()
            cursor.close()
            return True, "✅ Вы успешно записаны на игру!"
        except Exception as e:
            logging.error(f"❌ Ошибка записи на игру: {e}")
            return False, "❌ Ошибка при записи на игру"

    # ★★★ ОБНОВЛЕННЫЙ МЕТОД ПОЛУЧЕНИЯ ИГР ★★★
    def get_upcoming_games(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time
                FROM games 
                WHERE status = 'upcoming'
                ORDER BY game_date
            ''')
            games = cursor.fetchall()
            cursor.close()
            
            # Логируем для отладки
            logging.info(f"📊 Найдено игр: {len(games)}")
            for game in games:
                logging.info(f"🎮 Игра: {game[1]}, Дата: {game[2]}, Статус: {game[7]}")
            
            return games
        except Exception as e:
            logging.error(f"❌ Ошибка получения игр: {e}")
            return []
    
    def get_game_registrations(self, game_id):
        """Получение списка записавшихся на игру"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT r.player_name, r.status, p.rating, r.user_id
                FROM game_registrations r
                LEFT JOIN players p ON r.player_name = p.name
                WHERE r.game_id = %s
                ORDER BY r.registered_at
            ''', (game_id,))
            registrations = cursor.fetchall()
            cursor.close()
            return registrations
        except Exception as e:
            logging.error(f"❌ Ошибка получения записей: {e}")
            return []

    # ★★★ ОБНОВЛЕННЫЙ МЕТОД ПОЛУЧЕНИЯ ИГРЫ ПО ID ★★★
    def get_game_by_id(self, game_id):
        """Получение информации об игре по ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, game_name, game_date, game_type, max_players, buy_in, location, status, host, end_time
                FROM games WHERE id = %s
            ''', (game_id,))
            game = cursor.fetchone()
            cursor.close()
            return game
        except Exception as e:
            logging.error(f"❌ Ошибка получения игры: {e}")
            return None

    def remove_player_from_game(self, game_id, player_name):
        """Удаление игрока из игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                DELETE FROM game_registrations 
                WHERE game_id = %s AND player_name = %s
            ''', (game_id, player_name))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игрока из игры: {e}")
            return False

    def update_game_max_players(self, game_id, new_max_players):
        """Обновление максимального количества игроков"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE games SET max_players = %s WHERE id = %s
            ''', (new_max_players, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления лимита игроков: {e}")
            return False

    def cancel_game(self, game_id):
        """Отмена игры (изменение статуса)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE games SET status = 'cancelled' WHERE id = %s
            ''', (game_id,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка отмены игры: {e}")
            return False

    def delete_game(self, game_id):
        """Полное удаление игры из базы данных"""
        try:
            cursor = self.conn.cursor()
            
            # Сначала удаляем записи о регистрациях (из-за внешнего ключа)
            cursor.execute('DELETE FROM game_registrations WHERE game_id = %s', (game_id,))
            
            # Затем удаляем саму игру
            cursor.execute('DELETE FROM games WHERE id = %s', (game_id,))
            
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игры {game_id}: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                pass
            return False

    def delete_all_games(self):
        """Удаление всех игр"""
        try:
            cursor = self.conn.cursor()
            
            # Удаляем все регистрации
            cursor.execute('DELETE FROM game_registrations')
            
            # Удаляем все игры
            cursor.execute('DELETE FROM games')
            
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка удаления всех игр: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                pass
            return False

    def get_game_registrations_by_game(self, game_id):
        """Получение user_id записавшихся на конкретную игру"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_id FROM game_registrations 
                WHERE game_id = %s AND user_id IS NOT NULL
            ''', (game_id,))
            user_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return user_ids
        except Exception as e:
            logging.error(f"❌ Ошибка получения user_id для игры: {e}")
            return []

    def get_user_registrations(self, user_id):
        """Получение всех записей пользователя на игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT gr.game_id, g.game_name, g.game_date, g.location, gr.player_name
                FROM game_registrations gr
                JOIN games g ON gr.game_id = g.id
                WHERE gr.user_id = %s AND gr.status = 'registered' AND g.status = 'upcoming'
                ORDER BY g.game_date
            ''', (user_id,))
            registrations = cursor.fetchall()
            cursor.close()
            return registrations
        except Exception as e:
            logging.error(f"❌ Ошибка получения записей пользователя: {e}")
            return []

# Глобальный экземпляр базы данных
db = Database()