import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import os
import logging
from repositories.member_repo import MemberRepo
from repositories.assignment_repo import AssignmentRepo
from services.selector import SelectorService

logger = logging.getLogger('discord')

DAYS_MAP = {
    "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2,
    "THURSDAY": 3, "FRIDAY": 4, "SATURDAY": 5, "SUNDAY": 6
}

class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai_news_channel_id = int(os.getenv('AI_NEWS_CHANNEL_ID', 0))
        self.member_repo = MemberRepo(self.bot.db.pool)
        self.assignment_repo = AssignmentRepo(self.bot.db.pool)
        self.selector_service = SelectorService(self.member_repo, self.assignment_repo)
        
        day_str = os.getenv("SCHEDULE_DAY", "MONDAY").upper()
        self.target_day = DAYS_MAP.get(day_str, 0)
        
        schedule_hour = int(os.getenv("SCHEDULE_HOUR", 18))
        t = time(hour=schedule_hour, minute=0)
        
        self.weekly_selection.change_interval(time=t)
        self.weekly_selection.start()

    def cog_unload(self) -> None:
        self.weekly_selection.cancel()

    @tasks.loop(time=time(hour=18, minute=0))
    async def weekly_selection(self) -> None:
        if datetime.utcnow().weekday() != self.target_day:
            return

        channel = self.bot.get_channel(self.ai_news_channel_id)
        if not channel:
            logger.error("News channel not found.")
            return

        guild = channel.guild
        selected = await self.selector_service.pick_random_member(guild)
        
        if selected:
            await channel.send(
                f"Weekly AI News Bot\n"
                f"Hey {selected.mention}, you're this week's AI reporter!\n"
                f"Please post 3-5 important AI or technology developments from this week that are suitable for our Instagram page.\n"
                f"Once you post your news in this channel, I'll mark it as received."
            )
        else:
            logger.warning("No eligible members found for weekly selection.")

    @weekly_selection.before_loop
    async def before_weekly_selection(self) -> None:
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SchedulerCog(bot))
