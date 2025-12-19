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
            
            # ★★★ НОВАЯ ТАБЛИЦА: рейтинг мафии (Городская мафия) ★★★
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mafia_city_ratings (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(100) NOT NULL,
                    file_id TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ★★★ НОВАЯ ТАБЛИЦА: рейтинг мафии (Мафия Картель) ★★★
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mafia_cartel_ratings (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(100) NOT NULL,
                    file_id TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ★★★ НОВАЯ ТАБЛИЦА: рейтинг покера ★★★
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poker_ratings (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(100) NOT NULL,
                    file_id TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            # ★★★ ДОБАВЛЯЕМ КОЛОНКУ ДЛЯ АФИШИ ИГР ★★★
            try:
                cursor.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS poster_file_id TEXT")
            except Exception as e:
                logging.info(f"ℹ️ Колонка poster_file_id уже существует: {e}")
            
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

    def update_game_host(self, game_id, new_host):
        """Обновление ведущего игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET host = %s WHERE id = %s', (new_host, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления ведущего: {e}")
            return False

    def update_game_time(self, game_id, start_time, end_time):
        """Обновление времени игры"""
        try:
            cursor = self.conn.cursor()
            # Получаем текущую дату
            cursor.execute('SELECT game_date FROM games WHERE id = %s', (game_id,))
            result = cursor.fetchone()
            if not result:
                return False
                
            current_date = result[0]
            
            # Создаем новую дату-время
            new_datetime = current_date.replace(
                hour=int(start_time.split(':')[0]),
                minute=int(start_time.split(':')[1])
            )
            
            cursor.execute(
                'UPDATE games SET game_date = %s, end_time = %s WHERE id = %s',
                (new_datetime, end_time, game_id)
            )
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления времени: {e}")
            return False

    def update_game_date(self, game_id, new_date):
        """Обновление даты игры"""
        try:
            cursor = self.conn.cursor()
            # Получаем текущее время
            cursor.execute('SELECT game_date FROM games WHERE id = %s', (game_id,))
            result = cursor.fetchone()
            if not result:
                return False
                
            current_datetime = result[0]
            
            # Сохраняем время, меняем только дату
            new_datetime = new_date.replace(
                hour=current_datetime.hour,
                minute=current_datetime.minute
            )
            
            cursor.execute('UPDATE games SET game_date = %s WHERE id = %s', (new_datetime, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления даты: {e}")
            return False

    def update_game_location(self, game_id, new_location):
        """Обновление адреса игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET location = %s WHERE id = %s', (new_location, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления адреса: {e}")
            return False

    def update_game_max_players(self, game_id, new_max_players):
        """Обновление максимального количества игроков"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET max_players = %s WHERE id = %s', (new_max_players, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления лимита игроков: {e}")
            return False

    def update_game_buy_in(self, game_id, new_buy_in):
        """Обновление стоимости участия"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET buy_in = %s WHERE id = %s', (new_buy_in, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления стоимости: {e}")
            return False

    def update_game_name(self, game_id, new_name):
        """Обновление названия игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET game_name = %s WHERE id = %s', (new_name, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления названия: {e}")
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
            result = cursor.fetchone()
            if not result:
                cursor.close()
                return False, "❌ Игра не найдена"
                
            max_players = result[0]
            
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
            return True, "Вы успешно записаны на игру!"
        except Exception as e:
            logging.error(f"❌ Ошибка записи на игру: {e}")
            return False, "❌ Ошибка при записи на игру"

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

    def get_upcoming_games(self):
        """Получение предстоящих игр"""
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
            return games
        except Exception as e:
            logging.error(f"❌ Ошибка получения игр: {e}")
            return []

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
    
    # ★★★ МЕТОДЫ ДЛЯ РЕЙТИНГА МАФИИ (ГОРОД) ★★★
    def save_mafia_city_rating(self, player_name, file_id):
        """Сохранение рейтинга Городской мафии"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO mafia_city_ratings (player_name, file_id) VALUES (%s, %s)",
                (player_name, file_id)
            )
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения рейтинга Городской мафии: {e}")
            return False

    def get_mafia_city_ratings(self):
        """Получение всех рейтингов Городской мафии"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT player_name, file_id FROM mafia_city_ratings ORDER BY player_name")
            ratings = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return ratings
        except Exception as e:
            logging.error(f"❌ Ошибка получения рейтингов Городской мафии: {e}")
            return {}

    def remove_mafia_city_rating(self, player_name):
        """Удаление рейтинга Городской мафии"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM mafia_city_ratings WHERE player_name = %s", (player_name,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка удаления рейтинга Городской мафии: {e}")
            return False

    # ★★★ МЕТОДЫ ДЛЯ РЕЙТИНГА МАФИИ (КАРТЕЛЬ) ★★★
    def save_mafia_cartel_rating(self, player_name, file_id):
        """Сохранение рейтинга Мафии Картель"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO mafia_cartel_ratings (player_name, file_id) VALUES (%s, %s)",
                (player_name, file_id)
            )
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения рейтинга Мафии Картель: {e}")
            return False

    def get_mafia_cartel_ratings(self):
        """Получение всех рейтингов Мафии Картель"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT player_name, file_id FROM mafia_cartel_ratings ORDER BY player_name")
            ratings = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return ratings
        except Exception as e:
            logging.error(f"❌ Ошибка получения рейтингов Мафии Картель: {e}")
            return {}

    def remove_mafia_cartel_rating(self, player_name):
        """Удаление рейтинга Мафии Картель"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM mafia_cartel_ratings WHERE player_name = %s", (player_name,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка удаления рейтинга Мафии Картель: {e}")
            return False

    # ★★★ МЕТОДЫ ДЛЯ РЕЙТИНГА ПОКЕРА ★★★
    def save_poker_rating(self, player_name, file_id):
        """Сохранение рейтинга покера"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO poker_ratings (player_name, file_id) VALUES (%s, %s)",
                (player_name, file_id)
            )
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения рейтинга покера: {e}")
            return False

    def get_poker_ratings(self):
        """Получение всех рейтингов покера"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT player_name, file_id FROM poker_ratings ORDER BY player_name")
            ratings = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return ratings
        except Exception as e:
            logging.error(f"❌ Ошибка получения рейтингов покера: {e}")
            return {}

    def remove_poker_rating(self, player_name):
        """Удаление рейтинга покера"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM poker_ratings WHERE player_name = %s", (player_name,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка удаления рейтинга покера: {e}")
            return False

    # ★★★ МЕТОДЫ ДЛЯ АФИШ ИГР ★★★
    def update_game_poster(self, game_id, file_id):
        """Обновление афиши игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE games SET poster_file_id = %s WHERE id = %s', (file_id, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления афиши: {e}")
            return False

    def get_game_poster(self, game_id):
        """Получение афиши игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT poster_file_id FROM games WHERE id = %s', (game_id,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"❌ Ошибка получения афиши: {e}")
            return None

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

# Глобальный экземпляр базы данных
db = Database()