import discord
from discord import app_commands
from utils.state import active_fractal_groups
from discord.ext import commands
from typing import Dict, Optional
from datetime import datetime, timedelta

from cogs.base import BaseCog
from config.config import COLORS

# Store respect counts per user
respect_counts: Dict[int, int] = {}
last_respect: Dict[int, Dict[int, datetime]] = {}  # {user_id: {target_id: last_time}}

class RespectCog(BaseCog):
    """Cog for managing respect points between users."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @app_commands.command(
        name="respect",
        description="Give respect to another user"
    )
    @app_commands.describe(
        user="The user to give respect to",
        reason="Optional reason for giving respect"
    )
    async def give_respect(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = None
    ):
        """Give respect to another user."""
        try:
            # Can't give respect to yourself
            if user.id == interaction.user.id:
                await interaction.response.send_message(
                    "You can't give respect to yourself!",
                    ephemeral=True
                )
                return
            
            # Check cooldown
            now = datetime.now()
            if interaction.user.id in last_respect:
                last_time = last_respect[interaction.user.id].get(user.id)
                if last_time and now - last_time < timedelta(hours=24):
                    time_left = timedelta(hours=24) - (now - last_time)
                    hours = int(time_left.total_seconds() / 3600)
                    minutes = int((time_left.total_seconds() % 3600) / 60)
                    
                    await interaction.response.send_message(
                        f"You can give respect to {user.mention} again in "
                        f"{hours} hours and {minutes} minutes.",
                        ephemeral=True
                    )
                    return
            
            # Update respect count
            if user.id not in respect_counts:
                respect_counts[user.id] = 0
            respect_counts[user.id] += 1
            
            # Update cooldown
            if interaction.user.id not in last_respect:
                last_respect[interaction.user.id] = {}
            last_respect[interaction.user.id][user.id] = now
            
            # Create embed
            embed = discord.Embed(
                title="🎖️ Respect Given!",
                color=COLORS['success']
            )
            
            embed.add_field(
                name="From",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="To",
                value=user.mention,
                inline=True
            )
            embed.add_field(
                name="Total Respect",
                value=str(respect_counts[user.id]),
                inline=True
            )
            
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            self.logger.info(
                f"{interaction.user} gave respect to {user}"
                + (f" for: {reason}" if reason else "")
            )
            
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(
        name="respectrank",
        description="Show respect rankings"
    )
    async def show_ranks(self, interaction: discord.Interaction):
        """Show the respect rankings for the server."""
        try:
            if not respect_counts:
                await interaction.response.send_message(
                    "No respect has been given yet!",
                    ephemeral=True
                )
                return
            
            # Sort users by respect count
            sorted_users = sorted(
                respect_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            embed = discord.Embed(
                title="🏆 Respect Rankings",
                color=COLORS['info']
            )
            
            # Add top 10 users
            description = []
            for i, (user_id, count) in enumerate(sorted_users[:10], 1):
                user = interaction.guild.get_member(user_id)
                if user:
                    description.append(
                        f"{self._get_medal(i)} {user.mention}: {count} respect"
                    )
            
            embed.description = "\n".join(description)
            
            # Add requester's rank if not in top 10
            user_id = interaction.user.id
            if user_id in respect_counts:
                user_rank = next(
                    (i for i, (uid, _) in enumerate(sorted_users, 1)
                     if uid == user_id),
                    None
                )
                if user_rank and user_rank > 10:
                    embed.add_field(
                        name="Your Rank",
                        value=f"#{user_rank}: {respect_counts[user_id]} respect",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await self.handle_error(interaction, e)

    def _get_medal(self, position: int) -> str:
        """Get medal emoji for position."""
        medals = {
            1: "🥇",
            2: "🥈",
            3: "🥉"
        }
        return medals.get(position, f"#{position}")

async def setup(bot: commands.Bot):
    """Add the respect cog to the bot."""
    await bot.add_cog(RespectCog(bot))
