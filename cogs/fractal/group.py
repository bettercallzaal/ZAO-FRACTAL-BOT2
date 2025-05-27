from __future__ import annotations
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from config.config import (
    DEFAULT_LEVEL,
    VOTE_PERCENTAGE_REQUIRED
)

class FractalGroup:
    """
    Represents a fractal group in the bot.
    
    This class manages the state and operations of a single fractal group,
    including member management, voting, and round progression.
    
    Attributes:
        name (str): The name of the fractal group
        thread (discord.Thread): The Discord thread where the group operates
        facilitator (discord.Member): The user who created the group
        members (List[discord.Member]): Current members of the group
        spectators (List[discord.Member]): Users who can view but not participate
        external_voters (List[discord.Member]): Users who can vote but aren't in the fractal
        created_at (datetime): When the group was created
        votes (Dict[discord.Member, discord.Member]): Current votes {voter: candidate}
        vote_counts (Dict[discord.Member, int]): Vote tallies for each candidate
        status_message (Optional[discord.Message]): Message showing current vote status
        current_level (int): Current level being voted on
        winners (List[Tuple[int, discord.Member]]): Past winners with their levels
        current_round_message (Optional[discord.Message]): Current round's voting UI
    """
    
    def __init__(self, name: str, thread: discord.Thread, facilitator: discord.Member):
        self.name = name
        self.thread = thread
        self.facilitator = facilitator
        self.members = [facilitator]
        self.spectators = []
        self.external_voters = []
        self.created_at = datetime.now()
        self.votes = {}
        self.vote_counts = {}
        self.status_message = None
        self.current_level = DEFAULT_LEVEL
        self.winners = []
        self.current_round_message = None

    async def record_vote(self, voter: discord.Member, candidate: discord.Member) -> bool:
        """
        Record a vote from a voter for a candidate.
        
        Args:
            voter: The member casting the vote
            candidate: The member being voted for
            
        Returns:
            bool: True if vote was recorded, False if voter not eligible
        """
        if voter not in self.members and voter not in self.external_voters:
            return False
            
        # Handle changed votes
        if voter in self.votes:
            previous_vote = self.votes[voter]
            if previous_vote in self.vote_counts:
                self.vote_counts[previous_vote] -= 1
        
        # Record new vote
        self.votes[voter] = candidate
        if candidate not in self.vote_counts:
            self.vote_counts[candidate] = 0
        self.vote_counts[candidate] += 1
        
        await self.update_status_message()
        return True

    async def start_new_round(self, winner: Optional[discord.Member] = None):
        """
        Start a new voting round, optionally recording a winner from the previous round.
        
        Args:
            winner: Optional winner from the previous round
        """
        if winner:
            self.winners.append((self.current_level, winner))
            if winner in self.members:
                self.members.remove(winner)
            self.current_level -= 1
            
            # Auto-win for last member
            if len(self.members) == 1:
                last_member = self.members[0]
                self.winners.append((self.current_level, last_member))
                await self.show_final_results()
                return
        
        # Reset voting state
        self.votes = {}
        self.vote_counts = {}
        self.status_message = None
        self.current_round_message = None
        
        # Create vote button view
        from .views import VotingView
        view = VotingView(self)
        
        # Create round message
        embed = discord.Embed(
            title=f"Level {self.current_level} Voting",
            description=(
                f"Vote for who you think should be Level {self.current_level}!\n\n"
                f"Click a button below to vote for that member.\n"
                f"You can change your vote at any time.\n\n"
                f"Current Members:\n"
                + "\n".join(f"• {m.mention}" for m in self.members)
            ),
            color=0x5865F2
        )
        
        # Add previous winners
        if self.winners:
            winners_text = []
            for level, member in sorted(self.winners, key=lambda x: x[0], reverse=True):
                winners_text.append(f"Level {level}: {member.mention}")
            embed.add_field(
                name="Previous Winners",
                value="\n".join(winners_text),
                inline=False
            )
        
        embed.timestamp = datetime.now()
        
        # Send new round message
        self.current_round_message = await self.thread.send(embed=embed, view=view)
        await self.update_status_message()

    async def update_status_message(self):
        """Update or create the status message showing current votes."""
        embed = discord.Embed(
            title="Current Votes",
            description=f"Level {self.current_level} Voting Status",
            color=0x5865F2
        )
        
        # Add vote counts
        vote_status = []
        for candidate in self.members:
            votes = self.vote_counts.get(candidate, 0)
            voters = [v.mention for v, c in self.votes.items() if c == candidate]
            vote_status.append(
                f"{candidate.mention}: {votes} votes\n"
                f"└ Voters: {', '.join(voters) if voters else 'None'}"
            )
        
        embed.add_field(
            name="Vote Counts",
            value="\n".join(vote_status) or "No votes yet",
            inline=False
        )
        
        # Check for winner
        votes_needed = int(len(self.members) * VOTE_PERCENTAGE_REQUIRED)
        for candidate, votes in self.vote_counts.items():
            if votes >= votes_needed:
                embed.add_field(
                    name="🏆 Winner!",
                    value=f"{candidate.mention} has won Level {self.current_level}!",
                    inline=False
                )
                await self.start_new_round(winner=candidate)
                return
        
        # Update or send status message
        try:
            if self.status_message:
                await self.status_message.edit(embed=embed)
            else:
                self.status_message = await self.thread.send(embed=embed)
        except discord.HTTPException:
            pass

    async def show_final_results(self):
        """Display the final results and archive the thread."""
        embed = discord.Embed(
            title="🏆 Final Results",
            description="Here are the final fractal group assignments:",
            color=0x00FF00
        )
        
        # Sort winners by level (highest first)
        sorted_winners = sorted(self.winners, key=lambda x: x[0], reverse=True)
        
        for level, winner in sorted_winners:
            embed.add_field(
                name=f"Level {level}",
                value=winner.mention,
                inline=False
            )
            
        await self.thread.send(embed=embed)
        
        # Archive the thread
        await self.thread.edit(archived=True, locked=True)

    def add_member(self, member: discord.Member) -> None:
        """Add a member to the fractal group."""
        if member not in self.members:
            self.members.append(member)

    def remove_member(self, member: discord.Member) -> None:
        """Remove a member from the fractal group."""
        if member in self.members:
            self.members.remove(member)

    def add_spectator(self, member: discord.Member) -> None:
        """Add a spectator to the fractal group."""
        if member not in self.spectators:
            self.spectators.append(member)

    def remove_spectator(self, member: discord.Member) -> None:
        """Remove a spectator from the fractal group."""
        if member in self.spectators:
            self.spectators.remove(member)

    def add_external_voter(self, member: discord.Member) -> None:
        """Add an external voter to the fractal group."""
        if member not in self.external_voters:
            self.external_voters.append(member)

    def remove_external_voter(self, member: discord.Member) -> None:
        """Remove an external voter from the fractal group."""
        if member in self.external_voters:
            self.external_voters.remove(member)

    def is_full(self) -> bool:
        """Check if the fractal group has reached maximum capacity."""
        from ...config.config import MAX_GROUP_SIZE
        return len(self.members) >= MAX_GROUP_SIZE
