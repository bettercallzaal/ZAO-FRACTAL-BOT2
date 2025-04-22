import discord
from datetime import datetime

# Color constants
SUCCESS_COLOR = 0x57F287  # Green
WARNING_COLOR = 0xFEE75C  # Yellow
ERROR_COLOR = 0xED4245    # Red
INFO_COLOR = 0x5865F2     # Blue

def create_timer_embed(member_name, remaining_seconds, total_seconds=180):
    """
    Create an embed for the timer display.
    
    Args:
        member_name (str): The name of the member who is sharing
        remaining_seconds (int): Remaining time in seconds
        total_seconds (int): Total time in seconds (default: 180 seconds = 3 minutes)
    
    Returns:
        discord.Embed: The formatted embed
    """
    # Calculate minutes and seconds
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    
    # Calculate progress percentage
    progress_percent = (remaining_seconds / total_seconds) * 100
    
    # Determine color based on remaining time
    if progress_percent > 66:
        color = SUCCESS_COLOR
    elif progress_percent > 33:
        color = WARNING_COLOR
    else:
        color = ERROR_COLOR
    
    # Create embed
    embed = discord.Embed(
        title=f"Timer for {member_name}",
        description=f"Time remaining: **{minutes:02d}:{seconds:02d}**",
        color=color,
        timestamp=datetime.now()
    )
    
    # Create progress bar
    progress_bar_length = 20
    filled_length = int(progress_bar_length * (progress_percent / 100))
    bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
    
    embed.add_field(name="Progress", value=f"`{bar}` {progress_percent:.1f}%", inline=False)
    
    # Add footer
    embed.set_footer(text="ZAO Fractal Bot | Timer")
    
    return embed

def create_fractal_group_embed(group_name, facilitator, members, created_at):
    """
    Create an embed for displaying fractal group information.
    
    Args:
        group_name (str): The name of the fractal group
        facilitator (discord.Member): The facilitator of the group
        members (list): List of members in the group
        created_at (datetime): When the group was created
    
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title=f"Fractal Group: {group_name}",
        description=f"Facilitator: {facilitator.mention}",
        color=INFO_COLOR,
        timestamp=datetime.now()
    )
    
    # Add members field
    members_text = "\n".join([f"• {member.mention}" for member in members])
    if not members_text:
        members_text = "No members yet"
    
    embed.add_field(name=f"Members ({len(members)}/6)", value=members_text, inline=False)
    
    # Add creation time
    embed.set_footer(text=f"Created at {created_at.strftime('%Y-%m-%d %H:%M:%S')} | ZAO Fractal Bot")
    
    return embed

def create_respect_vote_embed(voter, candidates):
    """
    Create an embed for the respect voting process.
    
    Args:
        voter (discord.Member): The member who is voting
        candidates (list): List of members who can be voted for
    
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title="Respect Game Voting",
        description=f"It's {voter.mention}'s turn to vote!\nSelect a member who made impactful contributions.",
        color=INFO_COLOR,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Candidates", value="\n".join([f"• {candidate.mention}" for candidate in candidates]), inline=False)
    embed.set_footer(text="ZAO Fractal Bot | Respect Game")
    
    return embed

def create_respect_results_embed(results):
    """
    Create an embed for displaying respect voting results.
    
    Args:
        results (dict): Dictionary mapping members to their vote counts
    
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title="Respect Game Results",
        description="Here are the results of the Respect Game voting:",
        color=SUCCESS_COLOR,
        timestamp=datetime.now()
    )
    
    # Sort results by vote count (descending)
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    
    # Add results field
    results_text = "\n".join([f"• {member.mention}: **{votes}** votes" for member, votes in sorted_results])
    embed.add_field(name="Votes Received", value=results_text, inline=False)
    
    embed.set_footer(text="ZAO Fractal Bot | Respect Game Results")
    
    return embed

def create_summary_embed(channel_name, summary_text):
    """
    Create an embed for displaying discussion summaries.
    
    Args:
        channel_name (str): The name of the channel/thread being summarized
        summary_text (str): The generated summary text
    
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title=f"Summary of {channel_name}",
        description=summary_text,
        color=INFO_COLOR,
        timestamp=datetime.now()
    )
    
    embed.set_footer(text="ZAO Fractal Bot | AI Summary")
    
    return embed

def create_error_embed(error_message):
    """
    Create an embed for displaying errors.
    
    Args:
        error_message (str): The error message to display
    
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title="Error",
        description=error_message,
        color=ERROR_COLOR,
        timestamp=datetime.now()
    )
    
    embed.set_footer(text="ZAO Fractal Bot | Error")
    
    return embed
