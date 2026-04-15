#!/usr/bin/env python
"""Backend startup with proper module handling"""
import sys
import os
from pathlib import Path

# Get the Backend directory
BACKEND_DIR = Path(__file__).parent / "Backend"

# Add Backend to Python path
sys.path.insert(0, str(BACKEND_DIR))

# Now import and run
if __name__ == "__main__":
    print("🔍 Checking dependencies...")
    try:
        import fastapi
        print(f"✓ FastAPI {fastapi.__version__}")
    except ImportError as e:
        print(f"✗ FastAPI not installed: {e}")
        sys.exit(1)
    
    print("\n🚀 Starting Persona Automation API Backend...")
    print("=" * 60)
    
    try:
        # Import from Backend package structure
        from src.api.routes import app
        print("✓ API routes loaded successfully")
        
        import uvicorn
        
        print("\n📊 Server Configuration:")
        print(f"   Host: 0.0.0.0")
        print(f"   Port: 5000")
        print(f"   URL: http://localhost:5000")
        print(f"   Docs: http://localhost:5000/docs")
        print("=" * 60)
        print()
        
        # Run the server
        uvicorn.run(app, host="0.0.0.0", port=5000, reload=False, log_level="info")
        
    except Exception as e:
        print(f"\n❌ Error starting backend: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
