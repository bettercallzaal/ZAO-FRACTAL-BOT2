from discord.ext import commands
import discord
import logging

class BaseCog(commands.Cog):
    """Base cog class with common utilities."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_error(self, interaction: discord.Interaction, error: Exception):
        """Handle errors in commands."""
        error_msg = f"An error occurred: {str(error)}"
        self.logger.error(error_msg, exc_info=error)
        
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
    
    async def check_voice_state(self, interaction: discord.Interaction) -> tuple[bool, discord.VoiceChannel, list[discord.Member]]:
        """Check if user is in a voice channel and get members."""
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You must be in a voice channel to use this command.",
                ephemeral=True
            )
            return False, None, []
            
        voice_channel = interaction.user.voice.channel
        voice_members = [m for m in voice_channel.members if not m.bot]
        return True, voice_channel, voice_members
