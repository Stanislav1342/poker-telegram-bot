import os
import logging
import asyncpg
import asyncio

class Database:
    def __init__(self):
        self.pool = None
        asyncio.run(self.init_db())
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logging.error("❌ DATABASE_URL не найден в переменных окружения")
                return
            
            self.pool = await asyncpg.create_pool(database_url)
            
            # Создаем таблицы
            async with self.pool.acquire() as conn:
                # Таблица игроков
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS players (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        rating REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица карточек игроков
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS player_cards (
                        id SERIAL PRIMARY KEY,
                        player_name VARCHAR(100) UNIQUE NOT NULL,
                        file_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            logging.info("✅ База данных PostgreSQL инициализирована")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
    
    async def add_player(self, name, rating):
        """Добавление игрока"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO players (name, rating) VALUES ($1, $2) ON CONFLICT (name) DO UPDATE SET rating = EXCLUDED.rating",
                    name, rating
                )
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка добавления игрока: {e}")
            return False
    
    async def remove_player(self, name):
        """Удаление игрока"""
        try:
            async with self.pool.acquire() as conn:
                # Удаляем карточку и игрока
                await conn.execute("DELETE FROM player_cards WHERE player_name = $1", name)
                result = await conn.execute("DELETE FROM players WHERE name = $1", name)
                return "DELETE" in result
        except Exception as e:
            logging.error(f"❌ Ошибка удаления игрока: {e}")
            return False
    
    async def get_all_players(self):
        """Получение всех игроков"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT name, rating FROM players ORDER BY rating DESC")
                return {row['name']: row['rating'] for row in rows}
        except Exception as e:
            logging.error(f"❌ Ошибка получения игроков: {e}")
            return {}
    
    async def save_player_card(self, player_name, file_id):
        """Сохранение карточки игрока"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO player_cards (player_name, file_id) VALUES ($1, $2) ON CONFLICT (player_name) DO UPDATE SET file_id = EXCLUDED.file_id",
                    player_name, file_id
                )
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения карточки: {e}")
            return False
    
    async def get_player_card(self, player_name):
        """Получение карточки игрока"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT file_id FROM player_cards WHERE player_name = $1", player_name)
                return row['file_id'] if row else None
        except Exception as e:
            logging.error(f"❌ Ошибка получения карточки: {e}")
            return None
    
    async def get_all_cards(self):
        """Получение всех карточек"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT player_name, file_id FROM player_cards")
                return {row['player_name']: row['file_id'] for row in rows}
        except Exception as e:
            logging.error(f"❌ Ошибка получения карточек: {e}")
            return {}

# Глобальный экземпляр базы данных
db = Database()