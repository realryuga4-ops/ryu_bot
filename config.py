"""Configuration file for the Discord Bot.

Handles environment variables, constants, and bot settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Main configuration class for the bot."""
    
    # Discord Settings
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    BOT_PREFIX: str = os.getenv("BOT_PREFIX", "b!")
    BOT_VERSION: str = os.getenv("BOT_VERSION", "1.0.0")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION: bool = ENVIRONMENT == "production"
    
    # Bot Status Settings
    BOT_STATUSES = [
        "🎴 Anime Cards",
        "!help for commands",
        "Drop system active",
        "Made with discord.py",
    ]
    
    # Rarity Colors (Discord embeds)
    RARITY_COLORS = {
        "common": 0x95A5A6,
        "rare": 0x3498DB,
        "epic": 0x9B59B6,
        "legendary": 0xF39C12,
    }
    
    # Drop System Settings
    DROP_COOLDOWN_MINUTES: int = 10
    DROP_CLAIM_TIMEOUT: int = 10

    # Economy Settings
    STARTING_BALANCE: int = 1000
    DAILY_REWARD: int = 500
    DAILY_COOLDOWN_HOURS: int = 24
    
    @staticmethod
    def validate() -> bool:
        """Validate critical configuration values."""
        if not Config.DISCORD_TOKEN:
            print("❌ ERROR: DISCORD_TOKEN not set in .env file")
            return False
        return True


config = Config()
