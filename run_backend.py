#!/usr/bin/env python
"""Simple backend runner with error handling"""
import sys
import os

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try importing dependencies
print("🔍 Checking dependencies...")
try:
    import fastapi
    print(f"✓ FastAPI {fastapi.__version__}")
except ImportError as e:
    print(f"✗ FastAPI import failed: {e}")
    sys.exit(1)

try:
    from pathlib import Path
    print("✓ pathlib")
except ImportError as e:
    print(f"✗ pathlib: {e}")
    sys.exit(1)

# Suppress any startup warnings
import warnings
warnings.filterwarnings("ignore")

# Now import and run the app
print("\n🚀 Starting Persona Automation API...")
print("=" * 50)

try:
    from frontend.api.app import app
    print("✓ App imported successfully")

    import uvicorn
    print("📊 Running on http://0.0.0.0:5000")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False, log_level="info")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
