import os
import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile
from typing import List, Dict, Any
import time
import uuid
import json
from functools import lru_cache
from datetime import datetime

app = FastAPI(title="CSV_Excel_MCP_Server", description="Enhanced MCP server for CSV/Excel file operations with multi-file support")

DATA_DIR = "data"
CHAT_HISTORY_DIR = "chat_history"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

# Cache for DataFrames with timestamps and metadata
df_cache = {}
CACHE_TIMEOUT = 300  # 5 minutes

# Enhanced file metadata tracking
file_metadata = {}  # file_id -> metadata
source_tracking = {}  # query_id -> source information

def get_csv_excel_files():
    """Get list of CSV and Excel files in data directory"""
    files = []
    for file in os.listdir(DATA_DIR):
        if file.endswith(('.csv', '.xlsx', '.xls')):
            files.append(os.path.join(DATA_DIR, file))
    return files

def read_file(filename: str) -> pd.DataFrame:
    """Read CSV or Excel file into DataFrame with caching and metadata tracking"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    current_time = time.time()
    cache_key = filename

    # Check cache
    if cache_key in df_cache:
        cached_df, timestamp = df_cache[cache_key]
        if current_time - timestamp < CACHE_TIMEOUT:
            # Update source tracking info
            file_metadata[cache_key] = {
                'last_accessed': current_time,
                'file_size': os.path.getsize(filepath),
                'file_type': 'csv' if filename.endswith('.csv') else 'excel'
            }
            return cached_df
        else:
            # Cache expired, remove it
            del df_cache[cache_key]

    # Read file
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Cache the DataFrame with metadata
        df_cache[cache_key] = (df.copy(), current_time)
        
        # Track file metadata
        file_metadata[cache_key] = {
            'last_accessed': current_time,
            'file_size': os.path.getsize(filepath),
            'file_type': 'csv' if filename.endswith('.csv') else 'excel',
            'upload_time': current_time,
            'columns': list(df.columns),
            'row_count': len(df)
        }
        
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file {filename}: {str(e)}")

def track_query_source(query_id: str, filename: str, operation: str, columns_used: List[str] = None):
    """Track source information for a query"""
    source_tracking[query_id] = {
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'operation': operation,
        'columns_used': columns_used or [],
        'metadata': file_metadata.get(filename, {}),
        'query_result_summary': None
    }

def save_chat_history(session_id: str, question: str, response: str, source_info: Dict[str, Any] = None):
    """Save chat history to file"""
    try:
        history_file = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        # Add new entry
        new_entry = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'response': response,
            'source_info': source_info or {}
        }
        history.append(new_entry)
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

def get_chat_history(session_id: str) -> List[Dict[str, Any]]:
    """Get chat history for a session"""
    try:
        history_file = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

@app.get("/")
async def root():
    return {"message": "CSV_Excel_MCP_Server", "version": "2.0.0"}

@app.get("/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "list_files",
                "description": "List all uploaded CSV/Excel files with their columns.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_columns",
                "description": "Return all column names for a given file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "describe_file",
                "description": "Provide basic statistics (row count, column count, data types) for a given file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"}
                    },
                    "required": ["filename"]
                }
            },
            {
                "name": "query_data",
                "description": "Perform queries on data using pandas code with enhanced source tracking.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "operation": {"type": "string"},
                        "code": {"type": "string"},
                        "query_id": {"type": "string"},
                        "session_id": {"type": "string"},
                        "question": {"type": "string"}
                    },
                    "required": ["filename", "operation"]
                }
            },
            {
                "name": "get_chat_history",
                "description": "Get chat history for a specific session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            },
            {
                "name": "upload_files",
                "description": "Upload multiple CSV/Excel files at once.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"}
                    },
                    "required": ["session_id"]
                }
            }
        ]
    }

@app.post("/upload")
async def upload_files(session_id: str, files: List[UploadFile] = File(...)):
    """Upload multiple files for a session"""
    try:
        uploaded_files = []
        for file in files:
            # Validate file type
            if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
                return {"error": f"File {file.filename} is not a supported format. Only CSV and Excel files are allowed."}
            
            # Save file
            filepath = os.path.join(DATA_DIR, file.filename)
            with open(filepath, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Read and validate file
            try:
                df = read_file(file.filename)
                file_metadata[file.filename] = {
                    'upload_time': time.time(),
                    'file_size': len(content),
                    'file_type': 'csv' if file.filename.endswith('.csv') else 'excel',
                    'columns': list(df.columns),
                    'row_count': len(df),
                    'session_id': session_id
                }
                uploaded_files.append({
                    'filename': file.filename,
                    'size': len(content),
                    'columns': list(df.columns),
                    'row_count': len(df)
                })
            except Exception as e:
                # Remove file if reading fails
                os.remove(filepath)
                return {"error": f"Error reading file {file.filename}: {str(e)}"}
        
        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "uploaded_files": uploaded_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

@app.get("/chat_history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session"""
    history = get_chat_history(session_id)
    return {"session_id": session_id, "history": history}

