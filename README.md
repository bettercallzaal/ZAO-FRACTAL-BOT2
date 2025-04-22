# ZAO Fractal Bot

A Discord bot designed to facilitate and enhance the ZAO Fractals governance model. The bot provides tools for managing fractal group meetings, timing member sharing sessions, conducting the Respect Game voting, and summarizing discussions.

## Features

### Timer Functionality
- `/timer` - Start a 3-minute countdown timer for member sharing sessions
- Visual progress bar with color-coded time indicators
- Pause/Resume and Reset controls
- Automated warnings at key time intervals

### Fractal Group Management
- `/fractalgroup` - Create a new fractal group with an associated thread
- Automatic thread creation for each fractal group
- Member management with a cap of 6 members per group
- `/listgroups` - View all active fractal groups in a channel

### Respect Game Voting
- `/respectvote` - Initiate the Respect Game voting process in a fractal group
- Sequential voting for each member with prevention of self-voting
- `/respectresults` - Display the results of the voting

### Discussion Summarization
- `/summarize` - Generate an AI-powered summary of the discussion in a thread
- Option to export the summary as a text file

### Command Management
- `/sync` - Manually sync commands with Discord (admin only)

## Setup Instructions

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/zao-fractal-bot.git
   cd zao-fractal-bot
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Add your Discord bot token to the `.env` file
   ```
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

4. **Run the bot**
   ```
   python main.py
   ```

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and add a bot
3. Enable the following Privileged Gateway Intents:
   - Message Content Intent
   - Server Members Intent
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
zao-fractal-bot/
├── main.py                 # Bot initialization and event handling
├── timer_commands.py       # Timer functionality
├── fractal_commands.py     # Fractal group management
├── respect_commands.py     # Respect Game voting
├── summary_commands.py     # Discussion summarization
├── utils/                  # Utility functions and helpers
│   ├── embed_builder.py    # Functions for creating embeds
│   └── error_handler.py    # Error handling utilities
├── .env                    # Environment variables (create from .env.example)
├── requirements.txt        # Project dependencies
└── README.md               # Documentation
```

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
