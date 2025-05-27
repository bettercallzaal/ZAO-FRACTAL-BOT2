import discord
from discord.ui import Button, View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .group import FractalGroup

class VoteButton(Button):
    """Button for voting for a specific candidate."""
    
    def __init__(self, candidate: discord.Member, fractal_group: 'FractalGroup', index: int, row: int = 0):
        # Get the candidate's name, truncate if too long
        name = candidate.display_name
        if len(name) > 15:
            name = name[:12] + "..."
            
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{index+1}. {name}",
            row=row
        )
        self.candidate = candidate
        self.fractal_group = fractal_group
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Check if user can vote
        if interaction.user not in self.fractal_group.members and interaction.user not in self.fractal_group.external_voters:
            await interaction.response.send_message(
                "You are not allowed to vote in this group.",
                ephemeral=True
            )
            return
            
        # Record the vote
        success = await self.fractal_group.record_vote(interaction.user, self.candidate)
        
        if success:
            # Acknowledge the vote
            await interaction.response.send_message(
                f"You voted for {self.candidate.mention}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Failed to record your vote. Please try again.",
                ephemeral=True
            )

class JoinButton(Button):
    """Button for joining a fractal group."""
    
    def __init__(self, fractal_group: 'FractalGroup'):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Join Group",
            emoji="➕",
            custom_id=f"join_fractal_{fractal_group.thread.id}"
        )
        self.fractal_group = fractal_group

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Check if group is full
        if self.fractal_group.is_full():
            await interaction.response.send_message(
                "This fractal group is full.",
                ephemeral=True
            )
            return
            
        # Check if user is already in a group
        cog = self.fractal_group.thread.guild.get_cog('FractalCog')
        if not cog:
            await interaction.response.send_message(
                "Error: FractalCog not found",
                ephemeral=True
            )
            return
            
        if interaction.user.id in cog.member_groups:
            existing_thread_id = cog.member_groups[interaction.user.id]
            if existing_thread_id != self.fractal_group.thread.id:
                await interaction.response.send_message(
                    "You are already in another fractal group.",
                    ephemeral=True
                )
                return
        
        # Add member to group
        self.fractal_group.add_member(interaction.user)
        cog.member_groups[interaction.user.id] = self.fractal_group.thread.id
        
        try:
            await self.fractal_group.thread.add_user(interaction.user)
            await interaction.response.send_message(
                f"You have joined the fractal group!",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to add you to the thread: {str(e)}",
                ephemeral=True
            )

class AdminControlsButton(Button):
    """Button to show admin controls for managing spectators and voters."""
    
    def __init__(self, fractal_group: 'FractalGroup'):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Admin Controls",
            emoji="⚙️",
            row=1
        )
        self.fractal_group = fractal_group

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Check if user is admin or facilitator
        if not interaction.user.guild_permissions.administrator and interaction.user != self.fractal_group.facilitator:
            await interaction.response.send_message(
                "You don't have permission to use admin controls.",
                ephemeral=True
            )
            return
            
        # Create admin controls view
        view = AdminControlsView(self.fractal_group)
        
        await interaction.response.send_message(
            "Admin Controls",
            view=view,
            ephemeral=True
        )

class VotingView(View):
    """View for fractal group voting."""
    
    def __init__(self, fractal_group: 'FractalGroup'):
        super().__init__(timeout=None)
        
        # Add voting buttons
        for i, member in enumerate(fractal_group.members):
            self.add_item(VoteButton(member, fractal_group, i))

class FractalGroupView(View):
    """View for fractal group controls."""
    
    def __init__(self, fractal_group: 'FractalGroup'):
        super().__init__(timeout=None)
        
        # Add the join button
        self.add_item(JoinButton(fractal_group))
        
        # Add admin controls
        self.add_item(AdminControlsButton(fractal_group))

class AdminControlsView(View):
    """View for admin controls."""
    
    def __init__(self, fractal_group: 'FractalGroup'):
        super().__init__(timeout=60)  # Timeout after 1 minute
        self.fractal_group = fractal_group
