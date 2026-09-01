import discord
from discord import app_commands
from discord.ext import commands
import os
from repositories.member_repo import MemberRepo
from repositories.assignment_repo import AssignmentRepo
from services.selector import SelectorService
from services.assignment import AssignmentService

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai_news_channel_id = int(os.getenv('AI_NEWS_CHANNEL_ID', 0))
        self.member_repo = MemberRepo(self.bot.db.pool)
        self.assignment_repo = AssignmentRepo(self.bot.db.pool)
        self.selector_service = SelectorService(self.member_repo, self.assignment_repo)
        self.assignment_service = AssignmentService(self.assignment_repo)

    @app_commands.command(name="pick", description="Pick this week's user immediately")
    @app_commands.default_permissions(administrator=True)
    async def pick_cmd(self, interaction: discord.Interaction) -> None:
        channel = self.bot.get_channel(self.ai_news_channel_id)
        if not channel:
             await interaction.response.send_message("News channel not configured correctly.", ephemeral=True)
             return
             
        selected = await self.selector_service.pick_random_member(interaction.guild)
        if selected:
             if not interaction.response.is_done():
                 await interaction.response.send_message(f"Selected {selected.name}.", ephemeral=True)
             
             await channel.send(
                f"Weekly AI News Duty\n"
                f"Hey {selected.mention}, you're this week's AI reporter!\n"
                f"Please post 3-5 important AI or technology developments from this week that are suitable for our Instagram page.\n"
                f"Once you post your news in this channel, I'll mark it as received."
             )
        else:
             if not interaction.response.is_done():
                 await interaction.response.send_message("No eligible members found.", ephemeral=True)

    @app_commands.command(name="status", description="Show current assigned user and submission status")
    @app_commands.default_permissions(administrator=True)
    async def status_cmd(self, interaction: discord.Interaction) -> None:
        active = await self.assignment_service.get_active_assignment()
        if not active:
             await interaction.response.send_message("No pending assignment.", ephemeral=True)
             return
             
        user = interaction.guild.get_member(active['user_id'])
        username = user.name if user else f"User ID: {active['user_id']}"
        await interaction.response.send_message(
             f"Current assigned user: {username}\nAssigned at: {active['assigned_at']}\nStatus: {active['status']}",
             ephemeral=True
        )

    @app_commands.command(name="history", description="Show last 10 assignments")
    @app_commands.default_permissions(administrator=True)
    async def history_cmd(self, interaction: discord.Interaction) -> None:
        recent = await self.assignment_repo.get_recent_assignments(10)
        if not recent:
             await interaction.response.send_message("No history found.", ephemeral=True)
             return
             
        lines = []
        for r in recent:
             lines.append(f"User: {r['user_id']} | Assigned: {r['assigned_at']} | Status: {r['status']}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="reset_cycle", description="Reset rotation manually")
    @app_commands.default_permissions(administrator=True)
    async def reset_cycle_cmd(self, interaction: discord.Interaction) -> None:
        await self.selector_service.reset_cycle()
        await interaction.response.send_message("Cycle has been reset.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip current user and choose another")
    @app_commands.default_permissions(administrator=True)
    async def skip_cmd(self, interaction: discord.Interaction) -> None:
        await self.assignment_service.cancel_active_assignment()
        await self.pick_cmd(interaction)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
