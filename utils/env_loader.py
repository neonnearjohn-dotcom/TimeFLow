from pathlib import Path
from dotenv import load_dotenv


def load_env() -> None:
    """Load .env file safely removing BOM/CRLF."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        env_path.write_text(content, encoding="utf-8")
        load_dotenv(env_path)
    else:
        load_dotenv()
