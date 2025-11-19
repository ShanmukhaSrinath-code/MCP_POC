@echo off
echo Starting MCP Server...
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
