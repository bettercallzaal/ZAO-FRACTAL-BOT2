import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Check if token is available
if not TOKEN:
    print("ERROR: No Discord token found. Please add your token to the .env file.")
    print("Example: DISCORD_TOKEN=your_token_here")
    exit(1)

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
class FractalBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False
        
    async def on_ready(self):
        """Event handler for when the bot is ready."""
        await self.wait_until_ready()
        if not self.synced:
            # Sync commands with Discord
            await self.tree.sync()
            self.synced = True
        
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        
    async def setup_hook(self):
        """Setup hook for loading cogs."""
        # Load command modules
        from timer_commands import setup as timer_setup
        from fractal_commands import setup as fractal_setup
        from respect_commands import setup as respect_setup
        from summary_commands import setup as summary_setup
        
        await timer_setup(self)
        await fractal_setup(self)
        await respect_setup(self)
        await summary_setup(self)

# Initialize the bot
bot = FractalBot()

# Command to manually sync commands (admin only)
@bot.tree.command(name="sync", description="Manually sync commands (admin only)")
async def sync(interaction: discord.Interaction):
    """Manually sync commands with Discord."""
    # Check if the user has administrator permissions
    if interaction.user.guild_permissions.administrator:
        await bot.tree.sync()
        await interaction.response.send_message("Commands synced successfully!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
