import aiosqlite
import os
from datetime import datetime
import logging

logger = logging.getLogger('discord')

class Database:
    def __init__(self) -> None:
        self.db_path = "data/bot.db"
        self.pool = self.db_path

    async def init_db(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        discord_id INTEGER PRIMARY KEY,
                        leetcode_username TEXT NOT NULL,
                        total_solved INTEGER DEFAULT 0,
                        weekly_solved INTEGER DEFAULT 0,
                        last_updated TIMESTAMP,
                        linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS submissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id INTEGER REFERENCES users(discord_id) ON DELETE CASCADE,
                        problem_title TEXT,
                        problem_slug TEXT,
                        difficulty TEXT,
                        timestamp INTEGER,
                        week_number INTEGER
                    )
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_submissions_discord_id 
                    ON submissions(discord_id)
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_submissions_week 
                    ON submissions(week_number)
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS news_members (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL,
                        last_selected_at TIMESTAMP,
                        cycle_number INTEGER NOT NULL DEFAULT 1
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS news_blacklist (
                        user_id INTEGER PRIMARY KEY
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS news_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        assigned_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        status TEXT NOT NULL DEFAULT 'pending',
                        FOREIGN KEY(user_id) REFERENCES news_members(user_id)
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS daily_challenges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question_id INTEGER NOT NULL,
                        posted_date DATE DEFAULT CURRENT_DATE,
                        question_message_id INTEGER,
                        solution_message_id INTEGER,
                        solution_posted BOOLEAN DEFAULT 0
                    )
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_daily_challenges_date 
                    ON daily_challenges(posted_date)
                ''')
                
                await conn.commit()
                logger.info('Database tables created/verified')
        
        except Exception as e:
            logger.error(f'Database initialization error: {e}')
            raise
    
    async def close(self) -> None:
        pass

    async def link_user(self, discord_id: int, leetcode_username: str) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO users (discord_id, leetcode_username, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT (discord_id) 
                DO UPDATE SET leetcode_username = excluded.leetcode_username, last_updated = excluded.last_updated
            ''', (discord_id, leetcode_username, datetime.now().isoformat()))
            await conn.commit()
    
    async def get_user(self, discord_id: int):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT * FROM users WHERE discord_id = ?', (discord_id,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT discord_id, leetcode_username FROM users') as cursor:
                rows = await cursor.fetchall()
                return [(row['discord_id'], row['leetcode_username']) for row in rows]
    
    async def update_user_stats(self, discord_id: int, total_solved: int, weekly_solved: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                UPDATE users 
                SET total_solved = ?, weekly_solved = ?, last_updated = ?
                WHERE discord_id = ?
            ''', (total_solved, weekly_solved, datetime.now().isoformat(), discord_id))
            await conn.commit()
    
    async def unlink_user(self, discord_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('DELETE FROM users WHERE discord_id = ?', (discord_id,))
            await conn.commit()
    
    async def add_submission(self, discord_id: int, problem_title: str, 
                           problem_slug: str, difficulty: str, timestamp: int) -> bool:
        week_number = datetime.fromtimestamp(timestamp).isocalendar()[1]
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT id FROM submissions 
                WHERE discord_id = ? AND problem_slug = ? AND timestamp = ?
            ''', (discord_id, problem_slug, timestamp)) as cursor:
                existing = await cursor.fetchone()
            
            if not existing:
                await conn.execute('''
                    INSERT INTO submissions 
                    (discord_id, problem_title, problem_slug, difficulty, timestamp, week_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (discord_id, problem_title, problem_slug, difficulty, timestamp, week_number))
                await conn.commit()
                return True
            
            return False
    
    async def get_user_submissions_this_week(self, discord_id: int):
        current_week = datetime.now().isocalendar()[1]
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT problem_title, difficulty, timestamp
                FROM submissions
                WHERE discord_id = ? AND week_number = ?
                ORDER BY timestamp DESC
            ''', (discord_id, current_week)) as cursor:
                rows = await cursor.fetchall()
                return [(row['problem_title'], row['difficulty'], row['timestamp']) for row in rows]
    
    async def get_weekly_leaderboard(self, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT discord_id, leetcode_username, weekly_solved
                FROM users
                WHERE weekly_solved > 0
                ORDER BY weekly_solved DESC
                LIMIT ?
            ''', (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [(row['discord_id'], row['leetcode_username'], row['weekly_solved']) for row in rows]
    
    async def reset_weekly_stats(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('UPDATE users SET weekly_solved = 0')
            await conn.commit()
    
    async def get_todays_challenge(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT * FROM daily_challenges
                WHERE posted_date = CURRENT_DATE
            ''') as cursor:
                return await cursor.fetchone()
    
    async def post_daily_challenge(self, question_id: int, question_message_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO daily_challenges (question_id, posted_date, question_message_id)
                VALUES (?, CURRENT_DATE, ?)
            ''', (question_id, question_message_id))
            await conn.commit()
    
    async def post_challenge_solution(self, challenge_id: int, solution_message_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                UPDATE daily_challenges
                SET solution_posted = 1, solution_message_id = ?
                WHERE id = ?
            ''', (solution_message_id, challenge_id))
            await conn.commit()
    
    async def get_posted_question_ids(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT DISTINCT question_id FROM daily_challenges
            ''') as cursor:
                rows = await cursor.fetchall()
                return [row['question_id'] for row in rows]
    
    async def get_challenge_stats(self):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute('SELECT COUNT(*) FROM daily_challenges') as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0
                
            async with conn.execute('SELECT COUNT(*) FROM daily_challenges WHERE solution_posted = 1') as cursor:
                row = await cursor.fetchone()
                with_solution = row[0] if row else 0
                
            return {
                'total_posted': total,
                'solutions_posted': with_solution
            }