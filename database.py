import os
import logging
import json
import sqlite3

class Database:
    def __init__(self):
        self.conn = None
        self.db_type = "sqlite"  # Используем SQLite как временное решение
        self.init_db()
    
    def init_db(self):
        """Инициализация SQLite базы данных"""
        try:
            # Создаем SQLite базу в /tmp (сохраняется между перезапусками на Railway)
            self.conn = sqlite3.connect('/tmp/poker_bot.db', check_same_thread=False)
            cursor = self.conn.cursor()
            
            # Таблица игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    rating REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица карточек игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT UNIQUE NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            cursor.close()
            logging.info("✅ SQLite база данных инициализирована в /tmp/poker_bot.db")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
    
    def add_player(self, name, rating):
        """Добавление игрока"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO players (name, rating) VALUES (?, ?)",
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
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM player_cards WHERE player_name = ?", (name,))
            cursor.execute("DELETE FROM players WHERE name = ?", (name,))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игрока: {e}")
            return False
    
    def get_all_players(self):
        """Получение всех игроков"""
        try:
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
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO player_cards (player_name, file_id) VALUES (?, ?)",
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
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT file_id FROM player_cards WHERE player_name = ?", 
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