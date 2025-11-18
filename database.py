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
            
            # Таблица игр
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
            
            # Таблица записей на игру
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
            
            # Проверяем существование колонки game_name и добавляем если нет
            try:
                cursor.execute("SELECT game_name FROM games LIMIT 1")
            except Exception:
                # Колонки нет, добавляем
                cursor.execute('''
                    ALTER TABLE games 
                    ADD COLUMN IF NOT EXISTS game_name VARCHAR(200) NOT NULL DEFAULT 'Покерная игра'
                ''')
                logging.info("✅ Добавлена колонка game_name в таблицу games")
            
            self.conn.commit()
            cursor.close()
            logging.info("✅ Таблицы в PostgreSQL инициализированы")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
            # Пытаемся восстановить соединение
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            # Пробуем переподключиться
            self.connect()
    
    def add_player(self, name, rating):
        """Добавление игрока"""
        try:
            if not self.conn:
                self.connect()
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False
    
    def update_player_rating(self, name, new_rating):
        """Обновление рейтинга игрока"""
        try:
            if not self.conn:
                self.connect()
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False
    
    def remove_player(self, name):
        """Удаление игрока"""
        try:
            if not self.conn:
                self.connect()
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False
    
    def get_all_players(self):
        """Получение всех игроков"""
        try:
            if not self.conn:
                self.connect()
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
                self.connect()
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False
    
    def get_player_card(self, player_name):
        """Получение карточки игрока"""
        try:
            if not self.conn:
                self.connect()
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
                self.connect()
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

    # НОВЫЕ МЕТОДЫ ДЛЯ ИГР
    def create_game(self, game_name, game_date, max_players, game_type, buy_in, location, created_by):
        """Создание новой игры"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return None
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO games (game_name, game_date, max_players, game_type, buy_in, location, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (game_name, game_date, max_players, game_type, buy_in, location, created_by))
            game_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            return game_id
        except Exception as e:
            logging.error(f"❌ Ошибка создания игры: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return None

    def register_player_for_game(self, game_id, player_name, user_id):
        """Запись игрока на игру"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False, "❌ Ошибка подключения к базе данных"
            
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False, "❌ Ошибка при записи на игру"

    def get_upcoming_games(self):
        """Получение предстоящих игр"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, game_name, game_date, game_type, max_players, buy_in, location, status
                FROM games 
                WHERE game_date > NOW() AND status = 'upcoming'
                ORDER BY game_date
            ''')
            games = cursor.fetchall()
            cursor.close()
            return games
        except Exception as e:
            logging.error(f"❌ Ошибка получения игр: {e}")
            return []

    def get_all_games(self):
        """Получение всех игр (включая активные)"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, game_name, game_date, game_type, max_players, buy_in, location, status
                FROM games 
                WHERE status = 'upcoming'
                ORDER BY game_date
            ''')
            games = cursor.fetchall()
            cursor.close()
            return games
        except Exception as e:
            logging.error(f"❌ Ошибка получения всех игр: {e}")
            return []

    def get_game_registrations(self, game_id):
        """Получение списка записавшихся на игру"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
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

    def get_game_by_id(self, game_id):
        """Получение информации об игре по ID"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return None
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, game_name, game_date, game_type, max_players, buy_in, location, status
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
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False
            
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
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False

    def update_game_max_players(self, game_id, new_max_players):
        """Обновление максимального количества игроков"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False
            
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE games SET max_players = %s WHERE id = %s
            ''', (new_max_players, game_id))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка обновления лимита игроков: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False

    def cancel_game(self, game_id):
        """Отмена игры"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False
            
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE games SET status = 'cancelled' WHERE id = %s
            ''', (game_id,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка отмены игры: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False

    def delete_game(self, game_id):
        """Удаление игры без уведомлений"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False
            
            cursor = self.conn.cursor()
            # Сначала удаляем записи на игру (из-за CASCADE это делается автоматически, но для надежности)
            cursor.execute('DELETE FROM game_registrations WHERE game_id = %s', (game_id,))
            # Затем удаляем саму игру
            cursor.execute('DELETE FROM games WHERE id = %s', (game_id,))
            self.conn.commit()
            cursor.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игры: {e}")
            try:
                if self.conn:
                    self.conn.rollback()
            except:
                self.conn = None
            return False

    def get_all_game_registrations(self):
        """Получение всех записей на игры (для рассылки)"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT DISTINCT user_id 
                FROM game_registrations 
                WHERE user_id IS NOT NULL AND status = 'registered'
            ''')
            user_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return user_ids
        except Exception as e:
            logging.error(f"❌ Ошибка получения user_id для рассылки: {e}")
            return []

    def get_game_registrations_by_game(self, game_id):
        """Получение user_id записавшихся на конкретную игру"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_id FROM game_registrations 
                WHERE game_id = %s AND user_id IS NOT NULL AND status = 'registered'
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
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
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

    def delete_all_games(self):
        """Удаление всех игр"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return False
            
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM game_registrations')
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
                self.conn = None
            return False

    def get_all_registrations_info(self):
        """Получение информации о всех записях на все игры"""
        try:
            if not self.conn:
                self.connect()
                if not self.conn:
                    return []
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT g.id, g.game_name, g.game_date, g.location, 
                       COUNT(gr.id) as registered_count, g.max_players,
                       STRING_AGG(gr.player_name, ', ') as players_list
                FROM games g
                LEFT JOIN game_registrations gr ON g.id = gr.game_id AND gr.status = 'registered'
                WHERE g.status = 'upcoming'
                GROUP BY g.id, g.game_name, g.game_date, g.location, g.max_players
                ORDER BY g.game_date
            ''')
            games_info = cursor.fetchall()
            cursor.close()
            return games_info
        except Exception as e:
            logging.error(f"❌ Ошибка получения информации о записях: {e}")
            return []

# Глобальный экземпляр базы данных
db = Database()
