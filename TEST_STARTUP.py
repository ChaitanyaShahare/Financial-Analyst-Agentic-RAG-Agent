#!/usr/bin/env python3
"""
Quick startup test to verify all components can initialize.

Run this to test if the server can start:
    python TEST_STARTUP.py
"""

import sys
from pathlib import Path
import os

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

print("\n" + "="*80)
print("✅ TEST: Server Startup Verification")
print("="*80)

# Test 1: Load environment
print("\n1️⃣  Testing environment variable loading...")
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=str(env_path), override=True)

openai_key = os.getenv("OPENAI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

print(f"   OPENAI_API_KEY: {'✅ Loaded' if openai_key else '❌ Missing'}")
print(f"   TAVILY_API_KEY: {'✅ Loaded' if tavily_key else '❌ Missing'}")

# Test 2: Database verification
print("\n2️⃣  Testing database connection...")
from Src import db_queries
if db_queries.verify_database():
    print("   ✅ Database verified")
else:
    print("   ❌ Database verification failed")
    sys.exit(1)

# Test 3: Agent initialization
print("\n3️⃣  Testing agent initialization...")
try:
    from Src import agent
    agent.initialize_agent_components()
    print("   ✅ Agent components initialized")
except Exception as e:
    print(f"   ❌ Agent initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: FastAPI app load
print("\n4️⃣  Testing FastAPI app load...")
try:
    import app as app_module
    print("   ✅ FastAPI app loaded")
except Exception as e:
    print(f"   ❌ FastAPI app loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL TESTS PASSED - Server is ready to start!")
print("="*80)
print("\nTo start the server, run:")
print("   python app.py")
print("\nOr:")
print("   uvicorn app:app --reload --host 0.0.0.0 --port 8000")
print()
