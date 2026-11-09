import logging

from telegram import Update
from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
import database  # noqa: F401  (creates tables)
from features import register_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")


async def on_error(u, c):
    log.error("update error", exc_info=c.error)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register_all(app)
    app.add_error_handler(on_error)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
