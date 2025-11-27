#!/usr/bin/env python
import sys
import os

# Add server directory to path when running standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(current_dir, "server")
if os.path.exists(server_dir):
    sys.path.insert(0, server_dir)

try:
    from app.database import engine
    from sqlalchemy import text
except ImportError:
    # Try relative import if absolute import fails
    try:
        from server.app.database import engine
        from sqlalchemy import text
    except ImportError:
        print("❌ Error: Cannot import database module. Please run this script from the correct directory.")
        exit(1)

try:
    conn = engine.connect()
    result = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"))
    row = result.fetchone()

    if row:
        print(f"✅ pgvector extension: {row[0]} (version {row[1]})")
        print("🎯 RAG vector search will work!")
    else:
        print("❌ pgvector extension: NOT INSTALLED")
        print("📋 To install:")
        print("   psql -U your_username -d your_database")
        print("   CREATE EXTENSION IF NOT EXISTS vector;")
        print("   \\q")

    conn.close()
except Exception as e:
    print(f"❌ Database connection error: {e}")
