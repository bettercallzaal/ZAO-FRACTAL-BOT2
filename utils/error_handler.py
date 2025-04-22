import discord
import traceback
import sys
from .embed_builder import create_error_embed

async def handle_command_error(interaction, error):
    """
    Handle errors that occur during command execution.
    
    Args:
        interaction (discord.Interaction): The interaction that caused the error
        error (Exception): The error that occurred
    """
    # Check if the interaction has been responded to
    if interaction.response.is_done():
        # If already responded, send a follow-up message
        try:
            await interaction.followup.send(
                embed=create_error_embed(f"An error occurred: {str(error)}"),
                ephemeral=True
            )
        except discord.errors.HTTPException:
            # If we can't send a followup (e.g., interaction expired)
            pass
    else:
        # If not responded yet, respond with the error
        try:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(error)}"),
                ephemeral=True
            )
        except discord.errors.HTTPException:
            # If we can't respond (e.g., interaction expired)
            pass
    
    # Log the error to console
    print(f"Error in command {interaction.command.name}:", file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

def log_error(error, context=None):
    """
    Log an error to the console.
    
    Args:
        error (Exception): The error that occurred
        context (str, optional): Additional context about where the error occurred
    """
    if context:
        print(f"Error in {context}:", file=sys.stderr)
    else:
        print("Error:", file=sys.stderr)
    
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
