import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


def load_config(path: str = "config.yaml") -> dict:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    config["telegram"]["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    config["telegram"]["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID", "")
    return config
