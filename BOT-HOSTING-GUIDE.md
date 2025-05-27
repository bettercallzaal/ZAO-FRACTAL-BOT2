# Deploying Fractal Bot to Bot-Hosting.net

This guide will walk you through the process of deploying your Fractal Bot to Bot-Hosting.net for 24/7 uptime.

## Step 1: Prepare Your Bot Files

Your bot is already well-structured with the following key files:
- `main.py` - The entry point for your bot
- `zao_commands.py` - Contains the ENS resolution and ZAO token commands
- `zao_addresses.py` - Contains known Ethereum addresses and ENS names
- `requirements.txt` - Lists all dependencies

## Step 2: Create a Bot-Hosting.net Account

1. Go to [Bot-Hosting.net](https://bot-hosting.net/) and create an account
2. Verify your email address
3. Log in to your account dashboard

## Step 3: Create a New Bot Project

1. Click on "Create Bot" or similar option in the dashboard
2. Choose a name for your bot project (e.g., "FractalBot")
3. Select Python as the language
4. Choose the appropriate plan based on your needs (start with the free tier to test)

## Step 4: Upload Your Bot Files

Bot-Hosting.net typically offers several ways to upload your bot:

### Option A: Direct Upload
1. Use the file upload interface in the dashboard
2. Upload all your bot files, maintaining the directory structure

### Option B: GitHub Integration (if available)
1. Connect your GitHub account
2. Select your Fractal Bot repository
3. Configure the deployment settings

## Step 5: Configure Environment Variables

1. Look for "Environment Variables" or "Config Vars" in the dashboard
2. Add the following variables:
   - `DISCORD_TOKEN` = Your Discord bot token
   - `ALCHEMY_API_KEY` = Your Alchemy API key (3HPGRn6bvILV-WjQhagIky4E5I4vsLDW)
   - Any other environment variables your bot uses

## Step 6: Start Your Bot

1. Look for "Start" or "Deploy" button in the dashboard
2. The platform should automatically install dependencies from your requirements.txt
3. Monitor the logs to ensure your bot starts correctly

## Step 7: Verify Bot is Running

1. Check your Discord server to see if the bot comes online
2. Test the `/zao` command with an ENS name to verify functionality
3. Monitor the bot logs for any errors

## Troubleshooting

If your bot doesn't start properly:

1. Check the logs for error messages
2. Verify all environment variables are set correctly
3. Ensure your main.py file is in the root directory
4. Confirm all dependencies are listed in requirements.txt

## Maintaining Your Bot

1. **Updates**: When you want to update your bot, you'll need to either:
   - Upload new files through the dashboard
   - Push to GitHub if using GitHub integration

2. **Monitoring**: Regularly check the bot's status and logs

3. **Backup**: Keep a local backup of your bot code and any data files

## Future MongoDB Integration

For the planned MongoDB integration (to be implemented later):

1. You'll need to sign up for MongoDB Atlas (free tier available)
2. Create a cluster and database
3. Add the MongoDB connection string as an environment variable
4. Update your bot code to use MongoDB for data storage

## Notes

- Bot-Hosting.net may have resource limitations on free plans
- Consider upgrading to a paid plan if you need more resources
- Keep your Discord token and API keys secure and never share them
