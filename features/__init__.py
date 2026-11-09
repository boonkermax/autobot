from . import (start_help, login, join_requests, scanner, locks, warns, moderation, antispam, rules,
               welcome, blacklist, notes, autoreply, chat_settings, report, autoban, owner, pipeline)

MODULES = [start_help, login, join_requests, scanner, locks, warns, moderation, antispam, rules,
           welcome, blacklist, notes, autoreply, chat_settings, report, autoban, owner, pipeline]


def register_all(app):
    for mod in MODULES:
        mod.register(app)
