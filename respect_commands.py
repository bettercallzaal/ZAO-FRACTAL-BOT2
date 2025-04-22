import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime

from utils.embed_builder import create_respect_vote_embed, create_respect_results_embed, create_error_embed
from utils.error_handler import handle_command_error

# Dictionary to store active voting sessions
# Key: thread_id, Value: RespectVote object
active_votes = {}

class RespectVote:
    """Class for managing the Respect Game voting process."""
    
    def __init__(self, thread, members):
        self.thread = thread
        self.members = members  # List of members in the fractal group
        self.current_voter_index = 0
        self.votes = {member: 0 for member in members}  # Initialize vote counts to 0
        self.voted = set()  # Set of members who have already voted
        self.message = None  # Message containing the voting UI
    
    @property
    def current_voter(self):
        """Get the current voter."""
        if 0 <= self.current_voter_index < len(self.members):
            return self.members[self.current_voter_index]
        return None
    
    def next_voter(self):
        """Move to the next voter."""
        self.current_voter_index += 1
        
        # Skip any voters who have already voted (in case of rejoining)
        while (self.current_voter_index < len(self.members) and 
               self.members[self.current_voter_index] in self.voted):
            self.current_voter_index += 1
        
        return self.current_voter
    
    def record_vote(self, voter, candidate):
        """Record a vote from a voter to a candidate."""
        if voter in self.members and candidate in self.members:
            self.votes[candidate] += 1
            self.voted.add(voter)
            return True
        return False
    
    def is_complete(self):
        """Check if the voting process is complete."""
        return len(self.voted) >= len(self.members)
    
    def get_results(self):
        """Get the voting results."""
        return self.votes

class CandidateSelect(discord.ui.Select):
    """Dropdown select for choosing a candidate to vote for."""
    
    def __init__(self, respect_vote, candidates):
        # Create options for each candidate
        options = [
            discord.SelectOption(
                label=candidate.display_name,
                value=str(candidate.id),
                description=f"Vote for {candidate.display_name}"
            )
            for candidate in candidates
        ]
        
        super().__init__(
            placeholder="Select a member to vote for...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"respect_vote_select_{respect_vote.thread.id}"
        )
        
        self.respect_vote = respect_vote
    
    async def callback(self, interaction: discord.Interaction):
        """Handle selection."""
        # Check if the interaction user is the current voter
        if interaction.user != self.respect_vote.current_voter:
            await interaction.response.send_message(
                "It's not your turn to vote.",
                ephemeral=True
            )
            return
        
        # Get the selected candidate
        candidate_id = int(self.values[0])
        candidate = discord.utils.get(self.respect_vote.members, id=candidate_id)
        
        if candidate:
            # Record the vote
            success = self.respect_vote.record_vote(interaction.user, candidate)
            
            if success:
                await interaction.response.send_message(
                    f"You voted for {candidate.mention}!",
                    ephemeral=True
                )
                
                # Move to the next voter
                next_voter = self.respect_vote.next_voter()
                
                if next_voter:
                    # Continue with the next voter
                    # Get candidates excluding the next voter (no self-voting)
                    candidates = [m for m in self.respect_vote.members if m != next_voter]
                    
                    # Update the embed and view
                    embed = create_respect_vote_embed(next_voter, candidates)
                    view = RespectVoteView(self.respect_vote, candidates)
                    
                    await self.respect_vote.message.edit(embed=embed, view=view)
                    await self.respect_vote.thread.send(f"{next_voter.mention}, it's your turn to vote!")
                else:
                    # Voting is complete
                    results = self.respect_vote.get_results()
                    results_embed = create_respect_results_embed(results)
                    
                    await self.respect_vote.message.edit(
                        content="Voting has completed! Here are the results:",
                        embed=results_embed,
                        view=None
                    )
                    
                    # Clean up
                    if self.respect_vote.thread.id in active_votes:
                        del active_votes[self.respect_vote.thread.id]
            else:
                await interaction.response.send_message(
                    "There was an error recording your vote. Please try again.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "Invalid candidate selection. Please try again.",
                ephemeral=True
            )

class RespectVoteView(discord.ui.View):
    """View for respect voting UI."""
    
    def __init__(self, respect_vote, candidates):
        super().__init__(timeout=None)  # No timeout
        
        # Add the candidate select dropdown
        self.add_item(CandidateSelect(respect_vote, candidates))

class RespectCog(commands.Cog):
    """Cog for respect game-related commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="respectvote", description="Start the Respect Game voting process")
    async def respect_vote(self, interaction: discord.Interaction):
        """Start the Respect Game voting process in a fractal group thread."""
        try:
            # Check if this is a thread
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.response.send_message(
                    embed=create_error_embed("This command can only be used in a fractal group thread."),
                    ephemeral=True
                )
                return
            
            thread_id = interaction.channel.id
            
            # Check if there's already an active vote in this thread
            if thread_id in active_votes:
                await interaction.response.send_message(
                    embed=create_error_embed("There's already an active voting session in this thread."),
                    ephemeral=True
                )
                return
            
            # Get all members in the thread
            thread_members = []
            async for member in interaction.channel.fetch_members():
                user = interaction.guild.get_member(member.id)
                if user and not user.bot:  # Exclude bots
                    thread_members.append(user)
            
            if len(thread_members) < 2:
                await interaction.response.send_message(
                    embed=create_error_embed("At least 2 members are required for the Respect Game."),
                    ephemeral=True
                )
                return
            
            # Create a new respect vote
            respect_vote = RespectVote(interaction.channel, thread_members)
            
            # Store in active votes
            active_votes[thread_id] = respect_vote
            
            # Get the first voter
            first_voter = respect_vote.current_voter
            
            # Get candidates excluding the first voter (no self-voting)
            candidates = [m for m in thread_members if m != first_voter]
            
            # Create the embed and view
            embed = create_respect_vote_embed(first_voter, candidates)
            view = RespectVoteView(respect_vote, candidates)
            
            # Send the initial message
            await interaction.response.send_message(
                f"Starting the Respect Game voting process!\n"
                f"{first_voter.mention}, it's your turn to vote!",
                embed=embed,
                view=view
            )
            
            # Store the message for later updates
            respect_vote.message = await interaction.original_response()
        
        except Exception as e:
            await handle_command_error(interaction, e)
    
    @app_commands.command(name="respectresults", description="Show the results of the Respect Game voting")
    async def respect_results(self, interaction: discord.Interaction):
        """Show the results of the Respect Game voting."""
        try:
            thread_id = interaction.channel.id
            
            # Check if there's an active vote in this thread
            if thread_id in active_votes:
                respect_vote = active_votes[thread_id]
                
                # Check if voting is complete
                if respect_vote.is_complete():
                    results = respect_vote.get_results()
                    results_embed = create_respect_results_embed(results)
                    
                    await interaction.response.send_message(
                        embed=results_embed
                    )
                else:
                    await interaction.response.send_message(
                        embed=create_error_embed("Voting is still in progress."),
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("There's no active or completed voting session in this thread."),
                    ephemeral=True
                )
        
        except Exception as e:
            await handle_command_error(interaction, e)

async def setup(bot):
    """Add the respect cog to the bot."""
    await bot.add_cog(RespectCog(bot))
