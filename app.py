import streamlit as st
import pandas as pd
import os
import requests
import json
import uuid
from dotenv import load_dotenv
import openai
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress Streamlit warnings when run in bare mode
logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').setLevel(logging.ERROR)
logging.getLogger('streamlit.runtime.state.session_state_proxy').setLevel(logging.ERROR)

load_dotenv()

# Page config for modern look
st.set_page_config(
    page_title="Enhanced MCP Data Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MCP Server URL - Updated to use enhanced server
MCP_SERVER_URL = "http://localhost:8000"

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize session state for enhanced features
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.uploaded_files = []
    st.session_state.source_tracking = {}

st.title("🚀 Enhanced MCP Data Assistant with Multi-File Support")

st.markdown("Upload multiple CSV/Excel files, maintain chat history, and get source attribution for all your data queries.")

def call_mcp_tool(tool_name, **kwargs):
    """Call an MCP tool and return the result with source tracking"""
    try:
        logger.info(f"Calling MCP tool: {tool_name} with args: {kwargs}")
        response = requests.post(
            f"{MCP_SERVER_URL}/tools/{tool_name}",
            json=kwargs,
            headers={"Content-Type": "application/json"}
        )
        
        # Log the response status
        logger.info(f"MCP Response Status: {response.status_code}")
        
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"MCP Error: {error_detail}")
            return {"error": f"❌ Error calling MCP tool {tool_name} (Status {response.status_code}): {error_detail}"}
        
        result = response.json()
        logger.info(f"MCP Response: {result}")

        return result
    except Exception as e:
        logger.error(f"Exception calling MCP tool: {str(e)}")
        return {"error": f"❌ Error calling MCP tool {tool_name}: {str(e)}"}

def upload_multiple_files(files, session_id):
    """Upload multiple files to the server"""
    try:
        # Prepare files for upload
        file_list = []
        for file in files:
            if file is not None:
                file_list.append(('files', (file.name, file.getvalue(), file.type)))
        
        # Send to upload endpoint
        response = requests.post(
            f"{MCP_SERVER_URL}/upload?session_id={session_id}",
            files=file_list
        )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return {"error": f"Upload failed: {response.text}"}
    except Exception as e:
        return {"error": f"Upload error: {str(e)}"}

def load_chat_history(session_id):
    """Load chat history from server"""
    try:
        response = requests.get(f"{MCP_SERVER_URL}/chat_history/{session_id}")
        if response.status_code == 200:
            return response.json().get('history', [])
        return []
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return []

def clear_chat_history(session_id):
    """Clear chat history on server"""
    try:
        response = requests.delete(f"{MCP_SERVER_URL}/chat_history/{session_id}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return False

def format_natural_response(question, raw_result, filename, source_info=None):
    """Convert raw MCP tool results into natural language responses using OpenAI"""
    try:
        context = f"""
Dataset: {filename}
Raw Query Result: {raw_result}
Question: {question}

Source Information: {source_info}

Based on the raw result above and source information, provide a clear, natural language answer to the user's question. Use the data to give specific insights and format numbers appropriately. Include source attribution when relevant.
"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a data analysis assistant. Your task is to convert raw data query results into clear, natural language answers that business users can understand.

Be direct and informative. Format numbers appropriately (use commas for thousands, show decimals only when relevant). Explain what the data represents and provide context about the dataset.

IMPORTANT: When source information is available, mention the data source and any relevant details about the query."""},
                {"role": "user", "content": context}
            ],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}")
        return f"📊 Raw result: {raw_result}"

def display_source_attribution(source_info):
    """Display source attribution information"""
    if source_info and not source_info.get('error'):
        with st.expander("🔍 Source Information", expanded=False):
            st.markdown("### Query Source Details")
            
            if 'query_id' in source_info:
                st.markdown(f"**Query ID:** `{source_info['query_id']}`")
            
            if 'filename' in source_info:
                st.markdown(f"**Source File:** `{source_info['filename']}`")
            
            if 'operation' in source_info:
                st.markdown(f"**Operation:** `{source_info['operation']}`")
            
            if 'columns_used' in source_info:
                st.markdown(f"**Columns Used:** {', '.join(source_info['columns_used'])}")
            
            if 'timestamp' in source_info:
                st.markdown(f"**Timestamp:** `{source_info['timestamp']}`")
            
            if 'result_summary' in source_info:
                st.markdown(f"**Result Type:** `{source_info['result_summary'].get('result_type', 'Unknown')}`")
                st.markdown(f"**Result Size:** {source_info['result_summary'].get('result_size', 0)} characters")

