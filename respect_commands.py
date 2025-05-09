import discord
from discord import app_commands
from discord.ext import commands
import datetime

from utils.embed_builder import create_respect_vote_embed, create_respect_results_embed, create_error_embed
from utils.error_handler import handle_command_error

# Dictionary to store active voting sessions
# Key: thread_id, Value: RespectVote object
active_votes = {}

class RespectVote:
    """Class for managing the Respect Game voting process."""
    
    def __init__(self, thread, members, leader=None):
        self.thread = thread
        self.original_members = members.copy()  # Keep a copy of all original members
        self.members = members.copy()  # List of members in the fractal group (will change each round)
        self.votes = {member: 0 for member in members}  # Initialize vote counts to 0
        self.voter_choices = {}  # Track who voted for whom (for non-anonymous voting)
        self.message = None  # Message containing the voting UI
        self.status_message = None  # Message showing current vote status in chat
        self.total_members = len(members)
        self.threshold = self.total_members / 2  # 50% threshold
        self.current_round = 1
        self.round_winners = []  # List of winners in order
        self.candidate_indices = {}  # Store original indices of candidates
        self.leader = leader  # Group leader who can force completion
    
    def record_vote(self, voter, candidate):
        """Record a vote from a voter to a candidate."""
        # Check if voter is in original members and candidate is in current members
        if voter in self.original_members and candidate in self.members:
            # Check if voter has already voted
            if voter in self.voter_choices:
                # Remove previous vote
                previous_candidate = self.voter_choices[voter]
                if previous_candidate in self.votes:  # Make sure the candidate is still in votes
                    self.votes[previous_candidate] -= 1
            
            # Record new vote
            self.votes[candidate] += 1
            self.voter_choices[voter] = candidate
            return True
        return False
    
    def check_threshold_reached(self):
        """Check if any candidate has reached the 50% threshold."""
        for member, votes in self.votes.items():
            if votes >= self.threshold:
                return member
        return None
    
    def is_round_complete(self):
        """Check if the current voting round is complete."""
        # Round is complete if everyone from the original members has voted or someone reached the threshold
        # We use the original_members count to determine if everyone has voted
        return len(self.voter_choices) >= len(self.original_members) or self.check_threshold_reached() is not None
    
    def start_new_round(self):
        """Start a new voting round."""
        # Record the winner of the previous round
        winner = self.get_round_winner()
        if winner:
            self.round_winners.append(winner)
            # Remove the winner from the members list for the next round
            if winner in self.members:
                self.members.remove(winner)
        
        # If we have no more members to vote on, return current round
        if len(self.members) < 2:
            return self.current_round
        
        # Reset for next round
        self.current_round += 1
        self.votes = {member: 0 for member in self.members}  # Reset votes with remaining members
        self.voter_choices = {}  # Reset voter choices
        
        # The threshold is based on the number of original members
        # This ensures we need the same number of votes regardless of how many candidates remain
        self.total_members = len(self.original_members)  # Keep using original member count
        self.threshold = self.total_members / 2  # Update threshold based on original members
        
        return self.current_round
    
    def get_round_winner(self):
        """Get the winner of the current round."""
        threshold_winner = self.check_threshold_reached()
        if threshold_winner:
            return threshold_winner
        
        # If no threshold winner, get the member with the most votes
        if self.votes:
            return max(self.votes.items(), key=lambda x: x[1])[0]
        return None
    
    def get_results(self):
        """Get the voting results."""
        return self.votes
    
    def get_all_results(self):
        """Get all round winners."""
        return self.round_winners

# This class is no longer needed with the emoji reaction voting system
# Keeping it as a placeholder for backward compatibility
class CandidateSelect(discord.ui.Select):
    """Dropdown select for choosing a candidate to vote for (legacy - replaced by emoji reactions)."""
    
    def __init__(self, respect_vote):
        # Create options for each member
        options = []
        for i, member in enumerate(respect_vote.members):
            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {member.display_name}",
                    value=str(member.id),
                    description=f"Vote for {member.display_name}"
                )
            )
        
        # Create the select menu
        super().__init__(
            placeholder="Voting now uses emoji reactions instead",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"respect_vote_select_{respect_vote.thread.id}",
            disabled=True  # Disable the dropdown since we're using reactions now
        )
        
        self.respect_vote = respect_vote
    
    async def callback(self, interaction: discord.Interaction):
        """Handle selection (legacy - no longer used)."""
        await interaction.response.send_message(
            "Please use emoji reactions to vote instead of this dropdown.",
            ephemeral=True
        )

