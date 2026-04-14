#!/usr/bin/env python
"""Persona Automation Backend - Entry Point"""
import sys
import os
import warnings
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))

warnings.filterwarnings("ignore")

print("🔍 Checking dependencies...")
try:
    import fastapi
    print(f"✓ FastAPI {fastapi.__version__}")
except ImportError as e:
    print(f"✗ FastAPI import failed: {e}")
    sys.exit(1)

print("\n🚀 Starting Persona Automation API...")
print("=" * 50)

try:
    # Import app from Backend API structure
    from api.routes import app
    print("✓ App imported from api.routes (Backend)")

    import uvicorn
    print("📊 Running on http://0.0.0.0:5000")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False, log_level="info")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

