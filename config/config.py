import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
if not BOT_TOKEN:
    raise ValueError(
        "No Discord token found. Please add your token to the .env file.\n"
        "Example: DISCORD_TOKEN=your_token_here"
    )

COMMAND_PREFIX = '!'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# Discord Intents Configuration
INTENTS = {
    'message_content': True,
    'members': True,
    'voice_states': True,
    'guilds': True,
    'guild_messages': True
}

# Logging Configuration
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Fractal Group Settings
MAX_GROUP_SIZE = 6
MIN_GROUP_SIZE = 2
DEFAULT_LEVEL = 6
VOTE_PERCENTAGE_REQUIRED = 0.51  # 51% required for a vote to pass
THREAD_CLEANUP_INTERVAL = 300  # Check for inactive threads every 5 minutes
THREAD_INACTIVE_THRESHOLD = 3600  # Archive threads after 1 hour of inactivity

# Voice Channel Settings
VOICE_TIMEOUT = 300  # 5 minutes timeout for voice activity
VOICE_ACTIVITY_CHECK_INTERVAL = 60  # Check voice activity every minute

# Timer Settings
TIMER_MAX_DURATION = 3600  # Maximum timer duration in seconds (1 hour)
TIMER_CHECK_INTERVAL = 1  # Check timers every second

# ZAO Settings
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', '3HPGRn6bvILV-WjQhagIky4E5I4vsLDW')
ENS_RESOLVER_ADDRESS = '0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41'  # ENS Public Resolver
ZAO_ROLE_ID = int(os.getenv('ZAO_ROLE_ID', '0'))  # Replace with actual role ID
ZAO_CHANNEL_ID = int(os.getenv('ZAO_CHANNEL_ID', '0'))  # Replace with actual channel ID

# Data Storage
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Cache Settings
CACHE_TIMEOUT = 300  # 5 minutes cache timeout
MAX_CACHE_SIZE = 1000  # Maximum number of items in cache

# Rate Limiting
RATE_LIMIT_COMMANDS = 5  # Commands per user per minute
RATE_LIMIT_WINDOW = 60  # Window size in seconds for rate limiting

# Error Messages
ERROR_MESSAGES = {
    'not_in_voice': 'You must be in a voice channel to use this command.',
    'no_permission': 'You do not have permission to use this command.',
    'invalid_duration': 'Invalid duration. Please specify a duration between 1 second and 1 hour.',
    'group_full': 'This fractal group is already full.',
    'already_in_group': 'You are already in another fractal group.',
    'ens_resolution_failed': 'Failed to resolve ENS name. Please check the name and try again.',
}

# Success Messages
SUCCESS_MESSAGES = {
    'timer_started': 'Timer started! I will notify you when it\'s done.',
    'group_created': 'Fractal group created successfully!',
    'commands_synced': 'Commands synced successfully!',
    'ens_resolved': 'ENS name resolved successfully!',
    'respect_given': 'Respect given successfully!',
    'zao_joined': 'Successfully joined ZAO!',
    'zao_left': 'Successfully left ZAO.',
}

# Help Messages
HELP_MESSAGES = {
    'fractal': 'Create a new fractal group from members in your voice channel.',
    'timer': 'Set a timer for a specified duration.',
    'sync': 'Manually sync bot commands (admin only).',
    'ens': 'Resolve an ENS name to its Ethereum address.',
    'respect': 'Give respect to another user.',
    'summary': 'Get a summary of recent channel activity.',
    'voicestats': 'Show voice channel statistics.',
    'zaojoin': 'Join ZAO and get the role.',
}

# Embed Colors
COLORS = {
    'success': 0x00FF00,  # Green
    'error': 0xFF0000,    # Red
    'info': 0x5865F2,     # Discord Blurple
    'warning': 0xFFA500,  # Orange
}

# Thread cleanup settings
THREAD_CLEANUP_INTERVAL = 3600  # Check every hour
THREAD_INACTIVE_THRESHOLD = 86400  # Archive threads inactive for 24 hours
