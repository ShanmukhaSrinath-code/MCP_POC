# MCP Data Assistant POC

## What is this POC?

This proof-of-concept demonstrates a complete data analysis solution that combines:

**🎯 Natural Language Data Querying**
- Upload CSV or Excel files via web interface
- Ask questions in plain English (e.g., "What's the average sales by region?")
- Get instant answers powered by AI and pandas data analysis

**🔧 MCP-Compatible Backend**
- REST API server built with FastAPI
- Tool-based interface for data operations
- Resource management for file handling
- Session-based conversation history

**🌐 Modern Web Interface**
- Streamlit-based UI for easy file management
- Multi-file upload support
- Real-time Q&A with source attribution
- Chat history per session

**Key Features:**
- **Multi-file support**: Upload and analyze multiple datasets simultaneously
- **AI-powered analysis**: GPT integration for natural language to pandas conversion
- **Source tracking**: See exactly which data and operations produced each answer
- **Chat persistence**: Conversation history maintained across sessions
- **Caching**: Efficient data loading and caching for performance
- **File management**: Upload, list, and remove files dynamically

## Architecture Overview

- **Backend (FastAPI)**: Handles file operations, data processing, and MCP-compatible tool calls
- **Frontend (Streamlit)**: Provides user interface for file uploads and Q&A
- **AI Layer (OpenAI)**: Converts natural language questions to executable pandas operations
- **Storage**: Local directories for uploaded files and chat history

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. **Navigate to the project directory**
   ```bash
   cd path/to/mcp_poc
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up OpenAI API key**
   - Open the `.env` file
   - Add your OpenAI API key: `OPENAI_API_KEY=your_key_here`

### Running the Application

1. **Start the backend server**
   ```bash
  uvicorn main:app --reload
   ```
   Server will run on http://localhost:8000

2. **Start the web interface**
   ```bash
   streamlit run app.py
   ```
   Open http://localhost:8501 in your browser

## How to Test

### Upload Test Files
1. Go to the web interface at http://localhost:8501
2. Use the sidebar to upload CSV or Excel files
3. Supported formats: .csv, .xlsx, .xls

### Test Q&A Functionality
1. Upload some sample data files
2. Ask questions in natural language, such as:
   - "How many rows are in the data?"
   - "What are the column names?"
   - "Show me the first 5 rows"
   - "What is the average of column X?"


### View Chat History
- Session chat history is automatically saved
- View history through the web interface or API
- Each session maintains its own conversation history




This is a proof-of-concept implementation. For production use, consider:

- Adding authentication and security
- Implementing proper database storage
- Adding WebSocket transport for full MCP compliance
- Comprehensive error handling and logging
- Unit and integration tests

#
