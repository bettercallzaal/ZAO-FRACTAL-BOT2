import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from discord.ext import commands
from discord import Interaction, Member, User, Guild

from config.config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT

class BotLogger:
    """Enhanced logging utility for the Discord bot.
    
    This class provides structured logging with different output formats for
    console and file, error tracking, and Discord-specific logging methods.
    """
    
    def __init__(self, name: str = "FractalBot"):
        """Initialize the logger with console and file handlers.
        
        Args:
            name: Name of the logger, defaults to 'FractalBot'
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOG_LEVEL)
        
        # Ensure logs directory exists
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # File handlers
        self._setup_file_handlers(log_dir)
        
        # Console handler with colored output
        self._setup_console_handler()
        
    def _setup_file_handlers(self, log_dir: Path) -> None:
        """Set up file handlers for general logs and errors.
        
        Args:
            log_dir: Directory to store log files
        """
        # General logs
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_bot.log"
        file_handler = logging.FileHandler(filename=log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        self.logger.addHandler(file_handler)
        
        # Error logs with full tracebacks
        error_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_errors.log"
        error_handler = logging.FileHandler(filename=error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            f"{LOG_FORMAT}\nTraceback: %(exc_info)s",
            LOG_DATE_FORMAT
        ))
        self.logger.addHandler(error_handler)
        
    def _setup_console_handler(self) -> None:
        """Set up console handler with colored output."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '\033[92m[%(asctime)s]\033[0m \033[94m%(levelname)s\033[0m: %(message)s',
            '%H:%M:%S'
        ))
        self.logger.addHandler(console_handler)
        
    def _format_user(self, user: Union[Member, User]) -> str:
        """Format user information for logging.
        
        Args:
            user: Discord user or member
            
        Returns:
            Formatted string with user info
        """
        return f"{user} (ID: {user.id})"
        
    def _format_guild(self, guild: Optional[Guild]) -> str:
        """Format guild information for logging.
        
        Args:
            guild: Discord guild or None for DMs
            
        Returns:
            Formatted string with guild info
        """
        return f"in {guild.name} (ID: {guild.id})" if guild else "in DMs"
    
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message.
        
        Args:
            message: Debug message to log
            **kwargs: Additional logging arguments
        """
        self.logger.debug(message, **kwargs)
        
    def info(self, message: str, **kwargs) -> None:
        """Log an info message.
        
        Args:
            message: Info message to log
            **kwargs: Additional logging arguments
        """
        self.logger.info(message, **kwargs)
        
    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message.
        
        Args:
            message: Warning message to log
            **kwargs: Additional logging arguments
        """
        self.logger.warning(message, **kwargs)
        
    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs) -> None:
        """Log an error message with optional exception info.
        
        Args:
            message: Error message to log
            exc_info: Optional exception for traceback
            **kwargs: Additional logging arguments
        """
        if exc_info:
            tb = ''.join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            message = f"{message}\n{tb}"
        self.logger.error(message, **kwargs)
        
    def command(self, ctx: Union[commands.Context, Interaction], command_name: str, status: str = "executed") -> None:
        """Log command usage.
        
        Args:
            ctx: Command context or interaction
            command_name: Name of the command
            status: Command execution status
        """
        user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        guild = ctx.guild
        
        self.logger.info(
            f"Command '{command_name}' {status} by {self._format_user(user)} {self._format_guild(guild)}"
        )
        
    def startup(self, bot: commands.Bot) -> None:
        """Log bot startup information.
        
        Args:
            bot: The Discord bot instance
        """
        self.logger.info("=== Bot Starting Up ===")
        self.logger.info(f"Bot: {self._format_user(bot.user)}")
        self.logger.info(f"Discord.py Version: {discord.__version__}")
        self.logger.info(f"Python Version: {sys.version}")
        self.logger.info(f"Connected to {len(bot.guilds)} guilds")
        self.logger.info("=== Startup Complete ===")
        
    def guild_count(self, bot: commands.Bot) -> None:
        """Log current guild count.
        
        Args:
            bot: The Discord bot instance
        """
        self.logger.info(f"Currently in {len(bot.guilds)} guilds")
        
    def voice_event(self, member: Member, channel: str, event_type: str) -> None:
        """Log voice channel events.
        
        Args:
            member: Member involved in the event
            channel: Name of the voice channel
            event_type: Type of voice event (join/leave/move)
        """
        self.logger.info(
            f"Voice {event_type}: {self._format_user(member)} in channel '{channel}' {self._format_guild(member.guild)}"
        )
        
    def fractal_event(self, group_id: int, event_type: str, details: str) -> None:
        """Log fractal group events.
        
        Args:
            group_id: ID of the fractal group
            event_type: Type of event (create/vote/complete)
            details: Additional event details
        """
        self.logger.info(f"Fractal {event_type} [Group {group_id}]: {details}")
        
    def api_request(self, service: str, endpoint: str, status: str, details: Optional[str] = None) -> None:
        """Log external API requests.
        
        Args:
            service: Name of the service (e.g., 'Alchemy', 'ENS')
            endpoint: API endpoint called
            status: Request status (success/error)
            details: Optional request details
        """
        message = f"{service} API Request to {endpoint}: {status}"
        if details:
            message += f" - {details}"
        self.logger.info(message)
