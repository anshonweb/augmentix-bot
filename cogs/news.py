import discord
from discord.ext import commands
import os
import logging
from repositories.assignment_repo import AssignmentRepo
from services.assignment import AssignmentService

logger = logging.getLogger('discord')

class NewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai_news_channel_id = int(os.getenv('AI_NEWS_CHANNEL_ID', 0))
        self.assignment_repo = AssignmentRepo(self.bot.db.pool)
        self.assignment_service = AssignmentService(self.assignment_repo)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if message.channel.id != self.ai_news_channel_id:
            return

        try:
            active = await self.assignment_service.get_active_assignment()
            if not active:
                return

            if message.author.id == active['user_id']:
                await self.assignment_service.complete_assignment(active['id'])
                await message.reply(
                    f"AI news received! Thanks {message.author.mention}. Your submission has been recorded."
                )
        except Exception as e:
            logger.error(f"Error in AI news listener: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NewsCog(bot))