@app.delete("/chat_history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history for a session"""
    try:
        history_file = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(history_file):
            os.remove(history_file)
        return {"message": f"Chat history cleared for session {session_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """Enhanced tool calling with source tracking and chat history"""
    try:
        # Generate query ID for tracking
        query_id = str(uuid.uuid4())
        
        if tool_name == "list_files":
            files_info = []
            for filepath in get_csv_excel_files():
                filename = os.path.basename(filepath)
                try:
                    df = read_file(filename)
                    files_info.append({
                        "filename": filename,
                        "columns": list(df.columns),
                        "row_count": len(df),
                        "file_size": file_metadata.get(filename, {}).get('file_size', 0)
                    })
                except Exception as e:
                    continue  # Skip files that can't be read

            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(files_info)
                    }
                ],
                "source_info": {
                    "query_id": query_id,
                    "operation": "list_files",
                    "files_found": len(files_info)
                }
            }

        elif tool_name == "get_columns":
            filename = arguments.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="filename is required")

            df = read_file(filename)
            result = {
                "columns": list(df.columns),
                "column_count": len(df.columns)
            }
            
            # Track source
            track_query_source(query_id, filename, "get_columns", list(df.columns))
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ],
                "source_info": {
                    "query_id": query_id,
                    "filename": filename,
                    "operation": "get_columns",
                    "columns_returned": list(df.columns)
                }
            }

        elif tool_name == "describe_file":
            filename = arguments.get("filename")
            if not filename:
                raise HTTPException(status_code=400, detail="filename is required")

            df = read_file(filename)
            columns_info = []
            for col in df.columns:
                columns_info.append({
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "non_null_count": int(df[col].count())
                })

            result = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": columns_info
            }

            # Track source
            track_query_source(query_id, filename, "describe_file", list(df.columns))
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ],
                "source_info": {
                    "query_id": query_id,
                    "filename": filename,
                    "operation": "describe_file",
                    "row_count": len(df),
                    "column_count": len(df.columns)
                }
            }

        elif tool_name == "query_data":
            filename = arguments.get("filename")
            operation = arguments.get("operation")
            column = arguments.get("column")
            n = arguments.get("n", 5)
            filter_expr = arguments.get("filter")
            session_id = arguments.get("session_id")
            question = arguments.get("question")
            
            query_id = arguments.get("query_id") or str(uuid.uuid4())

            if not filename or not operation:
                raise HTTPException(status_code=400, detail="filename and operation are required")

            df = read_file(filename)

            # Apply filter if provided
            if filter_expr:
                try:
                    df = df.query(filter_expr)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid filter expression: {str(e)}")

            result = None

            if operation == "head":
                result = df.head(n).to_dict('records')
            elif operation == "average" and column:
                if column not in df.columns:
                    raise HTTPException(status_code=400, detail=f"Column {column} not found")
                result = float(df[column].mean())
            elif operation == "sum" and column:
                if column not in df.columns:
                    raise HTTPException(status_code=400, detail=f"Column {column} not found")
                result = float(df[column].sum())

            elif operation == "execute":
                code = arguments.get("code")
                if not code:
                    raise HTTPException(status_code=400, detail="code is required for execute operation")
                try:
                    exec_result = eval(code, {"pd": pd, "df": df})
                    if hasattr(exec_result, 'to_dict'):
                        if isinstance(exec_result, pd.DataFrame):
                            result = exec_result.to_dict('records')
                        else:
                            result = exec_result.to_dict()
                    else:
                        result = exec_result
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Error executing code: {str(e)}")

            elif operation == "count":
                result = len(df)
            elif operation == "describe":
                result = df.describe().to_dict()
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")

            # Track source information
            columns_used = [column] if column else []
            track_query_source(query_id, filename, operation, columns_used)
            
            # Update source tracking with query result summary
            if source_tracking.get(query_id):
                source_tracking[query_id]['query_result_summary'] = {
                    'result_type': type(result).__name__,
                    'result_size': len(str(result)) if result else 0
                }
            
            # Save to chat history if session info provided
            if session_id and question:
                response_text = str(result)
                source_info = source_tracking.get(query_id, {})
                save_chat_history(session_id, question, response_text, source_info)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ],
                "source_info": {
                    "query_id": query_id,
                    "filename": filename,
                    "operation": operation,
                    "columns_used": columns_used,
                    "result_summary": source_tracking.get(query_id, {}).get('query_result_summary', {}),
                    "timestamp": datetime.now().isoformat()
                }
            }

        elif tool_name == "get_chat_history":
            session_id = arguments.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id is required")
            
            history = get_chat_history(session_id)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(history)
                    }
                ]
            }

        else:
            raise HTTPException(status_code=404, detail="Tool not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources")
async def list_resources():
    """Enhanced resource listing with metadata"""
    resources = []
    for filepath in get_csv_excel_files():
        filename = os.path.basename(filepath)
        metadata = file_metadata.get(filename, {})
        resources.append({
            "uri": f"file://{filename}",
            "name": filename,
            "description": f"CSV/Excel file: {filename}",
            "mimeType": "application/octet-stream",
            "metadata": {
                "file_size": metadata.get('file_size', 0),
                "row_count": metadata.get('row_count', 0),
                "upload_time": metadata.get('upload_time', 0),
                "columns": metadata.get('columns', [])
            }
        })

    return {"resources": resources}

@app.get("/resources/{resource_uri:path}")
async def read_resource(resource_uri: str):
    """Enhanced resource reading with source tracking"""
    if resource_uri.startswith("file://"):
        filename = resource_uri[7:]  # Remove "file://" prefix
        filepath = os.path.join(DATA_DIR, filename)

        if os.path.exists(filepath):
            try:
                df = read_file(filename)
                return {
                    "contents": [
                        {
                            "uri": resource_uri,
                            "mimeType": "application/json",
                            "text": df.to_json(orient='records')
                        }
                    ],
                    "metadata": file_metadata.get(filename, {})
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    raise HTTPException(status_code=404, detail="Resource not found")

@app.get("/source/{query_id}")
async def get_source_info(query_id: str):
    """Get detailed source information for a specific query"""
    source_info = source_tracking.get(query_id)
    if source_info:
        return {
            "query_id": query_id,
            "source_info": source_info
        }
    raise HTTPException(status_code=404, detail="Source information not found")

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a file from the system"""
    try:
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Clean up cache and metadata
            if filename in df_cache:
                del df_cache[filename]
            if filename in file_metadata:
                del file_metadata[filename]
            return {"message": f"File {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
