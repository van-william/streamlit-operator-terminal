import streamlit as st
import openai
from tavily import TavilyClient
import os

st.set_page_config(page_title="Lean Instructor (Web)", layout="wide")
st.title("📚 Lean Instructor (Web-Enabled)")

st.markdown("""
This agent uses **Tavily** to search specific Lean Manufacturing resources (like *lean.org* and *giladlconsulting.com*) 
to provide grounded answers with citations.
""")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    
    # API Keys
    openai_api_key = os.getenv("OPENAI_API_KEY") # or st.secrets.get("OPENAI_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY") # or st.secrets.get("TAVILY_API_KEY")
    
    if not tavily_api_key:
        tavily_api_key = st.text_input("Tavily API Key", type="password")
        
    # Domains to Search
    default_domains = [
        "https://www.giladlconsulting.com/",
        "https://www.lean.org/"
    ]
    domains_input = st.text_area("Target Domains (one per line)", value="\n".join(default_domains), height=100)
    target_domains = [d.strip() for d in domains_input.split('\n') if d.strip()]
    
    if st.button("Clear Conversation"):
        st.session_state.instructor_messages = []
        st.rerun()

# --- Validation ---
if not openai_api_key:
    st.error("Please provide an OpenAI API Key in secrets or environment.")
    st.stop()

if not tavily_api_key:
    st.warning("Please provide a Tavily API Key to enable web search.")
    st.stop()

# --- Clients ---
client = openai.OpenAI(api_key=openai_api_key)
tavily = TavilyClient(api_key=tavily_api_key)

# --- Chat History ---
if "instructor_messages" not in st.session_state:
    st.session_state.instructor_messages = [
        {"role": "system", "content": "You are a Lean Manufacturing Instructor. You answer questions based strictly on the provided context from web search results. Always cite your sources with links."}
    ]

# --- UI: Chat ---
for msg in st.session_state.instructor_messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Ask about Lean principles, 5S, or digital transformation..."):
    # 1. User Message
    st.session_state.instructor_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # 2. Web Search (Tavily)
    with st.status("Searching Lean resources...", expanded=False) as status:
        try:
            # Search active domains
            # Tavily 'include_domains' expects clean domains without https:// usually, 
            # but let's try to parse or pass them. The SDK often handles URLs.
            # Best practice: extract domain from URL.
            clean_domains = []
            for d in target_domains:
                d = d.replace("https://", "").replace("http://", "").split('/')[0]
                clean_domains.append(d)
            
            search_result = tavily.search(
                query=prompt,
                search_depth="advanced",
                include_domains=clean_domains,
                max_results=5
            )
            
            # Format Context
            context_text = ""
            for result in search_result.get('results', []):
                context_text += f"\nSource: {result['title']}\nURL: {result['url']}\nContent: {result['content']}\n"
            
            status.write("Found relevant articles.")
            status.update(label="Search complete!", state="complete")
            
        except Exception as e:
            st.error(f"Tavily Search Error: {e}")
            context_text = ""

    # 3. LLM Response
    if context_text:
        # Augment prompt with context
        augmented_system_prompt = f"""
        You are a Lean Manufacturing Instructor.
        Answer the user's question using ONLY the following context. 
        If the answer is not in the context, say you couldn't find it in the specific resources.
        
        Always cite the source URL when using information.
        
        Context:
        {context_text}
        """
        
        # We create a temporary messages list for the LLM call to include context
        # without polluting the visible chat history with huge context blocks
        llm_messages = [
            {"role": "system", "content": augmented_system_prompt}
        ]
        # Add recent conversation history (optional, or just the last query)
        # For an instructor, immediate context is usually most important
        llm_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o", # Using a strong model for synthesis
                messages=llm_messages,
                stream=True
            )
            response = st.write_stream(stream)
            
        st.session_state.instructor_messages.append({"role": "assistant", "content": response})
    else:
        st.error("No results found or search failed.")

