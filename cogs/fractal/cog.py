import discord
import uuid
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List

from ..base import BaseCog
from .group import FractalGroup
from .views import FractalGroupView
from config.config import (
    MIN_GROUP_SIZE,
    THREAD_CLEANUP_INTERVAL,
    THREAD_INACTIVE_THRESHOLD
)

class FractalCog(BaseCog):
    """Cog for managing fractal groups and voting."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self._lock = asyncio.Lock()
        self._active_commands = set()
        self.cleanup_task = self.bot.loop.create_task(self.periodic_cleanup())
        
        # State management
        self.active_fractal_groups: Dict[int, FractalGroup] = {}
        self.member_groups: Dict[int, int] = {}
        
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.cleanup_task.cancel()

    @tasks.loop(seconds=THREAD_CLEANUP_INTERVAL)
    async def periodic_cleanup(self):
        """Periodically clean up inactive fractal groups."""
        try:
            now = datetime.now()
            to_remove = []
            
            for thread_id, group in list(self.active_fractal_groups.items()):
                # Check if thread still exists
                try:
                    thread = await self.bot.fetch_channel(thread_id)
                    if not thread:
                        to_remove.append(thread_id)
                        continue
                except discord.NotFound:
                    to_remove.append(thread_id)
                    continue
                
                # Check if thread is inactive
                if now - group.created_at > timedelta(seconds=THREAD_INACTIVE_THRESHOLD):
                    await thread.edit(archived=True, locked=True)
                    to_remove.append(thread_id)
            
            # Clean up removed groups
            for thread_id in to_remove:
                if thread_id in self.active_fractal_groups:
                    group = self.active_fractal_groups.pop(thread_id)
                    # Clean up member tracking
                    for member in group.members:
                        if member.id in self.member_groups and self.member_groups[member.id] == thread_id:
                            del self.member_groups[member.id]
                            
            self.logger.info(f"Cleaned up {len(to_remove)} inactive fractal groups")
            
        except Exception as e:
            self.logger.error("Error in periodic cleanup", exc_info=e)

    class FractalGroupModal(discord.ui.Modal, title='Create Fractal Group'):
        name = discord.ui.TextInput(
            label='Group Name',
            placeholder='Enter a name for the fractal group...',
            required=True,
            max_length=100
        )
        
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.modal_id = str(uuid.uuid4())  # Unique ID for this modal instance
            self.cog.logger.info(f"[{self.modal_id}] Created new FractalGroupModal")
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                self.cog.logger.info(f"[{self.modal_id}] Modal submitted by {interaction.user} (ID: {interaction.user.id})")
                thread_name = self.name.value
                self.cog.logger.info(f"[{self.modal_id}] Thread name: {thread_name}")
                
                # Defer the response immediately
                self.cog.logger.info(f"[{self.modal_id}] Deferring response")
                await interaction.response.defer(ephemeral=True)
                self.cog.logger.info(f"[{self.modal_id}] Response deferred")
                
                # Check voice state
                self.cog.logger.info(f"[{self.modal_id}] Checking voice state")
                if not interaction.user.voice or not interaction.user.voice.channel:
                    self.cog.logger.warning(f"[{self.modal_id}] User not in voice channel")
                    await interaction.followup.send(
                        "You must be in a voice channel to use this command.",
                        ephemeral=True
                    )
                    return
                    
                voice_channel = interaction.user.voice.channel
                voice_members = [m for m in voice_channel.members if not m.bot]
                self.cog.logger.info(f"[{self.modal_id}] Voice channel: {voice_channel.name} (ID: {voice_channel.id})")
                self.cog.logger.info(f"[{self.modal_id}] Members in voice: {[m.name for m in voice_members]}")
                    
                if len(voice_members) < MIN_GROUP_SIZE:
                    self.cog.logger.warning(f"[{self.modal_id}] Not enough members in voice ({len(voice_members)} < {MIN_GROUP_SIZE})")
                    await interaction.followup.send(
                        f"You need at least {MIN_GROUP_SIZE} members in the voice channel.",
                        ephemeral=True
                    )
                    return
                
                self.cog.logger.info(f"[{self.modal_id}] Acquiring lock")
                async with self.cog._lock:
                    self.cog.logger.info(f"[{self.modal_id}] Lock acquired")
                    # Check if any members are already in a group
                    busy_members = []
                    for member in voice_members:
                        if member.id in self.cog.member_groups:
                            group_id = self.cog.member_groups[member.id]
                            group = self.cog.active_fractal_groups.get(group_id)
                            if group:
                                busy_members.append(f"{member.mention} (in {group.name})")
                                self.cog.logger.warning(f"[{self.modal_id}] Member {member.name} already in group {group.name}")
                    
                    if busy_members:
                        self.cog.logger.warning(f"[{self.modal_id}] Found busy members: {busy_members}")
                        await interaction.followup.send(
                            "The following members are already in a fractal group:\n" +
                            "\n".join(busy_members),
                            ephemeral=True
                        )
                        return
                    
                    try:
                        # Create thread
                        self.cog.logger.info(f"[{self.modal_id}] Creating thread '{thread_name}'")
                        thread = await interaction.channel.create_thread(
                            name=thread_name,
                            type=discord.ChannelType.public_thread,
                            reason=f"Fractal group created by {interaction.user.name}"
                        )
                        self.cog.logger.info(f"[{self.modal_id}] Thread created with ID: {thread.id}")
                        
                        # Create fractal group
                        self.cog.logger.info(f"[{self.modal_id}] Creating FractalGroup object")
                        group = FractalGroup(thread_name, thread, interaction.user)
                        
                        # Add members
                        self.cog.logger.info(f"[{self.modal_id}] Adding members to thread")
                        for member in voice_members:
                            if member != interaction.user:  # Skip facilitator
                                group.add_member(member)
                                try:
                                    await thread.add_user(member)
                                    self.cog.logger.info(f"[{self.modal_id}] Added {member.name} to thread")
                                except discord.HTTPException as e:
                                    self.cog.logger.warning(f"[{self.modal_id}] Failed to add {member.name} to thread: {e}")
                        
                        # Store group
                        self.cog.logger.info(f"[{self.modal_id}] Storing group in active_fractal_groups")
                        self.cog.active_fractal_groups[thread.id] = group
                        for member in voice_members:
                            self.cog.member_groups[member.id] = thread.id
                            self.cog.logger.info(f"[{self.modal_id}] Mapped {member.name} to thread {thread.id}")
                        
                        # Send welcome message
                        self.cog.logger.info(f"[{self.modal_id}] Sending welcome message")
                        await thread.send(
                            f"🎯 **New Fractal Group**\n\n"
                            f"• Facilitator: {interaction.user.mention}\n"
                            f"• Members: {', '.join(m.mention for m in voice_members)}\n\n"
                            f"Starting Level 6 voting..."
                        )
                        
                        # Start voting
                        self.cog.logger.info(f"[{self.modal_id}] Starting voting round")
                        await group.start_new_round()
                        
                        self.cog.logger.info(f"[{self.modal_id}] Sending success message")
                        await interaction.followup.send(
                            f"Created fractal group in {thread.mention}",
                            ephemeral=True
                        )
                        self.cog.logger.info(f"[{self.modal_id}] Group creation complete")
                        
                    except discord.HTTPException as e:
                        self.cog.logger.error(f"[{self.modal_id}] HTTP error creating thread: {str(e)}")
                        await interaction.followup.send(
                            f"Error creating thread: {str(e)}",
                            ephemeral=True
                        )
                    except Exception as e:
                        self.cog.logger.error(f"[{self.modal_id}] Unexpected error: {str(e)}", exc_info=e)
                        await interaction.followup.send(
                            f"An unexpected error occurred: {str(e)}",
                            ephemeral=True
                        )
                    
                self.cog.logger.info(f"[{self.modal_id}] Lock released")
                
            except Exception as e:
                self.cog.logger.error(f"[{self.modal_id}] Critical error in on_submit: {str(e)}", exc_info=e)
                try:
                    await interaction.followup.send(
                        "A critical error occurred. Please try again.",
                        ephemeral=True
                    )
                except:
                    pass

    class FractalGroupModal(discord.ui.Modal, title='Create Fractal Group'):
        """Modal for creating a new fractal group with a custom name."""
        name = discord.ui.TextInput(
            label='Group Name',
            placeholder='Enter a name for the fractal group...',
            required=True,
            max_length=100
        )
        
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.modal_id = str(uuid.uuid4())  # Unique ID for this modal instance
            self.cog.logger.debug(f"Created modal instance {self.modal_id}")
        
        async def on_submit(self, interaction: discord.Interaction):
            """Handle modal submission and create a fractal group."""
            try:
                thread_name = self.name.value
                self.cog.logger.info(f"Creating fractal group '{thread_name}' requested by {interaction.user.name}")
                
                # Defer the response immediately
                await interaction.response.defer(ephemeral=True)
                
                # Check voice state
                if not interaction.user.voice or not interaction.user.voice.channel:
                    await interaction.followup.send(
                        "You must be in a voice channel to use this command.",
                        ephemeral=True
                    )
                    return
                    
                voice_channel = interaction.user.voice.channel
                voice_members = [m for m in voice_channel.members if not m.bot]
                    
                if len(voice_members) < MIN_GROUP_SIZE:
                    self.cog.logger.info(f"Not enough members in voice ({len(voice_members)} < {MIN_GROUP_SIZE})")
                    await interaction.followup.send(
                        f"You need at least {MIN_GROUP_SIZE} members in the voice channel.",
                        ephemeral=True
                    )
                    return
                
                async with self.cog._lock:
                    # Check if any members are already in a group
                    busy_members = []
                    for member in voice_members:
                        if member.id in self.cog.member_groups:
                            group_id = self.cog.member_groups[member.id]
                            group = self.cog.active_fractal_groups.get(group_id)
                            if group:
                                busy_members.append(f"{member.mention} (in {group.name})")
                    
                    if busy_members:
                        await interaction.followup.send(
                            "The following members are already in a fractal group:\n" +
                            "\n".join(busy_members),
                            ephemeral=True
                        )
                        return
                    
                    try:
                        # Create thread
                        thread = await interaction.channel.create_thread(
                            name=thread_name,
                            type=discord.ChannelType.public_thread,
                            reason=f"Fractal group created by {interaction.user.name}"
                        )
                        self.cog.logger.info(f"Created thread '{thread_name}' (ID: {thread.id})")
                        
                        # Create fractal group
                        group = FractalGroup(thread_name, thread, interaction.user)
                        
                        # Add members
                        for member in voice_members:
                            if member != interaction.user:  # Skip facilitator
                                group.add_member(member)
                                try:
                                    await thread.add_user(member)
                                except discord.HTTPException as e:
                                    self.cog.logger.warning(f"Failed to add {member.name} to thread: {e}")
                        
                        # Store group
                        self.cog.active_fractal_groups[thread.id] = group
                        for member in voice_members:
                            self.cog.member_groups[member.id] = thread.id
                        
                        # Send welcome message
                        await thread.send(
                            f"🎯 **New Fractal Group**\n\n"
                            f"• Facilitator: {interaction.user.mention}\n"
                            f"• Members: {', '.join(m.mention for m in voice_members)}\n\n"
                            f"Starting Level 6 voting..."
                        )
                        
                        # Start voting
                        await group.start_new_round()
                        
                        await interaction.followup.send(
                            f"Created fractal group in {thread.mention}",
                            ephemeral=True
                        )
                        
                    except discord.HTTPException as e:
                        self.cog.logger.error(f"HTTP error creating thread: {str(e)}")
                        await interaction.followup.send(
                            f"Error creating thread: {str(e)}",
                            ephemeral=True
                        )
                    except Exception as e:
                        self.cog.logger.error(f"Unexpected error: {str(e)}", exc_info=e)
                        await interaction.followup.send(
                            f"An unexpected error occurred: {str(e)}",
                            ephemeral=True
                        )
                    finally:
                        # Remove from active commands when done
                        if interaction.user.id in self.cog._active_commands:
                            self.cog._active_commands.remove(interaction.user.id)
                
            except Exception as e:
                self.cog.logger.error(f"Critical error in modal submission: {str(e)}", exc_info=e)
                try:
                    await interaction.followup.send(
                        "A critical error occurred. Please try again.",
                        ephemeral=True
                    )
                except:
                    pass
                finally:
                    # Always remove from active commands on error
                    if interaction.user.id in self.cog._active_commands:
                        self.cog._active_commands.remove(interaction.user.id)

    @app_commands.command(
        name="fractalgroup",
        description="Create a new fractal group from members in your voice channel"
    )
    async def fractal(self, interaction: discord.Interaction):
        """Create a new fractal group from members in your voice channel."""
        # Prevent duplicate commands
        if interaction.user.id in self._active_commands:
            await interaction.response.send_message(
                "Please wait for your previous command to finish.",
                ephemeral=True
            )
            return
            
        try:
            # Show modal to get thread name
            modal = self.FractalGroupModal(self)
            # Add user to active commands BEFORE showing modal
            self._active_commands.add(interaction.user.id)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            self.logger.error(f"Error showing modal: {str(e)}", exc_info=e)
            await interaction.response.send_message(
                f"Error creating fractal group: {str(e)}",
                ephemeral=True
            )
            # Only remove from active commands if modal fails to show
            self._active_commands.remove(interaction.user.id)


    @app_commands.command(
        name="listgroups",
        description="List all active fractal groups in this channel"
    )
    async def list_groups(self, interaction: discord.Interaction):
        """List all active fractal groups in this channel."""
        try:
            # Find all fractal groups in the current channel
            channel_threads = [
                thread for thread in interaction.channel.threads 
                if thread.id in self.active_fractal_groups
            ]
            
            if not channel_threads:
                await interaction.response.send_message(
                    "No active fractal groups in this channel.",
                    ephemeral=True
                )
                return
            
            # Build embed
            embed = discord.Embed(
                title="Active Fractal Groups",
                color=discord.Color.blue()
            )
            
            for thread in channel_threads:
                group = self.active_fractal_groups[thread.id]
                member_list = [f"{m.mention}" for m in group.members]
                
                embed.add_field(
                    name=f"{thread.name}",
                    value=f"• Facilitator: {group.facilitator.mention}\n"
                          f"• Members: {', '.join(member_list)}\n"
                          f"• Status: {group.status}\n"
                          f"• Thread: {thread.mention}",
                    inline=False
                )
            
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
        except Exception as e:
            self.logger.error(f"Error listing groups: {str(e)}", exc_info=e)
            await interaction.response.send_message(
                f"Error listing groups: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Add the fractal cog to the bot."""
    await bot.add_cog(FractalCog(bot))
