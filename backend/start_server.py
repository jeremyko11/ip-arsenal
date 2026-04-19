# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r"C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend")
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/ip_arsenal"
import uvicorn
from main import app
uvicorn.run(app, host="0.0.0.0", port=8766, log_level="warning")
