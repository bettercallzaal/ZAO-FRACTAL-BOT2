# ZAO Fractal Bot

A Discord bot designed to facilitate and enhance the ZAO Fractals governance model. The bot provides tools for managing fractal group meetings, timing member sharing sessions, conducting the Respect Game voting, and summarizing discussions.

## Features

### Fractal Group Management
- `/fractalgroup` - Create a new fractal group with an associated thread
- Automatic thread creation for each fractal group
- Member management with a cap of 6 members per group
- Voting system for group decisions

### Timer Functionality
- `/timer <duration> [message]` - Set a timer for a specified duration (max 1 hour)
- `/timers` - List your active timers
- `/canceltimer <timer_id>` - Cancel a specific timer

### ENS Resolution
- `/ens <name> [details]` - Resolve an ENS name to its Ethereum address using the ENS Public Resolver contract
- `/address <address>` - Look up ENS names owned by an Ethereum address
- Supports additional details like avatar, description, social links
- Uses Alchemy API for all Ethereum interactions for improved reliability

### Respect System
- `/respect <user> [reason]` - Give respect to another user
- `/respectrank` - Show respect rankings for the server
- 24-hour cooldown per user

### Voice Activity Tracking
- `/voicestats [user]` - Show voice channel statistics
- `/voicetop` - Show top voice channel users
- Automatic tracking of time spent in voice channels

### Channel Summary
- `/summary [hours] [channel]` - Get a summary of recent channel activity
- Activity timeline visualization
- Most active users statistics

### ZAO Management
- `/zaojoin` - Join ZAO and get the role
- `/zaoleave` - Leave ZAO
- `/zaostats` - Show ZAO member statistics
- `/zaomembers [active_only]` - List all ZAO members

### Command Management
- `/sync` - Manually sync commands with Discord (bot owner only)

## Setup Instructions

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/fractalbot3.git
   cd fractalbot3
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Add your Discord bot token and Alchemy API key to the `.env` file
   ```
   cp .env.example .env
   # Edit .env and add your Discord bot token and Alchemy API key
   ```

4. **Run the bot**
   ```
   python main.py
   ```

## Environment Variables

Create a `.env` file with the following variables:

```
# Required
DISCORD_TOKEN=your_discord_bot_token
ALCHEMY_API_KEY=your_alchemy_api_key

# Optional
LOG_LEVEL=INFO
COMMAND_PREFIX=!
OWNER_ID=your_discord_id
```

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and add a bot
3. Enable the following Privileged Gateway Intents:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
4. Use the OAuth2 URL Generator to create an invite link with the following scopes:
   - `bot`
   - `applications.commands`
5. Add the required bot permissions:
   - Read Messages/View Channels
   - Send Messages
   - Create Public Threads
   - Send Messages in Threads
   - Manage Threads
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Use Slash Commands

## Project Structure

```
fractalbot3/
├── main.py                 # Bot initialization and event handling
├── cogs/                   # Bot commands organized into cogs
│   ├── base.py            # Base cog with common utilities
│   ├── ens/               # ENS name resolution
│   │   ├── cog.py         # ENS commands and functionality
│   │   └── __init__.py
│   ├── fractal/           # Fractal group management
│   │   ├── cog.py         # Fractal commands
│   │   ├── group.py       # Fractal group class
│   │   ├── views.py       # UI components
│   │   └── __init__.py
│   ├── respect/           # Respect system
│   │   ├── cog.py         # Respect commands
│   │   └── __init__.py
│   ├── summary/           # Channel summarization
│   │   ├── cog.py         # Summary commands
│   │   └── __init__.py
│   ├── timer/             # Timer functionality
│   │   ├── cog.py         # Timer commands
│   │   └── __init__.py
│   ├── voice/             # Voice activity tracking
│   │   ├── cog.py         # Voice commands
│   │   └── __init__.py
│   └── zao/               # ZAO management
│       ├── cog.py         # ZAO commands
│       └── __init__.py
├── config/                # Configuration
│   └── config.py          # Bot settings and constants
├── utils/                 # Utility functions
│   └── logger.py          # Logging functionality
├── data/                  # Data storage
├── .env                   # Environment variables
├── requirements.txt       # Project dependencies
└── README.md             # Documentation
```

## Deployment

This bot can be deployed on:
1. A VPS or dedicated server
2. Heroku (using the included Procfile)
3. Docker (using the included Dockerfile and docker-compose.yml)

For detailed deployment instructions, see [BOT-HOSTING-GUIDE.md](BOT-HOSTING-GUIDE.md).

## ZAO Fractals Core Principles

- **Empowerment**: Every participant contributes to the governance process
- **Transparency**: All decisions are made openly in weekly fractal meetings
- **Sustainability**: Contributions are rewarded with $ZAO Respect tokens
- **Equitable Distribution**: Resources and decision-making power are distributed across smaller groups

## Weekly Meeting Structure

- 6:00 - 6:15 PM: Opening Announcements & Chit Chat
- 6:15 - 6:20 PM: ZAO Fractal Presentation
- 6:20 - 7:15 PM: ZAO Fractal Groups (with timer for member sharing)
- 7:15 - 7:30 PM: Extra Time & Closing Chit Chat

## License

[MIT License](LICENSE)

## Future Features

The following features are planned for future releases:

### Performance and Scalability
- Implement proper automatic sharding for large-scale deployments
- Add connection pooling for database operations
- Optimize memory usage with lazy loading and smarter caching
- Distributed hosting capability across multiple servers

### Code Structure Improvements
- Rename all cog files to include module name (e.g., `fractal_cog.py` instead of just `cog.py`)
- Implement comprehensive command error handling
- Add rate limiting to all commands
- Use ephemeral responses for all administrative commands

### Documentation Enhancements
- Installation diagrams and visual guides
- Dedicated COMMANDS.md with examples and screenshots
- CONTRIBUTING.md with code style guides
- Security documentation for API key handling

### User Experience Improvements
- Command autocompletion for parameters
- Interactive help command with UI components
- Command examples in help text
- Customizable command prefixes per server

### ENS & Ethereum Integration
- Enhanced ENS record caching to reduce API calls
- Full ENS reverse resolution for all address displays
- ENS avatar integration in user profiles
- Multi-provider fallback for blockchain connections

### New Features
- Command analytics dashboard for admins
- Scheduled events for recurring fractal group meetings
- Localization support for multiple languages
- Bot status website with uptime monitoring
- Voice channel integration for fractal meetings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Code Structure Guidelines

When contributing to this project, please follow these naming conventions:

- Cog files should be named with their module name, e.g., `fractal_cog.py` instead of just `cog.py`
- Follow PEP 8 style guidelines for Python code
- Include docstrings for all classes and functions
- Add type hints where appropriate
