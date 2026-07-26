"""LifeOps backend package."""
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load backend/.env (and project-root .env as a fallback) before any module
    # reads os.getenv. Without this the x402 payTo/OKX credentials stay empty and
    # the gateway falls back to the zero address, breaking the verified run.
    _BACKEND_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(_BACKEND_DIR / ".env")
    load_dotenv(_BACKEND_DIR.parent / ".env")
except ImportError:
    # python-dotenv is optional; real env vars still work without it.
    pass

__version__ = "1.0.0"
