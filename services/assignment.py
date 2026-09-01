from typing import Optional, Dict
from datetime import datetime
from repositories.assignment_repo import AssignmentRepo

class AssignmentService:
    def __init__(self, assignment_repo: AssignmentRepo) -> None:
        self.assignment_repo = assignment_repo

    async def get_active_assignment(self) -> Optional[Dict]:
        return await self.assignment_repo.get_pending_assignment()

    async def complete_assignment(self, assignment_id: int) -> None:
        now = datetime.utcnow()
        await self.assignment_repo.mark_completed(assignment_id, now)

    async def cancel_active_assignment(self) -> None:
        active = await self.get_active_assignment()
        if active:
            await self.assignment_repo.cancel_pending(active['id'])
