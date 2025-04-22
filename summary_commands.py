import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

from utils.embed_builder import create_summary_embed, create_error_embed
from utils.error_handler import handle_command_error

class SummaryCog(commands.Cog):
    """Cog for discussion summarization commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="summarize", description="Generate a summary of the discussion in this thread")
    async def summarize(self, interaction: discord.Interaction):
        """Generate a summary of the discussion in this thread."""
        try:
            # Check if this is a thread
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.response.send_message(
                    embed=create_error_embed("This command can only be used in a thread."),
                    ephemeral=True
                )
                return
            
            # Defer the response since this might take a while
            await interaction.response.defer(thinking=True)
            
            # Collect messages from the thread
            messages = []
            async for message in interaction.channel.history(limit=100):
                # Skip bot messages and commands
                if not message.author.bot and not message.content.startswith('/'):
                    messages.append(message)
            
            if not messages:
                await interaction.followup.send(
                    embed=create_error_embed("No messages found to summarize."),
                    ephemeral=True
                )
                return
            
            # Sort messages by timestamp (oldest first)
            messages.sort(key=lambda m: m.created_at)
            
            # Extract content and metadata
            message_data = [
                {
                    'author': message.author.display_name,
                    'content': message.content,
                    'timestamp': message.created_at.isoformat()
                }
                for message in messages
            ]
            
            # Generate summary (simplified version - in a real bot, this would use an AI service)
            summary = self._generate_summary(message_data, interaction.channel.name)
            
            # Create and send the summary embed
            embed = create_summary_embed(interaction.channel.name, summary)
            
            # Add a button for exporting the summary
            view = SummaryExportView(summary, interaction.channel.name)
            
            await interaction.followup.send(embed=embed, view=view)
        
        except Exception as e:
            await handle_command_error(interaction, e)
    
    def _generate_summary(self, message_data, channel_name):
        """
        Generate a summary of the discussion.
        
        In a real implementation, this would use an AI service like OpenAI's API.
        For this demo, we'll use a simplified approach.
        """
        # Count messages per author
        author_counts = {}
        for msg in message_data:
            author = msg['author']
            author_counts[author] = author_counts.get(author, 0) + 1
        
        # Get top contributors
        top_contributors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Get time span
        if message_data:
            start_time = datetime.fromisoformat(message_data[0]['timestamp'])
            end_time = datetime.fromisoformat(message_data[-1]['timestamp'])
            duration = end_time - start_time
        else:
            duration = timedelta(0)
        
        # Extract some key phrases (simplified)
        all_content = " ".join([msg['content'] for msg in message_data])
        words = all_content.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only consider words longer than 4 characters
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Build summary
        summary = f"**Discussion Summary**\n\n"
        
        summary += f"This discussion in {channel_name} lasted for {self._format_duration(duration)} "
        summary += f"and included {len(message_data)} messages from {len(author_counts)} participants.\n\n"
        
        if top_contributors:
            summary += "**Top Contributors:**\n"
            for author, count in top_contributors[:3]:
                summary += f"• {author}: {count} messages\n"
            summary += "\n"
        
        if top_words:
            summary += "**Key Topics:**\n"
            for word, count in top_words:
                summary += f"• {word} (mentioned {count} times)\n"
            summary += "\n"
        
        summary += "**Action Items:**\n"
        summary += "• No specific action items were identified in this discussion.\n\n"
        
        summary += "**Decisions:**\n"
        summary += "• No formal decisions were recorded in this discussion.\n\n"
        
        summary += "*Note: This is an automated summary. For a more accurate summary, please review the full discussion.*"
        
        return summary
    
    def _format_duration(self, duration):
        """Format a timedelta into a human-readable string."""
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        if not parts:
            return "less than a minute"
        
        return ", ".join(parts)

class SummaryExportView(discord.ui.View):
    """View for summary export button."""
    
    def __init__(self, summary_text, channel_name):
        super().__init__(timeout=None)
        self.summary_text = summary_text
        self.channel_name = channel_name
    
    @discord.ui.button(label="Export Summary", style=discord.ButtonStyle.primary, emoji="📄")
    async def export_summary(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Export the summary as a text file."""
        # Create a file with the summary
        file_name = f"{self.channel_name.replace(' ', '_')}_summary.txt"
        file = discord.File(
            fp=self._string_to_file(self.summary_text),
            filename=file_name
        )
        
        # Send the file
        await interaction.response.send_message(
            "Here's your exported summary:",
            file=file,
            ephemeral=True
        )
    
    def _string_to_file(self, content):
        """Convert a string to a file-like object."""
        import io
        return io.BytesIO(content.encode('utf-8'))

async def setup(bot):
    """Add the summary cog to the bot."""
    await bot.add_cog(SummaryCog(bot))
