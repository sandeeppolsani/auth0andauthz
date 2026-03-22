#!/bin/bash
set -a && source .env && set +a
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 3002 --reload
