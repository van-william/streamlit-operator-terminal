import streamlit as st
import openai
import os
import json
import pandas as pd
from db import get_connection, get_lines, get_machines, get_downtime_reasons

# --- Page Config ---
st.set_page_config(page_title="Lean Assistant", layout="wide")
st.title("🏭 Factory & Lean Q&A Bot")

# --- Sidebar / Context ---
with st.sidebar:
    st.markdown("### Assistant Settings")
    model = st.selectbox("Model", ["gpt-3.5-turbo", "gpt-4", "gpt-4o"], index=0)
    st.markdown("""
    **Expertise:**
    - Lean Manufacturing Principles (5S, Kaizen, Kanban)
    - Root Cause Analysis (5 Whys, Fishbone)
    - Operational Efficiency (OEE)
    - **Active Database Querying**
    """)
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- Setup OpenAI ---
api_key =  os.getenv("OPENAI_API_KEY")
# st.secrets.get("OPENAI_API_KEY") or
client = openai.OpenAI(api_key=api_key)

# --- Tool Definitions ---

def run_sql_query(query):
    """Executes a SQL query on the internal SQLite database and returns the results."""
    try:
        conn = get_connection()
        # Use pandas for easy formatting, but strict SQL is fine too
        df = pd.read_sql(query, conn)
        conn.close()
        return df.to_json(orient="records", date_format="iso")
    except Exception as e:
        return f"Error executing query: {str(e)}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": "Execute a SELECT SQL query against the factory database to retrieve data about production, downtime, quality, or orders. The database is SQLite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute. Example: SELECT * FROM downtime_events WHERE start_time > '2023-01-01'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """You are a highly experienced Manufacturing Engineer and Lean Six Sigma Black Belt. 
        You help operators, supervisors, and managers with factory operations.
        
        You have access to the factory database via the 'run_sql_query' tool. 
        When asked for data, stats, or recent events, write a SQL query to fetch it.
        
        Database Schema Context:
        - lines (id, name, description)
        - machines (id, name, line_id, description)
        - work_orders (id, wo_number, part_number, target_quantity, status, line_id)
        - downtime_events (id, machine_id, reason_id, start_time, end_time, duration_minutes, notes)
        - quality_events (id, machine_id, reason_id, quantity, timestamp, notes)
        - production_counts (id, machine_id, good_quantity, scrap_quantity, timestamp)
        - downtime_reasons (id, code, description, category)
        - quality_reasons (id, code, description, category)
        
        Always LIMIT large queries to 20 rows unless asked otherwise.
        """}
    ]

# --- Display Chat ---
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            # If content is None (tool call), show something else or skip
            if message.get("content"):
                st.markdown(message["content"])
            elif message.get("tool_calls"):
                st.markdown("*Checking database...*")

# --- User Input ---
if prompt := st.chat_input("Ask about Lean, OEE, or how to solve a production issue..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response loop (to handle tool calls)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # 1. First Call
        completion = client.chat.completions.create(
            model=model,
            messages=st.session_state.messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = completion.choices[0].message
        
        # 2. Check for tool calls
        if response_message.tool_calls:
            # Append the assistant's request to history
            st.session_state.messages.append(response_message)
            
            # Execute tool calls
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "run_sql_query":
                    args = json.loads(tool_call.function.arguments)
                    query = args["query"]
                    message_placeholder.markdown(f"```sql\n{query}\n```")
                    
                    # Run Function
                    result = run_sql_query(query)
                    
                    # Append result to history
                    st.session_state.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "run_sql_query",
                        "content": result,
                    })
            
            # 3. Second Call (Get final answer active on data)
            final_completion = client.chat.completions.create(
                model=model,
                messages=st.session_state.messages,
            )
            final_response = final_completion.choices[0].message.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
        else:
            # No tool call, just normal response
            final_response = response_message.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
