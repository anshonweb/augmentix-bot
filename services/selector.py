import random
from typing import Optional, List
import discord
from datetime import datetime
import os

from repositories.member_repo import MemberRepo
from repositories.assignment_repo import AssignmentRepo

class SelectorService:
    def __init__(self, member_repo: MemberRepo, assignment_repo: AssignmentRepo) -> None:
        self.member_repo = member_repo
        self.assignment_repo = assignment_repo
        self.admin_role_name = os.getenv("ADMIN_ROLE_NAME", "Admin")

    async def get_eligible_members(self, guild: discord.Guild) -> List[discord.Member]:
        eligible = []
        blacklisted_ids = await self.member_repo.get_blacklisted_users()
        
        for member in guild.members:
            if member.bot:
                continue
            
            is_admin = any(role.name == self.admin_role_name for role in member.roles)
            if is_admin:
                continue
                
            if member.id in blacklisted_ids:
                continue
                
            eligible.append(member)
            await self.member_repo.upsert_member(member.id, member.name)
            
        return eligible

    async def pick_random_member(self, guild: discord.Guild) -> Optional[discord.Member]:
        eligible_members = await self.get_eligible_members(guild)
        if not eligible_members:
            return None

        current_cycle = await self.member_repo.get_highest_cycle()
        db_members = await self.member_repo.get_all_members()
        
        member_cycle_map = {row['user_id']: row['cycle_number'] for row in db_members}
        
        pool = []
        for member in eligible_members:
            mem_cycle = member_cycle_map.get(member.id, 0)
            if mem_cycle < current_cycle:
                pool.append(member)

        if not pool:
            current_cycle += 1
            pool = eligible_members

        selected = random.choice(pool)
        
        now = datetime.utcnow()
        await self.member_repo.update_member_selection(selected.id, now, current_cycle)
        
        pending = await self.assignment_repo.get_pending_assignment()
        if pending:
             await self.assignment_repo.cancel_pending(pending['id'])
             
        await self.assignment_repo.create_assignment(selected.id, now)
        
        return selected

    async def reset_cycle(self) -> None:
        current_cycle = await self.member_repo.get_highest_cycle()
        db_members = await self.member_repo.get_all_members()
        for row in db_members:
            await self.member_repo.update_member_selection(row['user_id'], row['last_selected_at'], current_cycle + 1)
