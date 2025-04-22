import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.embed_builder import create_fractal_group_embed, create_error_embed
from utils.error_handler import handle_command_error

# Dictionary to store active fractal groups
# Key: thread_id, Value: FractalGroup object
active_fractal_groups = {}

class FractalGroup:
    """Class representing a fractal group."""
    
    def __init__(self, name, thread, facilitator):
        self.name = name
        self.thread = thread
        self.facilitator = facilitator
        self.members = [facilitator]  # Facilitator is automatically a member
        self.created_at = datetime.now()
    
    def add_member(self, member):
        """Add a member to the fractal group."""
        if len(self.members) < 6:  # Max 6 members per fractal group
            if member not in self.members:
                self.members.append(member)
                return True
        return False
    
    def remove_member(self, member):
        """Remove a member from the fractal group."""
        if member in self.members:
            self.members.remove(member)
            return True
        return False
    
    def is_full(self):
        """Check if the fractal group is full."""
        return len(self.members) >= 6

class JoinButton(discord.ui.Button):
    """Button for joining a fractal group."""
    
    def __init__(self, fractal_group):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Join Group",
            emoji="➕",
            custom_id=f"join_fractal_{fractal_group.thread.id}"
        )
        self.fractal_group = fractal_group
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Check if the group is full
        if self.fractal_group.is_full():
            await interaction.response.send_message(
                embed=create_error_embed("This fractal group is already full (6 members)."),
                ephemeral=True
            )
            return
        
        # Add the member to the group
        success = self.fractal_group.add_member(interaction.user)
        
        if success:
            # Update the embed with the new member list
            embed = create_fractal_group_embed(
                self.fractal_group.name,
                self.fractal_group.facilitator,
                self.fractal_group.members,
                self.fractal_group.created_at
            )
            
            # Disable the button if the group is now full
            if self.fractal_group.is_full():
                self.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self.view)
            
            # Also send a notification in the thread
            await self.fractal_group.thread.send(f"{interaction.user.mention} has joined the fractal group!")
        else:
            # Member is already in the group
            await interaction.response.send_message(
                embed=create_error_embed("You are already a member of this fractal group."),
                ephemeral=True
            )

class FractalGroupView(discord.ui.View):
    """View for fractal group controls."""
    
    def __init__(self, fractal_group):
        super().__init__(timeout=None)  # No timeout for the view
        self.fractal_group = fractal_group
        
        # Add the join button
        self.add_item(JoinButton(fractal_group))

class FractalNameModal(discord.ui.Modal, title="Fractal Group Name"):
    """Modal for collecting the name of the fractal group."""
    
    # Text input for fractal group name
    group_name = discord.ui.TextInput(
        label="Group Name",
        placeholder="Enter a name for this fractal group",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        # Create a new thread for the fractal group
        thread = await interaction.channel.create_thread(
            name=f"Fractal: {self.group_name.value}",
            type=discord.ChannelType.public_thread,
            reason=f"Fractal group created by {interaction.user.display_name}"
        )
        
        # Create a new fractal group
        fractal_group = FractalGroup(self.group_name.value, thread, interaction.user)
        
        # Store the fractal group in the active fractal groups dictionary
        active_fractal_groups[thread.id] = fractal_group
        
        # Create the embed and view
        embed = create_fractal_group_embed(
            fractal_group.name,
            fractal_group.facilitator,
            fractal_group.members,
            fractal_group.created_at
        )
        view = FractalGroupView(fractal_group)
        
        # Send the initial message in the thread
        await thread.send(
            f"Welcome to the **{fractal_group.name}** fractal group!\n"
            f"This group is facilitated by {fractal_group.facilitator.mention}.\n"
            f"Use the button below to join this group (max 6 members).",
            embed=embed,
            view=view
        )
        
        # Respond to the interaction
        await interaction.response.send_message(
            f"Fractal group **{fractal_group.name}** created successfully! "
            f"Check the new thread: {thread.mention}",
            ephemeral=True
        )

class FractalCog(commands.Cog):
    """Cog for fractal group-related commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="fractalgroup", description="Create a new fractal group for a meeting")
    async def fractal_group(self, interaction: discord.Interaction):
        """Create a new fractal group for a meeting."""
        try:
            # Show the modal to get the fractal group name
            modal = FractalNameModal()
            await interaction.response.send_modal(modal)
        
        except Exception as e:
            await handle_command_error(interaction, e)
    
    @app_commands.command(name="listgroups", description="List all active fractal groups in this channel")
    async def list_groups(self, interaction: discord.Interaction):
        """List all active fractal groups in this channel."""
        try:
            # Find all fractal groups in the current channel
            channel_threads = [thread for thread in interaction.channel.threads 
                              if thread.id in active_fractal_groups]
            
            if not channel_threads:
                await interaction.response.send_message(
                    "There are no active fractal groups in this channel.",
                    ephemeral=True
                )
                return
            
            # Create an embed to list all groups
            embed = discord.Embed(
                title="Active Fractal Groups",
                description=f"There are {len(channel_threads)} active fractal groups in this channel:",
                color=0x5865F2
            )
            
            for thread in channel_threads:
                fractal_group = active_fractal_groups[thread.id]
                embed.add_field(
                    name=fractal_group.name,
                    value=f"Facilitator: {fractal_group.facilitator.mention}\n"
                          f"Members: {len(fractal_group.members)}/6\n"
                          f"Thread: {thread.mention}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            await handle_command_error(interaction, e)

async def setup(bot):
    """Add the fractal cog to the bot."""
    await bot.add_cog(FractalCog(bot))
