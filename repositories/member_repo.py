import aiosqlite
from typing import Optional, List, Dict

class MemberRepo:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def get_all_members(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM news_members") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_member(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM news_members WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def upsert_member(self, user_id: int, username: str) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO news_members (user_id, username) 
                VALUES (?, ?)
                ON CONFLICT (user_id) 
                DO UPDATE SET username = excluded.username
            ''', (user_id, username))
            await conn.commit()

    async def update_member_selection(self, user_id: int, timestamp, cycle_number: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                UPDATE news_members 
                SET last_selected_at = ?, cycle_number = ? 
                WHERE user_id = ?
            ''', (timestamp, cycle_number, user_id))
            await conn.commit()

    async def get_highest_cycle(self) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT MAX(cycle_number) FROM news_members") as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else 1

    async def get_blacklisted_users(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT user_id FROM news_blacklist") as cursor:
                rows = await cursor.fetchall()
                return [r['user_id'] for r in rows]

    async def add_to_blacklist(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO news_blacklist (user_id) 
                VALUES (?) 
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id,))
            await conn.commit()

    async def remove_from_blacklist(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM news_blacklist WHERE user_id = ?", (user_id,))
            await conn.commit()
