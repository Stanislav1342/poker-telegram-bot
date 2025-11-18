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
                    host VARCHAR(100) DEFAULT 'Капоне',
                    end_time VARCHAR(10) DEFAULT '22:00',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Остальные существующие таблицы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    rating REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_cards (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(100) UNIQUE NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
    
    # ★★★ ОБНОВЛЕННЫЙ МЕТОД СОЗДАНИЯ ИГРЫ ★★★
    def create_game(self, game_name, game_date, max_players, game_type, buy_in, location, host=None, end_time=None, created_by=None):
        """Создание новой игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO games (game_name, game_date, max_players, game_type, buy_in, location, host, end_time, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (game_name, game_date, max_players, game_type, buy_in, location, host, end_time, created_by))
            game_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            return game_id
        except Exception as e:
            logging.error(f"❌ Ошибка создания игры: {e}")
            return None

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

    # Остальные методы остаются без изменений...
    # ... (все остальные методы из предыдущей версии)

# Глобальный экземпляр базы данных
db = Database()