class ContinueVoteView(discord.ui.View):
    """View for continuing to the next round of voting."""
    
    def __init__(self, respect_vote):
        super().__init__(timeout=None)  # No timeout
        self.respect_vote = respect_vote
    
    @discord.ui.button(label="Continue to Next Round", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Continue to the next round of voting."""
        # Start a new round
        new_round = self.respect_vote.start_new_round()
        
        # Create the embed for the new round
        embed = discord.Embed(
            title=f"Round {new_round} Voting - LIVE RESULTS",
            description="Click a button below to vote. Results update in real-time. You can change your vote at any time!",
            color=0x5865F2,
            timestamp=datetime.datetime.now()  # Add timestamp to show when last updated
        )
        
        # Add candidates field with numbers
        candidates_text = "\n".join([f"• {candidate.mention}" for candidate in self.respect_vote.members])
        embed.add_field(name="Candidates", value=candidates_text, inline=False)
        
        # Add voting instructions
        embed.add_field(
            name="Instructions", 
            value="• Click a button below to vote for that member\n"
                  "• You can change your vote at any time by clicking a different button\n"
                  "• Results will appear at the bottom of the chat\n"
                  "• The round ends when everyone votes or someone gets 50% of votes", 
            inline=False
        )
        
        # Create a new view with buttons for voting
        view = RespectVoteView(self.respect_vote)
        
        # Update the message
        await interaction.response.edit_message(embed=embed, view=view)
        
        # Store the updated message
        self.respect_vote.message = await interaction.original_response()
        
        # Reset the status message for the new round
        self.respect_vote.status_message = None
        
        # Announce the new round
        announcement = await self.respect_vote.thread.send(
            f"🗳️ **Round {new_round} voting has started!** Click a button to vote."
        )
        
        # Create an initial status embed
        status_embed = await view.create_status_embed()
        
        # Send the initial status message
        self.respect_vote.status_message = await self.respect_vote.thread.send(
            "Current voting status (updates in real-time):",
            embed=status_embed
        )
    
    @discord.ui.button(label="End Voting", style=discord.ButtonStyle.danger)
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """End the voting process."""
        await interaction.response.defer()
        await self.show_final_results()
    
    async def show_final_results(self):
        """Show the final results of all rounds."""
        # Delete previous status message if it exists
        if self.respect_vote.status_message:
            try:
                await self.respect_vote.status_message.delete()
            except:
                pass  # Ignore errors if message was already deleted
        
        # Get all winners
        winners = self.respect_vote.round_winners
        
        # If we have members left who haven't been ranked, add them in arbitrary order
        remaining_members = [m for m in self.respect_vote.original_members if m not in winners]
        winners.extend(remaining_members)
        
        final_embed = discord.Embed(
            title="Final Respect Game Results",
            description="The Respect Game voting has concluded. Here are the final rankings:",
            color=0x57F287,
            timestamp=datetime.datetime.now()
        )
        
        # Add final rankings with Fibonacci-based points (doubled)
        rankings_text = ""
        points_text = ""
        
        # Define the Fibonacci-like point values (doubled from standard)
        fibonacci_points = [110, 68, 42, 26, 16, 10]  # 55, 34, 21, 13, 8, 5 doubled
        
        for i, winner in enumerate(winners):
            # Add medal emoji for top 3
            if i == 0:
                rankings_text += f"🥇 1st Place: {winner.mention}\n"
                points = fibonacci_points[0] if i < len(fibonacci_points) else 0
                points_text += f"🥇 {winner.mention}: **{points} Respect Points**\n"
            elif i == 1:
                rankings_text += f"🥈 2nd Place: {winner.mention}\n"
                points = fibonacci_points[1] if i < len(fibonacci_points) else 0
                points_text += f"🥈 {winner.mention}: **{points} Respect Points**\n"
            elif i == 2:
                rankings_text += f"🥉 3rd Place: {winner.mention}\n"
                points = fibonacci_points[2] if i < len(fibonacci_points) else 0
                points_text += f"🥉 {winner.mention}: **{points} Respect Points**\n"
            else:
                rankings_text += f"{i+1}. {winner.mention}\n"
                points = fibonacci_points[i] if i < len(fibonacci_points) else 0
                points_text += f"{i+1}. {winner.mention}: **{points} Respect Points**\n"
        
        if rankings_text:
            final_embed.add_field(name="Final Rankings", value=rankings_text, inline=False)
            final_embed.add_field(name="Respect Points Earned", value=points_text, inline=False)
        else:
            final_embed.add_field(name="Results", value="No rounds were completed.", inline=False)
        
        # Add a thank you message
        final_embed.set_footer(text="Thanks for participating in the Respect Game!")
        
        # Send the final results
        await self.respect_vote.thread.send(
            "🏆 **FINAL RESULTS** 🏆",
            embed=final_embed
        )
        
        # Update the original message to show voting has ended
        if self.respect_vote.message:
            try:
                await self.respect_vote.message.edit(embed=final_embed, view=None)
            except:
                pass  # If we can't edit the message, just continue
        
        # Clean up
        if self.respect_vote.thread.id in active_votes:
            del active_votes[self.respect_vote.thread.id]

class VoteButton(discord.ui.Button):
    """Button for voting for a specific candidate."""
    
    def __init__(self, candidate, respect_vote, index, row=0):
        # Get the candidate's name, truncate if too long
        name = candidate.display_name
        if len(name) > 10:
            name = name[:8] + "..."
        
        # Create the button with the candidate's number and name
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{index+1}. {name}",
            row=row
        )
        self.candidate = candidate
        self.respect_vote = respect_vote
        self.index = index
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Get the user who clicked
        user = interaction.user
        
        # Check if the user is in the original members list
        if user not in self.respect_vote.original_members:
            await interaction.response.send_message(
                "You are not part of this Respect Game.",
                ephemeral=True
            )
            return
        
        # Get the view
        view = self.view
        
        # Check if the user has already voted
        changing_vote = user in self.respect_vote.voter_choices
        previous_vote = self.respect_vote.voter_choices.get(user)
        
        # Record the vote
        self.respect_vote.record_vote(user, self.candidate)
        
        try:
            # Acknowledge the vote
            if changing_vote and previous_vote != self.candidate:
                await interaction.response.send_message(
                    f"You changed your vote from {previous_vote.mention} to {self.candidate.mention}!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"You voted for {self.candidate.mention}!",
                    ephemeral=True
                )
                
            # Update the vote display immediately
            await view.update_vote_display()
            
            # Create a status embed for the chat
            status_embed = await view.create_status_embed()
            
            # Delete previous status message if it exists
            if self.respect_vote.status_message:
                try:
                    await self.respect_vote.status_message.delete()
                except:
                    pass  # Ignore errors if message was already deleted
            
            # Announce the vote change to the thread (non-ephemeral)
            if changing_vote and previous_vote != self.candidate:
                announcement = f"📊 **Vote Changed**: {interaction.user.mention} changed their vote from {previous_vote.mention} to {self.candidate.mention}!"
            else:
                announcement = f"📊 **New Vote**: {interaction.user.mention} voted for {self.candidate.mention}!"
            
            # Send new status message with the current votes
            self.respect_vote.status_message = await self.respect_vote.thread.send(
                announcement,
                embed=status_embed
            )
            
            # Check if the round is complete
            if self.respect_vote.is_round_complete():
                await view.complete_round()
        except Exception as e:
            # If we can't respond, just continue
            print(f"Error in vote button callback: {e}")
            pass


class LeaderCompleteButton(discord.ui.Button):
    """Button for the leader to force completion of the round with current votes."""
    
    def __init__(self, respect_vote):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Leader: Complete Round",
            row=4  # Place at the bottom
        )
        self.respect_vote = respect_vote
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        # Check if the user is the leader
        if interaction.user != self.respect_vote.leader:
            await interaction.response.send_message(
                "Only the designated leader can force completion of the round.",
                ephemeral=True
            )
            return
        
        # Check if there are any votes
        if not self.respect_vote.voter_choices:
            await interaction.response.send_message(
                "Cannot complete the round - no votes have been cast yet.",
                ephemeral=True
            )
            return
        
        # Acknowledge the action
        await interaction.response.send_message(
            "Completing the round with current votes...",
            ephemeral=True
        )
        
        # Get the view
        view = self.view
        
        # Announce that the leader is forcing completion
        await self.respect_vote.thread.send(
            f"🔔 **Round Completion**: {interaction.user.mention} as the leader has decided to complete this round with the current votes."
        )
        
        # Complete the round
        await view.complete_round()


class RespectVoteView(discord.ui.View):
    """View for the Respect Game voting UI."""
    
    def __init__(self, respect_vote):
        super().__init__(timeout=None)  # No timeout for this view
        self.respect_vote = respect_vote
        
        # Create buttons for each candidate
        for i, candidate in enumerate(respect_vote.members):
            # Store the original index for this candidate
            respect_vote.candidate_indices[candidate] = i + 1
            
            # Create a button for this candidate
            # Add the button to the view
            self.add_item(VoteButton(candidate, respect_vote, i, row=i//3))
        
        # Add a leader force completion button if there's a leader
        if respect_vote.leader:
            self.add_item(LeaderCompleteButton(respect_vote))
    
    async def create_status_embed(self):
        """Create an embed for the current vote status to display in chat."""
        # Create a status embed
        embed = discord.Embed(
            title=f"Round {self.respect_vote.current_round} Voting Status",
            description=f"**{len(self.respect_vote.voter_choices)}/{self.respect_vote.total_members}** members have voted.",
            color=0x57F287,  # Green color for status messages
            timestamp=datetime.datetime.now()
        )
        
        # Use the stored candidate indices if available
        candidate_indices = getattr(self.respect_vote, 'candidate_indices', {})
        if not candidate_indices:
            # Create indices if not available
            for i, candidate in enumerate(self.respect_vote.members):
                candidate_indices[candidate] = i + 1
        
        # Sort candidates by vote count (highest first)
        sorted_candidates = sorted(
            self.respect_vote.members,
            key=lambda x: self.respect_vote.votes[x],
            reverse=True
        )
        
        # Add candidates with their current vote counts
        candidates_text = ""
        for candidate in sorted_candidates:
            votes = self.respect_vote.votes[candidate]
            percentage = 0
            if len(self.respect_vote.voter_choices) > 0:
                percentage = (votes / len(self.respect_vote.voter_choices)) * 100
            
            # Add visual indicator for vote count
            bar = '█' * int(percentage / 10) if percentage > 0 else ''
            
            # Use the original index for display
            original_index = candidate_indices.get(candidate, 0)
            if original_index > 0:  # Only show if we have a valid index
                candidates_text += f"{original_index}. {candidate.mention}: **{votes}** vote{'s' if votes != 1 else ''} ({percentage:.1f}%) {bar}\n"
        
        embed.add_field(name="Current Votes", value=candidates_text or "No votes yet", inline=False)
        
        # Add footer with instructions
        embed.set_footer(text="Click a button in the voting message above to vote or change your vote")
        
        return embed
    
    async def update_vote_display(self):
        """Update the vote count display."""
        # Create an updated embed
        embed = discord.Embed(
            title=f"Round {self.respect_vote.current_round} Voting - LIVE RESULTS",
            description=f"**{len(self.respect_vote.voter_choices)}/{self.respect_vote.total_members}** members have voted. Results update in real-time.",
            color=0x5865F2,
            timestamp=datetime.datetime.now()  # Add timestamp to show when last updated
        )
        
        # Add candidates with their current vote counts and numbers
        candidates_text = ""
        
        # Use the stored candidate indices if available
        candidate_indices = getattr(self.respect_vote, 'candidate_indices', {})
        if not candidate_indices:
            # Create indices if not available
            for i, candidate in enumerate(self.respect_vote.members):
                candidate_indices[candidate] = i + 1
        
        # Sort candidates by vote count (highest first)
        sorted_candidates = sorted(
            self.respect_vote.members,
            key=lambda x: self.respect_vote.votes[x],
            reverse=True
        )
        
        for candidate in sorted_candidates:
            votes = self.respect_vote.votes[candidate]
            percentage = 0
            if len(self.respect_vote.voter_choices) > 0:
                percentage = (votes / len(self.respect_vote.voter_choices)) * 100
            
            # Add visual indicator for vote count
            bar = '█' * int(percentage / 10) if percentage > 0 else ''
            
            # Use the original index for display
            original_index = candidate_indices.get(candidate, 0)
            if original_index > 0:  # Only show if we have a valid index
                candidates_text += f"{original_index}. {candidate.mention}: **{votes}** vote{'s' if votes != 1 else ''} ({percentage:.1f}%) {bar}\n"
        
        embed.add_field(name="📊 Live Vote Count", value=candidates_text, inline=False)
        
        # Show who voted for whom (non-anonymous)
        votes_by_member = ""
        for voter, candidate in self.respect_vote.voter_choices.items():
            # Use the original index for display
            original_index = candidate_indices.get(candidate, 0)
            if original_index > 0 and candidate in self.respect_vote.members:  # Only show if valid and still in members
                votes_by_member += f"{voter.mention} → {original_index}. {candidate.mention}\n"
        
        if votes_by_member:
            embed.add_field(name="👥 Current Votes", value=votes_by_member, inline=False)
        
        # Add who hasn't voted yet - from original members
        not_voted = [member for member in self.respect_vote.original_members if member not in self.respect_vote.voter_choices.keys()]
        if not_voted:
            not_voted_text = ", ".join([member.mention for member in not_voted])
            embed.add_field(name="⏳ Waiting for Votes From", value=not_voted_text, inline=False)
        
        # Check if threshold reached
        threshold_member = self.respect_vote.check_threshold_reached()
        if threshold_member:
            embed.add_field(
                name="🎉 Threshold Reached!",
                value=f"{threshold_member.mention} has reached the 50% threshold!",
                inline=False
            )
        
        # Add footer with instructions
        embed.set_footer(text="Click a number button below to vote or change your vote")
        
        # Update the message
        await self.respect_vote.message.edit(embed=embed)
    
    async def complete_round(self):
        """Complete the current voting round."""
        # Get the winner
        winner = self.respect_vote.get_round_winner()
        
        # Delete previous status message if it exists
        if self.respect_vote.status_message:
            try:
                await self.respect_vote.status_message.delete()
            except:
                pass  # Ignore errors if message was already deleted
        
        # Create results embed
        results_embed = discord.Embed(
            title=f"Round {self.respect_vote.current_round} Results",
            description=f"Winner: {winner.mention}",
            color=0x57F287
        )
        
        # Add voting details
        votes_text = "\n".join([f"{member.mention}: **{votes}** vote{'s' if votes != 1 else ''}" 
                           for member, votes in sorted(self.respect_vote.votes.items(), key=lambda x: x[1], reverse=True)])
        results_embed.add_field(name="Final Votes", value=votes_text, inline=False)
        
        # Add current rankings
        if self.respect_vote.round_winners:
            rankings = "\n".join([f"{i+1}. {winner.mention}" for i, winner in enumerate(self.respect_vote.round_winners)])
            results_embed.add_field(name="Current Rankings", value=rankings, inline=False)
        
        # Send results
        await self.respect_vote.thread.send(
            f"🎉 **Round {self.respect_vote.current_round} Complete!** {winner.mention} wins this round!",
            embed=results_embed
        )
        
        # Check if we have enough members for another round
        remaining_members = len(self.respect_vote.members) - 1  # Subtract the current winner
        
        if remaining_members >= 2:
            # Ask if they want to continue
            continue_embed = discord.Embed(
                title=f"Continue to Round {self.respect_vote.current_round + 1}?",
                description=f"Would you like to continue to the next round of voting? {remaining_members} members remain.",
                color=0x5865F2
            )
            
            continue_view = ContinueVoteView(self.respect_vote)
            continue_message = await self.respect_vote.thread.send(embed=continue_embed, view=continue_view)
            self.respect_vote.message = continue_message
            self.respect_vote.status_message = None  # Reset status message for next round
        else:
            # No more members to vote on, show final results
            # Add the last winner if there's only one member left
            if remaining_members == 1:
                last_member = [m for m in self.respect_vote.members if m != winner][0]
                self.respect_vote.round_winners.append(last_member)
            
            await self.show_final_results()

class RespectCog(commands.Cog):
    """Cog for respect game-related commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="respectvote", description="Start the Respect Game voting process with clickable buttons")
    @app_commands.describe(leader="Designate a leader who can force completion of the round")
    async def respect_vote(self, interaction: discord.Interaction, leader: discord.Member = None):
        """Start a Respect Game vote in the current thread."""
        try:
            # Check if we're in a thread
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.response.send_message("This command can only be used in a thread.", ephemeral=True)
                return
            
            # Check if there's already an active vote in this thread
            if interaction.channel.id in active_votes:
                await interaction.response.send_message("There's already an active vote in this thread.", ephemeral=True)
                return
            
            # Get the members in the thread
            thread = interaction.channel
            members = []
            
            # Fetch thread members
            async for member in thread.fetch_members():
                user = await interaction.guild.fetch_member(member.id)
                if not user.bot:  # Exclude bots
                    members.append(user)
            
            # Check if we have enough members
            if len(members) < 2:
                await interaction.response.send_message("Need at least 2 members in the thread to start a vote.", ephemeral=True)
                return
            
            # Check if the leader is in the thread
            if leader and leader not in members:
                await interaction.response.send_message(f"{leader.mention} is not in this thread and cannot be designated as leader.", ephemeral=True)
                return
            
            # Create a new RespectVote instance with optional leader
            vote = RespectVote(thread, members, leader)
            
            # Store the vote in the active_votes dictionary
            active_votes[thread.id] = vote
            
            # Create the embed for the vote
            embed = discord.Embed(
                title=f"Round {vote.current_round} Voting - LIVE RESULTS",
                description="Click a button below to vote. Results update in real-time. You can change your vote at any time!",
                color=0x5865F2,
                timestamp=datetime.datetime.now()  # Add timestamp to show when last updated
            )
            
            # Add candidates field with numbers
            candidates_text = "\n".join([f"• {candidate.mention}" for candidate in vote.members])
            embed.add_field(name="Candidates", value=candidates_text, inline=False)
            
            # Add leader information if applicable
            if leader:
                embed.add_field(
                    name="Group Leader", 
                    value=f"{leader.mention} has been designated as the leader and can force completion of the round.",
                    inline=False
                )
            
            # Add voting instructions
            embed.add_field(
                name="Instructions", 
                value="• Click a button below to vote for that member\n"
                      "• You can change your vote at any time by clicking a different button\n"
                      "• Voting is public - everyone can see who you voted for\n"
                      "• Results will appear at the bottom of the chat\n"
                      "• The round ends when everyone votes or someone gets 50% of votes", 
                inline=False
            )
            
            # Create the view with voting buttons
            view = RespectVoteView(vote)
            
            # Send the message with the view
            await interaction.response.send_message("Starting Respect Game vote...")
            vote.message = await thread.send(embed=embed, view=view)
            
            # Create an initial status embed
            status_embed = await view.create_status_embed()
            
            # Send the initial status message
            vote.status_message = await thread.send(
                "Current voting status (updates in real-time):",
                embed=status_embed
            )
            
        except Exception as e:
            print(f"Error in respect_vote command: {e}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="respectresults", description="Show the results of the Respect Game voting")
    async def respect_results(self, interaction: discord.Interaction):
        """Show the results of the Respect Game voting."""
        try:
            thread_id = interaction.channel.id
            
            # Check if there's an active vote in this thread
            if thread_id in active_votes:
                respect_vote = active_votes[thread_id]
                
                # Get current round results
                results = respect_vote.get_results()
                
                # Create embed for current round
                results_embed = discord.Embed(
                    title=f"Round {respect_vote.current_round} Current Results",
                    description=f"Voting is in progress. {len(respect_vote.voter_choices)}/{respect_vote.total_members} members have voted.",
                    color=0x5865F2
                )
                
                # Add voting details
                votes_text = "\n".join([f"{member.mention}: **{votes}** vote{'s' if votes != 1 else ''}" for member, votes in sorted(results.items(), key=lambda x: x[1], reverse=True)])
                results_embed.add_field(name="Current Votes", value=votes_text or "No votes yet", inline=False)
                
                # Show who voted for whom (non-anonymous)
                votes_by_member = ""
                for voter, candidate in respect_vote.voter_choices.items():
                    votes_by_member += f"{voter.mention} → {candidate.mention}\n"
                
                if votes_by_member:
                    results_embed.add_field(name="Votes Cast", value=votes_by_member, inline=False)
                
                # Add previous round winners if any
                winners = respect_vote.get_all_results()
                if winners:
                    winners_text = "\n".join([f"Round {i+1}: {winner.mention}" for i, winner in enumerate(winners)])
                    results_embed.add_field(name="Previous Round Winners", value=winners_text, inline=False)
                
                await interaction.response.send_message(embed=results_embed)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("There's no active voting session in this thread."),
                    ephemeral=True
                )
        
        except Exception as e:
            await handle_command_error(interaction, e)

async def setup(bot):
    """Add the respect cog to the bot."""
    await bot.add_cog(RespectCog(bot))
