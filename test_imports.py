#!/usr/bin/env python3
"""Test script to verify circular import resolution"""
import sys
import os

# Add server directory to path - we're in the root Radex directory
server_dir = os.path.join(os.getcwd(), "Radex", "server")
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

# Set the working directory to server for proper import resolution
os.chdir(server_dir)

def test_imports():
    try:
        print("Testing imports...")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path[0]}")
        
        # Test individual imports
        print("1. Testing EmbeddingService import...")
        from app.services.embedding_service import EmbeddingService
        print("   ✅ EmbeddingService imported successfully")
        
        print("2. Testing DocumentService import...")
        from app.services.document_service import DocumentService
        print("   ✅ DocumentService imported successfully")
        
        print("3. Testing RAGService import...")
        from app.services.rag_service import RAGService
        print("   ✅ RAGService imported successfully")
        
        print("4. Testing MCPDataProcessor import...")
        from app.mcp.data_processor import MCPDataProcessor
        print("   ✅ MCPDataProcessor imported successfully")
        
        print("\n🎉 All imports successful! Circular import issue resolved!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Available files in current directory:")
        for item in os.listdir('.'):
            print(f"  - {item}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    test_imports()
