import logging

from flask import Flask, Response, request
from slack_bolt import App as SlackApp
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Config
from models.database import init_db
from web.routes import bp as web_bp
from scheduler.setup import create_scheduler
from scheduler.jobs import sync_all_data
from slack_bot.handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_flask_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(web_bp)
    return app


def create_slack_app() -> SlackApp:
    app = SlackApp(token=Config.SLACK_BOT_TOKEN)
    register_handlers(app)
    return app


# --- Module-level setup (runs when gunicorn imports app:flask_app) ---

# 1. Init database
logger.info("Initializing database...")
init_db()

# 2. Run initial data sync
logger.info("Running initial data sync...")
try:
    sync_all_data()
except Exception as e:
    logger.warning(f"Initial sync failed (will retry on schedule): {e}")

# 3. Start scheduler
logger.info("Starting scheduler...")
scheduler = create_scheduler()
scheduler.start()

# 4. Start Slack Socket Mode in a background thread
logger.info("Starting Slack Socket Mode...")
slack_app = create_slack_app()
socket_handler = SocketModeHandler(slack_app, Config.SLACK_APP_TOKEN)
socket_handler.connect()
logger.info("Slack Socket Mode connected")

# 5. Create Flask app
flask_app = create_flask_app()


@flask_app.before_request
def require_auth():
    if not Config.DASHBOARD_USER:
        return  # skip auth when not configured (local dev)
    auth = request.authorization
    if not auth or auth.username != Config.DASHBOARD_USER or auth.password != Config.DASHBOARD_PASS:
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})


if __name__ == "__main__":
    logger.info(f"Starting Flask on port {Config.FLASK_PORT}...")
    try:
        flask_app.run(host="0.0.0.0", port=Config.FLASK_PORT, debug=False)
    finally:
        scheduler.shutdown()
