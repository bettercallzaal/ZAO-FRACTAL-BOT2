import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

from utils.embed_builder import create_error_embed
from utils.error_handler import handle_command_error

class VoiceCommands(commands.Cog):
    """Cog for voice channel-related commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="randomize", description="Randomize members from one voice channel to multiple target channels")
    @app_commands.describe(
        max_per_channel="Maximum number of members per target channel (default: 6)",
        exclude_channels="Comma-separated list of channel names to exclude as targets"
    )
    # Make sure the command is available in all channel types
    @app_commands.guild_only()
    async def randomize_voice(
        self, 
        interaction: discord.Interaction, 
        max_per_channel: int = 6,
        exclude_channels: str = None
    ):
        """
        Randomize members from the current voice channel to other available voice channels.
        
        Args:
            interaction: The interaction that triggered this command
            max_per_channel: Maximum number of members per target channel (default: 6)
            exclude_channels: Comma-separated list of channel names to exclude as targets
        """
        try:
            # Check if the user is in a voice channel
            if not interaction.user.voice:
                await interaction.response.send_message(
                    embed=create_error_embed("You need to be in a voice channel to use this command."),
                    ephemeral=True
                )
                return
            
            # Get the source voice channel
            source_channel = interaction.user.voice.channel
            
            # Get all voice channels in the guild
            voice_channels = [vc for vc in interaction.guild.voice_channels if vc != source_channel]
            
            # Process exclude_channels if provided
            if exclude_channels:
                exclude_list = [name.strip().lower() for name in exclude_channels.split(',')]
                voice_channels = [vc for vc in voice_channels if vc.name.lower() not in exclude_list]
            
            if not voice_channels:
                await interaction.response.send_message(
                    embed=create_error_embed("No target voice channels available."),
                    ephemeral=True
                )
                return
            
            # Get members from the source channel
            try:
                members = source_channel.members
                # Filter out bots
                members = [member for member in members if not member.bot]
            except AttributeError:
                await interaction.response.send_message(
                    embed=create_error_embed("Could not access voice channel members."),
                    ephemeral=True
                )
                return
            
            if len(members) < 2:
                await interaction.response.send_message(
                    embed=create_error_embed("Not enough members in the voice channel to randomize."),
                    ephemeral=True
                )
                return
            
            # Shuffle the members
            random.shuffle(members)
            
            # Calculate how many channels we need
            num_channels_needed = (len(members) + max_per_channel - 1) // max_per_channel
            
            if num_channels_needed > len(voice_channels):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        f"Not enough target channels. Need {num_channels_needed} channels for {len(members)} members " 
                        f"with max {max_per_channel} per channel, but only {len(voice_channels)} channels available."
                    ),
                    ephemeral=True
                )
                return
            
            # Use only the needed number of channels
            target_channels = voice_channels[:num_channels_needed]
            
            # Acknowledge the command - make sure this works in any channel type
            try:
                await interaction.response.defer(thinking=True)
            except Exception as defer_error:
                # If defer fails, try to send a message instead
                print(f"Error deferring response: {str(defer_error)}")
                await interaction.response.send_message("Randomizing voice channels...", ephemeral=True)
            
            # Create groups of members
            groups = []
            for i in range(num_channels_needed):
                start_idx = i * max_per_channel
                end_idx = min(start_idx + max_per_channel, len(members))
                groups.append(members[start_idx:end_idx])
            
            # Move members to their assigned channels
            move_tasks = []
            for i, group in enumerate(groups):
                target_channel = target_channels[i]
                for member in group:
                    move_tasks.append(member.move_to(target_channel))
            
            # Execute all moves concurrently
            await asyncio.gather(*move_tasks)
            
            # Create a summary embed
            embed = discord.Embed(
                title="Voice Channel Randomization",
                description=f"Successfully randomized {len(members)} members into {len(groups)} channels.",
                color=0x57F287
            )
            
            # Add details for each group
            for i, (group, channel) in enumerate(zip(groups, target_channels)):
                member_list = "\n".join([f"• {member.display_name}" for member in group])
                embed.add_field(
                    name=f"Group {i+1} - {channel.name}",
                    value=member_list or "No members",
                    inline=False
                )
            
            # Send the follow-up message with results
            try:
                await interaction.followup.send(embed=embed)
            except Exception as followup_error:
                # If followup fails, try to send a new message
                print(f"Error sending followup: {str(followup_error)}")
                try:
                    await interaction.channel.send(embed=embed)
                except:
                    pass  # If all else fails, just continue
        
        except discord.Forbidden:
            # Handle permission errors
            try:
                await interaction.followup.send(
                    embed=create_error_embed("I don't have permission to move members between voice channels."),
                    ephemeral=True
                )
            except:
                try:
                    await interaction.channel.send(
                        embed=create_error_embed("I don't have permission to move members between voice channels.")
                    )
                except:
                    pass  # If all else fails, just continue
        except Exception as e:
            await handle_command_error(interaction, e)

async def setup(bot):
    """Add the voice commands cog to the bot."""
    await bot.add_cog(VoiceCommands(bot))
