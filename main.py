import discord
from discord.ext import commands
import asyncio
import os
import logging
from pathlib import Path

from config.config import BOT_TOKEN, COMMAND_PREFIX
from utils.logger import BotLogger

# Set up logging
logger = BotLogger()

# Initialize intents - use all intents for maximum compatibility
intents = discord.Intents.all()
logger.info("Using all intents for maximum compatibility")
logger.info(f"Message content intent: {intents.message_content}")
class FractalBot(commands.Bot):
    """
    Custom bot class with enhanced functionality.
    
    This class extends the discord.py Bot class with additional features
    like automatic cog loading and command syncing.
    """
    
    def __init__(self):
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=intents,
            activity=discord.Game(name="/fractalgroup")
        )
        self.synced = False
        self.logger = logger
        
    async def setup_hook(self):
        """Set up the bot before it starts running."""
        self.logger.info("=== Starting bot setup ===")
        
        try:
            # Load cogs
            active_cogs = ['fractal', 'timer']
            
            for cog_name in active_cogs:
                try:
                    # Use the actual module structure which has 'cog.py' in each directory
                    await self.load_extension(f"cogs.{cog_name}.cog")
                    self.logger.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {cog_name}: {e}")
            
            self.logger.info("All cogs loaded successfully")
            
        except Exception as e:
            self.logger.error("Error in setup", exc_info=e)
            raise
            
        self.logger.info("=== Bot setup complete ===")
    
    async def sync_commands(self):
        """Sync application commands with Discord."""
        try:
            self.logger.info("Syncing commands...")
            
            # If we have guilds, sync to each guild for faster updates
            if len(self.guilds) > 0:
                for guild in self.guilds:
                    self.logger.info(f"Syncing commands to guild: {guild.name}")
                    await self.tree.sync(guild=discord.Object(id=guild.id))
                    self.logger.info(f"Commands synced to guild {guild.id}")
            
            # Also sync globally
            await self.tree.sync()
            self.logger.info("Commands synced globally")
            
            self.synced = True
                
        except Exception as e:
            self.logger.error("Error syncing commands", exc_info=e)
            raise
    
    async def on_ready(self):
        logger.info("=== Bot Starting Up ===")
        logger.info(f"Bot: {self.user} (ID: {self.user.id})")
        await self.wait_until_ready()
        
        # Check bot permissions
        for guild in self.guilds:
            logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")
            me = guild.get_member(self.user.id)
            missing_perms = []
            
            # Check for required permissions
            if not me.guild_permissions.manage_messages:
                missing_perms.append("Manage Messages")
            if not me.guild_permissions.manage_threads:
                missing_perms.append("Manage Threads")
            if not me.guild_permissions.create_public_threads:
                missing_perms.append("Create Public Threads")
                
            if missing_perms:
                logger.warning(f"Missing permissions in {guild.name}: {', '.join(missing_perms)}")
        
        # Sync commands after bot is ready and in guilds
        if not self.synced:
            await self.sync_commands()
            
        self.logger.startup(self)
        
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        logger.info(f"Command '{command.name}' completed by {interaction.user} (ID: {interaction.user.id})")
        
    async def on_app_command(self, interaction: discord.Interaction):
        logger.info(f"Command '{interaction.command.name}' invoked by {interaction.user} (ID: {interaction.user.id})")
        
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        self.logger.error(f"Command error in {ctx.command}", exc_info=error)
        
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all interactions with the bot. This is crucial for slash commands."""
        # Log detailed information about the interaction to help debug slash commands
        self.logger.info(f"INTERACTION RECEIVED: Type={interaction.type}, User={interaction.user.name}, ID={interaction.user.id}")
        
        if hasattr(interaction, 'data') and interaction.data:
            self.logger.info(f"INTERACTION DATA: {interaction.data}")
            
            # If this is an application command, log which command is being invoked
            if interaction.type == discord.InteractionType.application_command:
                command_name = interaction.data.get('name', 'unknown')
                self.logger.info(f"SLASH COMMAND INVOKED: /{command_name}")
        
        # Let discord.py handle the interaction - no need to do anything more here

def main():
    """Main entry point for the bot."""
    # Initialize the bot
    bot = FractalBot()
    
    # Add sync command
    @bot.tree.command(
        name="sync",
        description="Manually sync commands (owner only)"
    )
    async def sync(interaction: discord.Interaction):
        """Manually sync commands with Discord."""
        try:
            guild = interaction.guild
            if guild:
                # Sync commands to this specific guild
                await bot.tree.sync(guild=discord.Object(id=guild.id))
                bot.logger.info(f"Commands explicitly synced to guild {guild.id}")
                await interaction.response.send_message(
                    "✅ Commands synced to this server! Try using /fractalgroup now.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⚠️ You must use this command in a server, not in DMs.",
                    ephemeral=True
                )
        except Exception as e:
            bot.logger.error(f"Error syncing commands: {e}", exc_info=e)
            await interaction.response.send_message(
                f"❌ Error syncing commands: {str(e)}",
                ephemeral=True
            )
    
    # Add a simple direct fractalgroup command for testing
    @bot.tree.command(
        name="directfractalgroup",
        description="Direct command to create a fractal group (test version)"
    )
    async def directfractalgroup(interaction: discord.Interaction):
        """Direct test implementation of fractalgroup command."""
        bot.logger.info(f"directfractalgroup command invoked by {interaction.user.name}")
        
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You must be in a voice channel to use this command.",
                ephemeral=True
            )
            return
        
        # Log success and respond
        bot.logger.info("Direct fractalgroup command completed successfully")
        await interaction.response.send_message(
            "✅ Direct fractalgroup command worked! This confirms slash commands are functioning correctly.",
            ephemeral=True
        )
        
    # Add a test command
    @bot.tree.command(
        name="test",
        description="Test if slash commands are working"
    )
    async def test(interaction: discord.Interaction):
        """Simple test command to verify slash commands work."""
        bot.logger.info(f"Test command executed by {interaction.user.name}")
        await interaction.response.send_message(
            "✅ Slash commands are working correctly! Try /sync to register all commands to this server.",
            ephemeral=True
        )
    
    # Run the bot
    try:
        asyncio.run(bot.start(BOT_TOKEN))
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error("Bot crashed", exc_info=e)
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
