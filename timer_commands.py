import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

from utils.embed_builder import create_timer_embed, create_error_embed
from utils.error_handler import handle_command_error

# Dictionary to store active timers
active_timers = {}

class MemberNameModal(discord.ui.Modal, title="Member Name"):
    """Modal for collecting the name of the member who is sharing."""
    
    # Text input for member name
    member_name = discord.ui.TextInput(
        label="Member Name",
        placeholder="Enter the name of the member who is sharing",
        required=True,
        max_length=100
    )
    
    def __init__(self, timer_view):
        super().__init__()
        self.timer_view = timer_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        # Start the timer with the provided member name
        await self.timer_view.start_timer(interaction, self.member_name.value)

class TimerView(discord.ui.View):
    """View for timer controls."""
    
    def __init__(self, channel_id, member_name, duration=180):
        super().__init__(timeout=None)  # No timeout for the view
        self.channel_id = channel_id
        self.member_name = member_name
        self.duration = duration  # Default: 3 minutes (180 seconds)
        self.remaining = duration
        self.paused = False
        self.message = None
        self.update_task = None
    
    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle pause/resume state of the timer."""
        self.paused = not self.paused
        await interaction.response.defer()  # Acknowledge the interaction without sending a message
    
    @discord.ui.button(label="Reset", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset the timer to its initial duration."""
        self.remaining = self.duration
        self.paused = False
        await interaction.response.defer()  # Acknowledge the interaction
    
    async def start_timer(self, interaction: discord.Interaction, member_name):
        """Start the timer with the provided member name."""
        self.member_name = member_name
        
        # Create and send the initial embed
        embed = create_timer_embed(self.member_name, self.remaining)
        await interaction.response.send_message(embed=embed, view=self)
        self.message = await interaction.original_response()
        
        # Start the update task
        self.update_task = asyncio.create_task(self.update_timer())
    
    async def update_timer(self):
        """Update the timer display periodically."""
        try:
            while self.remaining > 0:
                if not self.paused:
                    # Update every second for all time intervals
                    update_interval = 1
                    
                    # Wait for the update interval
                    await asyncio.sleep(update_interval)
                    
                    # Decrement the timer
                    self.remaining -= update_interval
                    
                    # Ensure we don't go below 0
                    if self.remaining < 0:
                        self.remaining = 0
                    
                    # Update the embed
                    embed = create_timer_embed(self.member_name, self.remaining)
                    
                    # Add warnings based on remaining time
                    if self.remaining == 60:  # 1 minute warning
                        embed.add_field(name="Warning", value="⚠️ 1 minute remaining!", inline=False)
                    elif self.remaining == 30:  # 30 seconds warning
                        embed.add_field(name="Warning", value="⚠️ 30 seconds remaining!", inline=False)
                    elif self.remaining == 10:  # 10 seconds warning
                        embed.add_field(name="Warning", value="⚠️ 10 seconds remaining!", inline=False)
                    
                    # Update the message
                    await self.message.edit(embed=embed)
                else:
                    # If paused, just wait a bit before checking again
                    await asyncio.sleep(1)
            
            # Timer completed
            final_embed = create_timer_embed(self.member_name, 0)
            final_embed.add_field(name="Completed", value="⏰ Time's up! 🔔", inline=False)
            await self.message.edit(embed=final_embed, view=None)  # Remove buttons
            
            # Cleanup
            if self.channel_id in active_timers:
                del active_timers[self.channel_id]
        
        except Exception as e:
            # Handle any errors during timer updates
            error_embed = create_error_embed(f"Timer error: {str(e)}")
            await self.message.edit(embed=error_embed, view=None)
            
            # Cleanup
            if self.channel_id in active_timers:
                del active_timers[self.channel_id]

class TimerCog(commands.Cog):
    """Cog for timer-related commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="timer", description="Start a 3-minute countdown timer for member sharing")
    async def timer(self, interaction: discord.Interaction):
        """Start a 3-minute countdown timer for member sharing."""
        try:
            channel_id = interaction.channel_id
            
            # Check if there's already an active timer in this channel
            if channel_id in active_timers:
                await interaction.response.send_message(
                    embed=create_error_embed("There's already an active timer in this channel."),
                    ephemeral=True
                )
                return
            
            # Create a new timer view
            timer_view = TimerView(channel_id, "Member")
            
            # Create and show the modal to get the member name
            modal = MemberNameModal(timer_view)
            await interaction.response.send_modal(modal)
            
            # Store the timer in the active timers dictionary
            active_timers[channel_id] = timer_view
        
        except Exception as e:
            await handle_command_error(interaction, e)

async def setup(bot):
    """Add the timer cog to the bot."""
    await bot.add_cog(TimerCog(bot))