# Sidebar for file upload and info
with st.sidebar:
    st.header("📁 Multi-File Upload & Management")
    
    # Session info
    st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
    
    # Multiple file upload
    uploaded_files = st.file_uploader(
        "Choose multiple CSV/Excel files", 
        type=["csv", "xlsx", "xls"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("🚀 Upload Files", key="upload_button"):
            with st.spinner("Uploading files..."):
                upload_result = upload_multiple_files(uploaded_files, st.session_state.session_id)
                
                if "error" in upload_result:
                    st.error(upload_result["error"])
                else:
                    st.success(upload_result.get("message", "Files uploaded successfully!"))
                    st.session_state.uploaded_files = upload_result.get("uploaded_files", [])
                    
                    # Show uploaded files info
                    st.subheader("📋 Uploaded Files")
                    for file_info in st.session_state.uploaded_files:
                        st.markdown(f"**{file_info['filename']}**")
                        st.markdown(f"- Size: {file_info['size']:,} bytes")
                        st.markdown(f"- Rows: {file_info['row_count']:,}")
                        st.markdown(f"- Columns: {', '.join(file_info['columns'])}")
                        st.markdown("---")
    
    # File management tools
    if uploaded_files:
        with st.expander("🛠️ File Management Tools"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📂 List All Files", key="list_files"):
                    with st.spinner("Listing files..."):
                        result = call_mcp_tool("list_files")
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.code(result.get("content", [{}])[0].get("text", ""), language="json")
                            
                            # Store source info
                            if "source_info" in result:
                                st.session_state.source_tracking[st.session_state.session_id] = result["source_info"]
            
            with col2:
                selected_file = st.selectbox(
                    "Select file for operations", 
                    [f['filename'] for f in st.session_state.uploaded_files] if st.session_state.uploaded_files else []
                )
                
                if selected_file and st.button(f"📊 Describe {selected_file}", key="desc_file"):
                    with st.spinner(f"Describing {selected_file}..."):
                        result = call_mcp_tool("describe_file", filename=selected_file)
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.code(result.get("content", [{}])[0].get("text", ""), language="json")
                            
                            # Display source info
                            if "source_info" in result:
                                display_source_attribution(result["source_info"])

    # Chat history management
    if st.session_state.chat_history:
        st.subheader("📝 Chat History Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Load History", key="load_history"):
                with st.spinner("Loading chat history..."):
                    server_history = load_chat_history(st.session_state.session_id)
                    if server_history:
                        st.session_state.chat_history = server_history
                        st.success(f"Loaded {len(server_history)} messages from server")
                    else:
                        st.info("No chat history found on server")
        
        with col2:
            if st.button("🗑️ Clear History", key="clear_history"):
                if clear_chat_history(st.session_state.session_id):
                    st.session_state.chat_history = []
                    st.success("Chat history cleared")
                else:
                    st.error("Failed to clear chat history")
        
        # Display local chat history
        st.subheader("📋 Current Session History")
        for i, entry in enumerate(st.session_state.chat_history[-5:]):  # Show last 5
            st.markdown(f"**Q:** {entry.get('question', 'N/A')}")
            st.markdown(f"**A:** {entry.get('response', 'N/A')[:200]}...")
            st.divider()

# Main content area for Q&A
st.header("💬 Enhanced Q&A with Source Attribution")

if not st.session_state.uploaded_files:
    st.info("👈 Please upload some files from the sidebar to get started.")
else:
    st.markdown(f"Ask natural language questions about your uploaded data. Currently analyzing **{len(st.session_state.uploaded_files)} file(s)**.")
    
    # Display available files
    with st.expander("📁 Available Files", expanded=True):
        for file_info in st.session_state.uploaded_files:
            st.markdown(f"- **{file_info['filename']}** ({file_info['row_count']:,} rows, {len(file_info['columns'])} columns)")

    # Question input
    question = st.text_input("Enter your question:", placeholder="e.g., What is the average batting average? or Show me the top 5 players by total runs.", key="question_input")

    if st.button("🚀 Ask Question", key="ask_button") and question:
        with st.spinner("🤔 Analyzing your question and processing data..."):
            try:
                # Generate query ID for tracking
                query_id = str(uuid.uuid4())
                
                # Get available columns for context
                available_columns = {}
                for file_info in st.session_state.uploaded_files:
                    available_columns[file_info['filename']] = file_info['columns']
                
                # Use OpenAI to determine which MCP tool to call and how to interpret the question
                files_context = json.dumps(available_columns, indent=2)
                
                # Build chat history context for follow-up questions
                chat_history_context = ""
                if st.session_state.chat_history:
                    recent_entries = st.session_state.chat_history[-3:]  # Last 3 conversations
                    chat_history_context = "Recent Conversation History:\n" + "\n".join([
                        f"Q: {entry['question']}\nA: {entry['response'][:200]}{'...' if len(entry['response']) > 200 else ''}"
                        for entry in recent_entries
                    ]) + "\n\n"

                context = f"""
{chat_history_context}Question: {question}
Available Files and Columns:
{files_context}

IMPORTANT: You must use these EXACT column names in your pandas code. Do not invent or guess column names.
Use context from recent conversation history to understand references to previous answers, entities, or data.

Available MCP tools:
- list_files: List all uploaded CSV/Excel files with their columns
- get_columns: Return all column names for a file
- describe_file: Provide statistics (row count, column count, data types) for a file
- query_data: Perform queries on data using pandas code with parameters: operation (execute, head, count, average, sum, describe), code (pandas code to execute on df), n (number of rows for head operation)

For most data queries, use query_data with operation="execute" and code containing a pandas expression to evaluate on df.

Respond with ONLY valid JSON, no markdown, no explanations:
{{"tool": "query_data", "parameters": {{"filename": "file.csv", "operation": "execute", "code": "pandas expression", "query_id": "{query_id}", "session_id": "{st.session_state.session_id}", "question": "{question}"}}}}

Examples:
- "What is the average of total_runs?" -> {{"tool": "query_data", "parameters": {{"filename": "file.csv", "operation": "execute", "code": "df['total_runs'].mean()", "query_id": "{query_id}", "session_id": "{st.session_state.session_id}", "question": "{question}"}}}}
- "Show top 5 rows" -> {{"tool": "query_data", "parameters": {{"filename": "file.csv", "operation": "execute", "code": "df.head(5).to_dict('records')", "query_id": "{query_id}", "session_id": "{st.session_state.session_id}", "question": "{question}"}}}}
- "How many rows?" -> {{"tool": "query_data", "parameters": {{"filename": "file.csv", "operation": "count", "query_id": "{query_id}", "session_id": "{st.session_state.session_id}", "question": "{question}"}}}}
"""

                logger.info(f"Sending question to OpenAI: {question}")
                
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": """You are an AI that analyzes questions about data and generates MCP tool calls.

CRITICAL: Respond ONLY with valid JSON. No markdown code blocks, no explanations, no extra text.

Format: {"tool": "tool_name", "parameters": {"filename": "file.csv", ...}}

For most data questions, use query_data with operation="execute" and code containing a pandas expression to evaluate on df."""},
                        {"role": "user", "content": context}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )

                # Parse the AI response to get tool and parameters
                ai_response = response.choices[0].message.content.strip()
                logger.info(f"AI Response: {ai_response}")
                
                # Display AI response for debugging
                with st.expander("🔍 Debug: AI Response", expanded=False):
                    st.code(ai_response, language="json")
                
                try:
                    # Clean up the response - remove markdown code blocks if present
                    if ai_response.startswith("```"):
                        ai_response = ai_response.split("```")[1]
                        if ai_response.startswith("json"):
                            ai_response = ai_response[4:]
                        ai_response = ai_response.strip()
                    
                    # Parse JSON
                    tool_info = json.loads(ai_response)
                    tool_name = tool_info["tool"]
                    params = tool_info["parameters"]
                    
                    logger.info(f"Calling tool: {tool_name} with params: {params}")

                    # Call the MCP tool
                    mcp_result = call_mcp_tool(tool_name, **params)
                    
                    # Display raw result for debugging
                    with st.expander("🔍 Debug: Raw MCP Result", expanded=False):
                        st.code(json.dumps(mcp_result, indent=2), language="json")

                    if "error" in mcp_result:
                        st.error(mcp_result["error"])
                    else:
                        # Extract content and source info
                        content = mcp_result.get("content", [{}])[0].get("text", "")
                        source_info = mcp_result.get("source_info", {})
                        
                        # Format the response naturally
                        selected_file = params.get("filename", "Unknown file")
                        natural_response = format_natural_response(question, content, selected_file, source_info)

                        # Add to local chat history
                        chat_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "question": question,
                            "response": natural_response,
                            "source_info": source_info
                        }
                        st.session_state.chat_history.append(chat_entry)

                        # Display the response
                        st.markdown("**💡 Answer:**")
                        st.success(natural_response)
                        
                        # Display source attribution
                        if source_info:
                            display_source_attribution(source_info)

                        # Show updated chat history
                        if len(st.session_state.chat_history) > 1:
                            with st.expander("📋 Chat History", expanded=False):
                                for i, entry in enumerate(st.session_state.chat_history[-3:], 1):  # Show last 3
                                    st.markdown(f"**{i}. Q:** {entry['question']}")
                                    st.markdown(f"**   A:** {entry['response'][:150]}{'...' if len(entry['response']) > 150 else ''}")
                                    st.divider()

                except json.JSONDecodeError as e:
                    st.error(f"❌ Error parsing AI response as JSON: {e}")
                    st.subheader("Raw AI Response:")
                    st.code(ai_response)
                    logger.error(f"JSON parse error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error processing tool call: {str(e)}")
                    logger.error(f"Tool call error: {str(e)}")

            except Exception as e:
                st.error(f"❌ Error processing question: {str(e)}")
                logger.error(f"Question processing error: {str(e)}")

# Enhanced footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🚀 Enhanced MCP Server v2.0.0")
with col2:
    st.caption(f"📊 {len(st.session_state.uploaded_files)} files loaded")
with col3:
    st.caption(f"💬 {len(st.session_state.chat_history)} interactions")

st.caption("Built with Streamlit, Enhanced MCP, and OpenAI. Multi-file support, chat history, and source attribution enabled.")
