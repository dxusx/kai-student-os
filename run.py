import asyncio
import logging
import sys

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from api.app import app as fastapi_app
from bot.handlers.base import base_router
from bot.handlers.schedule import schedule_router
from bot.handlers.tasks import tasks_router
from core.config import settings
from database.connection import init_db
from scheduler.jobs import NotificationScheduler
from services.tunnel import TunnelService

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("kai_assistant")


async def main() -> None:
    logger.info("Initializing KAI Student Assistant & Mobile PWA...")
    logger.info("Academic group: %s, Subgroup: %s", settings.kai_group, settings.kai_subgroup)

    # 1. Initialize SQLite database and models
    logger.info("Initializing database: %s", settings.database_url)
    await init_db()
    logger.info("Database tables verified/created successfully.")

    # 2. Configure Uvicorn server
    uvicorn_config = uvicorn.Config(
        app=fastapi_app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)
    logger.info("FastAPI Web Server configured on http://%s:%d", settings.web_host, settings.web_port)

    # 3. Start Cloudflare Quick Tunnel if enabled
    tunnel: TunnelService | None = None
    tunnel_url: str | None = None
    if settings.enable_tunnel:
        tunnel = TunnelService(port=settings.web_port)
        tunnel_url = await tunnel.start()
        if tunnel_url:
            msg = (
                "\n" + "=" * 74 + "\n"
                "🌐 ПУБЛИЧНЫЙ HTTPS-АДРЕС ДЛЯ СМАРТФОНА И PWA:\n"
                f"👉 {tunnel_url}\n"
                + "=" * 74 + "\n"
            )
            try:
                print(msg, flush=True)
            except Exception:
                print(f"\n[PUBLIC HTTPS PWA URL]: {tunnel_url}\n", flush=True)
            logger.info("Public HTTPS PWA URL: %s", tunnel_url)
        else:
            logger.warning("Could not establish public tunnel. Falling back to local network.")


    # 4. Check Telegram Bot Token
    token = settings.bot_token.strip() if settings.bot_token else ""
    if not token:
        logger.warning(
            "⚠️ BOT_TOKEN is empty in .env! Telegram bot polling will be skipped.\n"
            "FastAPI Web Server & Mobile PWA are launching now at http://localhost:%d",
            settings.web_port
        )
        try:
            await server.serve()
        finally:
            if tunnel:
                await tunnel.stop()
        return

    # 5. Create Bot and Dispatcher instances
    session = None
    if settings.tg_api_base_url:
        from aiogram.client.telegram import TelegramAPIServer
        from aiogram.client.session.aiohttp import AiohttpSession
        import socket
        from aiohttp import TCPConnector

        logger.info("Using custom Telegram API reverse proxy: %s", settings.tg_api_base_url)
        api_server = TelegramAPIServer.from_base(settings.tg_api_base_url)
        session = AiohttpSession(api=api_server)
        session._connector_init["family"] = socket.AF_INET

    bot = Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 6. Register routers
    dp.include_router(base_router)
    dp.include_router(schedule_router)
    dp.include_router(tasks_router)

    # 7. Start background proactive scheduler
    scheduler = NotificationScheduler(bot=bot)
    scheduler.start()

    logger.info("Starting Telegram bot polling for group %s...", settings.kai_group)
    logger.info("Web App & PWA accessible at: http://localhost:%d and http://%s:%d", settings.web_port, settings.web_host, settings.web_port)

    # Optionally notify student in Telegram with public URL
    if tunnel_url and settings.tg_user_id:
        try:
            await bot.send_message(
                chat_id=settings.tg_user_id,
                text=(
                    "🌐 <b>Мобильное веб-приложение (PWA) запущено:</b>\n\n"
                    f"🔗 <b><a href='{tunnel_url}'>{tunnel_url}</a></b>\n\n"
                    "📱 <i>Откройте в браузере Chrome на смартфоне и нажмите «Добавить на главный экран»!</i>"
                ),
                parse_mode="HTML"
            )
            logger.info("Sent public PWA URL to Telegram user %s", settings.tg_user_id)
        except Exception as e:
            logger.warning("Could not notify Telegram user with tunnel URL: %s", e)

    # 8. Concurrently run FastAPI Uvicorn Server and Telegram Bot Polling
    server_task = asyncio.create_task(server.serve())
    bot_task = None
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        bot_task = asyncio.create_task(dp.start_polling(bot))

        # Wait until either one finishes or is interrupted
        done, pending = await asyncio.wait(
            [server_task, bot_task],
            return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        logger.info("Shutting down KAI Assistant services...")
        server.should_exit = True
        scheduler.stop()
        if tunnel:
            await tunnel.stop()

        if bot_task and not bot_task.done():
            bot_task.cancel()
        if not server_task.done():
            server_task.cancel()

        await bot.session.close()
        logger.info("Bot session, scheduler, tunnel, and web server stopped cleanly.")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("KAI Student Assistant stopped.")

