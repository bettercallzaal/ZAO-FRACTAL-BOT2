import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

from cogs.base import BaseCog
from config.config import (
    TIMER_MAX_DURATION,
    TIMER_CHECK_INTERVAL,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    COLORS
)

# Store active timers: {timer_id: (user_id, end_time, task)}
active_timers: Dict[int, tuple[int, datetime, asyncio.Task]] = {}

class TimerCog(BaseCog):
    """Cog for managing timers and reminders."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self._next_timer_id = 1
        self.check_timers.start()

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.check_timers.cancel()
        # Cancel all active timers
        for timer_id, (_, _, task) in active_timers.items():
            if not task.done():
                task.cancel()
        active_timers.clear()

    @tasks.loop(seconds=TIMER_CHECK_INTERVAL)
    async def check_timers(self):
        """Check for completed timers."""
        now = datetime.now()
        completed = []
        
        for timer_id, (user_id, end_time, task) in active_timers.items():
            if now >= end_time and not task.done():
                task.cancel()
                completed.append(timer_id)
                
                try:
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        await user.send(
                            embed=discord.Embed(
                                title="⏰ Timer Complete!",
                                description="Your timer has finished!",
                                color=COLORS['success']
                            )
                        )
                except Exception as e:
                    self.logger.error(f"Failed to notify user {user_id} about timer completion", exc_info=e)
        
        # Clean up completed timers
        for timer_id in completed:
            del active_timers[timer_id]

    @app_commands.command(
        name="timer",
        description="Set a timer for a specified duration"
    )
    @app_commands.describe(
        duration="Duration in seconds (max 1 hour)",
        message="Optional message to show when timer completes"
    )
    async def timer(
        self,
        interaction: discord.Interaction,
        duration: int,
        message: Optional[str] = None
    ):
        """Set a timer that will notify you when it's done."""
        try:
            # Validate duration
            if not 1 <= duration <= TIMER_MAX_DURATION:
                await interaction.response.send_message(
                    ERROR_MESSAGES['invalid_duration'],
                    ephemeral=True
                )
                return
            
            # Create timer
            timer_id = self._next_timer_id
            self._next_timer_id += 1
            
            end_time = datetime.now() + timedelta(seconds=duration)
            
            # Create task
            task = asyncio.create_task(self._timer_task(
                timer_id,
                interaction.user.id,
                duration,
                message
            ))
            
            # Store timer
            active_timers[timer_id] = (interaction.user.id, end_time, task)
            
            # Format duration for display
            duration_str = self._format_duration(duration)
            
            # Send confirmation
            embed = discord.Embed(
                title="⏰ Timer Started",
                description=f"I'll remind you in {duration_str}",
                color=COLORS['info']
            )
            if message:
                embed.add_field(name="Message", value=message)
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
            self.logger.info(
                f"Timer started by {interaction.user} for {duration} seconds"
                + (f" with message: {message}" if message else "")
            )
            
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(
        name="timers",
        description="List your active timers"
    )
    async def list_timers(self, interaction: discord.Interaction):
        """List all active timers for the user."""
        try:
            user_timers = {
                tid: (end_time, task)
                for tid, (uid, end_time, task) in active_timers.items()
                if uid == interaction.user.id and not task.done()
            }
            
            if not user_timers:
                await interaction.response.send_message(
                    "You have no active timers.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="Your Active Timers",
                color=COLORS['info']
            )
            
            now = datetime.now()
            for timer_id, (end_time, _) in user_timers.items():
                remaining = end_time - now
                if remaining.total_seconds() > 0:
                    embed.add_field(
                        name=f"Timer #{timer_id}",
                        value=f"Time remaining: {self._format_duration(int(remaining.total_seconds()))}",
                        inline=False
                    )
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(
        name="canceltimer",
        description="Cancel one of your active timers"
    )
    @app_commands.describe(timer_id="ID of the timer to cancel")
    async def cancel_timer(self, interaction: discord.Interaction, timer_id: int):
        """Cancel a specific timer."""
        try:
            if timer_id not in active_timers:
                await interaction.response.send_message(
                    "Timer not found.",
                    ephemeral=True
                )
                return
            
            user_id, _, task = active_timers[timer_id]
            if user_id != interaction.user.id:
                await interaction.response.send_message(
                    "You can only cancel your own timers.",
                    ephemeral=True
                )
                return
            
            # Cancel and remove timer
            if not task.done():
                task.cancel()
            del active_timers[timer_id]
            
            await interaction.response.send_message(
                f"Timer #{timer_id} has been cancelled.",
                ephemeral=True
            )
            
            self.logger.info(f"Timer #{timer_id} cancelled by {interaction.user}")
            
        except Exception as e:
            await self.handle_error(interaction, e)

    async def _timer_task(
        self,
        timer_id: int,
        user_id: int,
        duration: int,
        message: Optional[str]
    ):
        """Background task for a timer."""
        try:
            await asyncio.sleep(duration)
            
            # Timer completed naturally
            if timer_id in active_timers:
                user = await self.bot.fetch_user(user_id)
                if user:
                    embed = discord.Embed(
                        title="⏰ Timer Complete!",
                        description="Your timer has finished!",
                        color=COLORS['success']
                    )
                    if message:
                        embed.add_field(name="Message", value=message)
                    
                    await user.send(embed=embed)
                    del active_timers[timer_id]
                    
        except asyncio.CancelledError:
            # Timer was cancelled
            pass
        except Exception as e:
            self.logger.error(f"Error in timer task #{timer_id}", exc_info=e)

    def _format_duration(self, seconds: int) -> str:
        """Format a duration in seconds to a human-readable string."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        return " ".join(parts)

async def setup(bot: commands.Bot):
    """Add the timer cog to the bot."""
    await bot.add_cog(TimerCog(bot))
