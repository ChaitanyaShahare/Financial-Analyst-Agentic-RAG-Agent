#!/usr/bin/env python3
"""
Debug script to verify environment setup and paths.

Run this to diagnose configuration issues:
    python DEBUG_ENVIRONMENT.py
"""

import os
import sys
from pathlib import Path

print("\n" + "="*80)
print("🔍 ENVIRONMENT DIAGNOSTIC REPORT")
print("="*80)

# 1. Python Info
print("\n1️⃣  PYTHON INFO:")
print(f"   Python Version: {sys.version}")
print(f"   Python Executable: {sys.executable}")
print(f"   Python Path: {sys.prefix}")

# 2. Current Working Directory
print("\n2️⃣  WORKING DIRECTORY:")
cwd = Path.cwd()
print(f"   Current: {cwd}")
print(f"   Is absolute: {cwd.is_absolute()}")

# 3. Project Structure
print("\n3️⃣  PROJECT STRUCTURE:")
project_root = Path(__file__).parent
print(f"   Script location: {Path(__file__)}")
print(f"   Project root: {project_root}")

# Check required folders
required_folders = [
    "Src",
    "vectordb",
    "data",
    "frontend",
    "frontend/static"
]

for folder in required_folders:
    path = project_root / folder
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {folder}: {path}")

# 4. Database Check
print("\n4️⃣  DATABASE CHECK:")
db_path = project_root / "data" / "meridian_wealth.db"  # Fixed: meridian (not meridain)
print(f"   Expected path: {db_path}")
print(f"   Exists: {'✅ YES' if db_path.exists() else '❌ NO'}")
print(f"   Absolute path: {db_path.resolve()}")

if db_path.exists():
    size_mb = db_path.stat().st_size / (1024*1024)
    print(f"   File size: {size_mb:.2f} MB")
    
    # Try to verify database
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        print(f"   Tables found: {[t[0] for t in tables]}")
    except Exception as e:
        print(f"   ❌ Error reading database: {e}")
else:
    print("   ⚠️  Database file not found!")

# 5. Environment Variables
print("\n5️⃣  ENVIRONMENT VARIABLES:")

# Check .env file
env_file = project_root / ".env"
print(f"   .env file exists: {'✅ YES' if env_file.exists() else '❌ NO'}")

if env_file.exists():
    print(f"   .env location: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key = line.split('=')[0]
                print(f"   ✅ {key} defined in .env")

# Check environment for loaded keys
print("\n   Environment variables:")
openai_key = os.getenv("OPENAI_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")
print(f"   OPENAI_API_KEY: {'✅ SET' if openai_key else '❌ NOT SET'}")
print(f"   TAVILY_API_KEY: {'✅ SET' if tavily_key else '❌ NOT SET'}")

if openai_key:
    print(f"      Length: {len(openai_key)} characters")
    print(f"      First 10 chars: {openai_key[:10]}...")
if tavily_key:
    print(f"      Length: {len(tavily_key)} characters")
    print(f"      First 10 chars: {tavily_key[:10]}...")

# 6. Required Modules
print("\n6️⃣  REQUIRED MODULES:")
required_modules = [
    "fastapi",
    "uvicorn",
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langchain_tavily",
    "pydantic",
    "faiss",
    "dotenv"
]

for module in required_modules:
    try:
        __import__(module)
        print(f"   ✅ {module}")
    except ImportError:
        print(f"   ❌ {module} NOT INSTALLED")

# 7. Policy Documents Check
print("\n7️⃣  POLICY DOCUMENTS:")
policy_zip = project_root / "data" / "policy_Document.zip"
policy_dir = project_root / "data" / "policy_documents"

print(f"   ZIP file exists: {'✅ YES' if policy_zip.exists() else '❌ NO'}")
print(f"   Extracted dir exists: {'✅ YES' if policy_dir.exists() else '❌ NO'}")

if policy_dir.exists():
    files = list(policy_dir.glob("*"))
    print(f"   PDFs in directory: {len(files)}")
    for pdf in files[:3]:  # Show first 3
        print(f"      - {pdf.name}")

# 8. Quick Test
print("\n8️⃣  QUICK IMPORT TEST:")
try:
    from dotenv import load_dotenv
    print("   ✅ Can import dotenv")
except Exception as e:
    print(f"   ❌ Cannot import dotenv: {e}")

try:
    from Src import db_queries
    print("   ✅ Can import Src.db_queries")
except Exception as e:
    print(f"   ❌ Cannot import Src.db_queries: {e}")

try:
    from Src import agent
    print("   ✅ Can import Src.agent")
except Exception as e:
    print(f"   ❌ Cannot import Src.agent: {e}")

print("\n" + "="*80)
print("📝 RECOMMENDATIONS:")
print("="*80)

issues = []

if not db_path.exists():
    issues.append("❌ Database file not found in data/meridain_wealth.db")

if not openai_key:
    issues.append("❌ OPENAI_API_KEY not set - check .env file")

if not tavily_key:
    issues.append("❌ TAVILY_API_KEY not set - check .env file")

if not policy_dir.exists() and policy_zip.exists():
    issues.append("⚠️  Policy documents need to be extracted: unzip data/policy_Document.zip -d data/policy_documents")

if not issues:
    print("✅ All checks passed! Your environment is ready.")
else:
    for issue in issues:
        print(f"  {issue}")

print("\n" + "="*80)
print("🚀 TO START THE SERVER:")
print("  python app.py")
print("="*80 + "\n")
