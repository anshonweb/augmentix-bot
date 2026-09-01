import aiosqlite
from typing import Optional, List, Dict

class AssignmentRepo:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def create_assignment(self, user_id: int, assigned_at) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute('''
                INSERT INTO news_assignments (user_id, assigned_at) 
                VALUES (?, ?)
            ''', (user_id, assigned_at))
            await conn.commit()
            return cursor.lastrowid

    async def get_pending_assignment(self) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM news_assignments WHERE status = 'pending'") as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def mark_completed(self, assignment_id: int, completed_at) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                UPDATE news_assignments 
                SET status = 'completed', completed_at = ? 
                WHERE id = ?
            ''', (completed_at, assignment_id))
            await conn.commit()
    
    async def get_recent_assignments(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('''
                SELECT * FROM news_assignments 
                ORDER BY assigned_at DESC LIMIT ?
            ''', (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def cancel_pending(self, assignment_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                UPDATE news_assignments 
                SET status = 'cancelled' 
                WHERE id = ?
            ''', (assignment_id,))
            await conn.commit()
