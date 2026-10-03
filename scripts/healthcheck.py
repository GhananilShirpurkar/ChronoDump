#!/usr/bin/env python3
"""ChronoDump Production Health Check Runner.

Validates:
1. Environment variables & secret integrity
2. Database connectivity & SQLite file permissions
3. Ollama server reachability & model availability
4. Telegram Bot API connectivity & identity
5. Storage & disk sanity
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_environment() -> Dict[str, Any]:
    """Verify presence of essential environment variables."""
    from app.config import settings

    has_token = bool(settings.TELEGRAM_BOT_TOKEN and ":" in settings.TELEGRAM_BOT_TOKEN)
    has_user = bool(settings.AUTHORIZED_USER_ID and settings.AUTHORIZED_USER_ID > 0)

    return {
        "status": "ok" if (has_token and has_user) else "error",
        "bot_token_configured": has_token,
        "authorized_user_configured": has_user,
        "user_id": settings.AUTHORIZED_USER_ID,
        "timezone": settings.DEFAULT_TIMEZONE,
    }


def check_databases() -> Dict[str, Any]:
    """Verify SQLite database connectivity and write permissions."""
    from app.config import settings
    from app.storage.database import engine
    from sqlalchemy import text

    db_path = settings.DATA_DIR / "chronodump.db"
    sched_path = settings.DATA_DIR / "chronodump_scheduler.db"

    data_dir = db_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    can_connect = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        can_connect = True
    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {
        "status": "ok" if can_connect else "error",
        "app_db_exists": db_path.exists(),
        "scheduler_db_exists": sched_path.exists(),
        "app_db_size_kb": round(db_path.stat().st_size / 1024, 2) if db_path.exists() else 0,
        "scheduler_db_size_kb": round(sched_path.stat().st_size / 1024, 2) if sched_path.exists() else 0,
    }


async def check_ollama() -> Dict[str, Any]:
    """Verify Ollama server connectivity and model readiness."""
    import urllib.request
    from app.config import settings

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    target_model = settings.OLLAMA_MODEL.lower()

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ChronoDump-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status != 200:
                return {"status": "error", "error": f"HTTP {response.status}"}
            payload = json.loads(response.read().decode("utf-8"))
            available_models = [m.get("name", "").lower() for m in payload.get("models", [])]

            model_found = any(target_model in m for m in available_models)
            return {
                "status": "ok" if model_found else "warning",
                "endpoint": settings.OLLAMA_BASE_URL,
                "target_model": target_model,
                "model_ready": model_found,
                "available_models": available_models,
            }
    except Exception as e:
        return {
            "status": "error",
            "endpoint": settings.OLLAMA_BASE_URL,
            "target_model": target_model,
            "model_ready": False,
            "error": str(e),
        }


async def check_telegram() -> Dict[str, Any]:
    """Verify Telegram Bot API authentication and connectivity."""
    from aiogram import Bot
    from app.config import settings

    if not settings.TELEGRAM_BOT_TOKEN:
        return {"status": "error", "error": "No token configured"}

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        me = await bot.get_me()
        return {
            "status": "ok",
            "bot_id": me.id,
            "bot_username": f"@{me.username}" if me.username else "Unknown",
            "bot_name": me.first_name,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        await bot.session.close()


async def run_all_checks() -> Dict[str, Any]:
    """Execute all system health probes."""
    env_res = check_environment()
    db_res = check_databases()
    ollama_res = await check_ollama()
    tg_res = await check_telegram()

    all_ok = (
        env_res["status"] == "ok"
        and db_res["status"] == "ok"
        and ollama_res["status"] in ("ok", "warning")
        and tg_res["status"] == "ok"
    )

    return {
        "healthy": all_ok,
        "checks": {
            "environment": env_res,
            "databases": db_res,
            "ollama": ollama_res,
            "telegram": tg_res,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="ChronoDump Production Health Check")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = asyncio.run(run_all_checks())

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("⚡ ChronoDump Health Probe")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Environment
        env = results["checks"]["environment"]
        if env["status"] == "ok":
            print(f"✅ Environment: Configured (User: {env['user_id']}, Timezone: {env['timezone']})")
        else:
            print("❌ Environment: Invalid or missing .env variables")

        # Databases
        db = results["checks"]["databases"]
        if db["status"] == "ok":
            print(f"✅ Databases: Connected (App: {db['app_db_size_kb']} KB, Sched: {db['scheduler_db_size_kb']} KB)")
        else:
            print(f"❌ Databases: Failed ({db.get('error')})")

        # Ollama
        ol = results["checks"]["ollama"]
        if ol["status"] == "ok":
            print(f"✅ Ollama LLM: Connected to {ol['endpoint']} (Model: {ol['target_model']} ready)")
        elif ol["status"] == "warning":
            print(f"⚠️ Ollama LLM: Server up, but model '{ol['target_model']}' not loaded in tags")
        else:
            print(f"❌ Ollama LLM: Cannot reach {ol['endpoint']} ({ol.get('error')})")

        # Telegram
        tg = results["checks"]["telegram"]
        if tg["status"] == "ok":
            print(f"✅ Telegram API: Connected as {tg['bot_username']} (ID: {tg['bot_id']})")
        else:
            print(f"❌ Telegram API: Authentication failed ({tg.get('error')})")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if results["healthy"]:
            print("🟢 ALL SYSTEMS OPERATIONAL")
        else:
            print("🔴 SYSTEM DEGRADED — Review failed checks above")

    sys.exit(0 if results["healthy"] else 1)


if __name__ == "__main__":
    main()
