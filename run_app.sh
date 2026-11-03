#!/usr/bin/env bash
# Khởi chạy Chương trình Desktop Seminar Meet
cd "$(dirname "$0")" || exit 1

if [ -f ".venv/bin/python3" ]; then
    .venv/bin/python3 run_app.py "$@"
else
    python3 run_app.py "$@"
fi
