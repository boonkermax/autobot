#!/usr/bin/env bash
set -e
cd /opt/autobot
git pull --ff-only
./venv/bin/pip install -q -r requirements.txt
systemctl restart autobot
systemctl --no-pager status autobot | head -n 5
