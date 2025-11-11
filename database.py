import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_db()
    
    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logging.error("❌ DATABASE_URL не найден в переменных окружения")
                return
            
            self.conn = psycopg2.connect(database_url)
            logging.info("✅ Подключение к PostgreSQL установлено")
        except Exception as e:
            logging.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
    
    def init_db(self):
        """Инициализация таблиц"""
        try:
            if not self.conn:
                self.connect()
            
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
            
            self.conn.commit()
            cursor.close()
            logging.info("✅ Таблицы в PostgreSQL инициализированы")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
    
    def add_player(self, name, rating):
        """Добавление игрока"""
        try:
            if not self.conn:
                self.connect()
            
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
    
    def remove_player(self, name):
        """Удаление игрока"""
        try:
            if not self.conn:
                self.connect()
            
            cursor = self.conn.cursor()
            # Удаляем карточку и игрока
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
                self.connect()
            
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
                self.connect()
            
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
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT player_name, file_id FROM player_cards")
            cards = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return cards
        except Exception as e:
            logging.error(f"❌ Ошибка получения карточек: {e}")
            return {}

# Глобальный экземпляр базы данных
db = Database()