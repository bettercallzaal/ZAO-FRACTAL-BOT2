import discord
from discord.ext import commands
import asyncio
import os
import logging
from pathlib import Path

from config.config import BOT_TOKEN, COMMAND_PREFIX, INTENTS
from utils.logger import BotLogger

# Set up logging
logger = BotLogger()

# Initialize intents
intents = discord.Intents.default()
for intent_name, enabled in INTENTS.items():
    setattr(intents, intent_name, enabled)
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
            # Load only fractal and timer cogs
            cogs = ['fractal', 'timer']
            for cog_name in cogs:
                try:
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
            
            # Sync commands globally
            await self.tree.sync()
            self.synced = True
            
            # Log registered commands
            commands = await self.tree.fetch_commands()
            self.logger.info("Registered commands:")
            for cmd in commands:
                self.logger.info(f"  - /{cmd.name}: {cmd.description}")
                
        except Exception as e:
            self.logger.error("Error syncing commands", exc_info=e)
            raise
    
    async def on_ready(self):
        logger.info("=== Bot Starting Up ===")
        logger.info(f"Bot: {self.user} (ID: {self.user.id})")
        await self.wait_until_ready()
        
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
        if interaction.user.id != bot.owner_id:
            await interaction.response.send_message(
                "Only the bot owner can use this command.",
                ephemeral=True
            )
            return
            
        try:
            await bot.sync_commands()
            await interaction.response.send_message(
                "Commands synced successfully!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error syncing commands: {str(e)}",
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
