# Setup
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # fill BOT_TOKEN, API_ID/API_HASH (my.telegram.org), OWNER_ID, ENC_KEY
python main.py

# Structure
main.py            entry point
config.py          env + constants
database.py        sqlite helpers
utils.py           admin checks, target parsing, shared decorators
services/          userbot.py (Telethon), saved.py (notes/filters storage)
features/          one file per feature; each exposes register(app)
  start_help  login  join_requests  scanner  locks  warns  moderation  antispam
  rules  welcome  blacklist  notes  autoreply  chat_settings  report  autoban  owner
  pipeline    runs check() of locks/blacklist/slowmode/antispam, then report/notes/autoreply

# Add a new feature
Create features/myfeature.py with register(app), then add it to the list in features/__init__.py.

# Flow
1. Add bot as admin (invite users, ban, delete, pin) in group/channel.
2. DM bot: /login → /accept <chat_id>   (registers that session for auto-scan)
3. Every SCAN_INTERVAL_MIN the bot approves pending requests and posts scan stats in each chat.
