"""
Simple Streamlit test app for Manufacturing AI Analysis
"""
import streamlit as st
import sys
import requests

st.set_page_config(
    page_title="Manufacturing AI Test",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 Manufacturing AI Analysis - Test Interface")

# Test basic functionality
st.sidebar.header("System Status")

# Test API connection
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        st.sidebar.success("✅ API Server Connected")
        api_status = "Connected"
    else:
        st.sidebar.error(f"❌ API Error: {response.status_code}")
        api_status = f"Error {response.status_code}"
except requests.exceptions.ConnectionError:
    st.sidebar.error("❌ API Server Not Running")
    api_status = "Not Connected"
except Exception as e:
    st.sidebar.error(f"❌ Connection Error: {e}")
    api_status = "Error"

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🚀 Quick Start Guide")
    
    st.markdown("""
    ### Step 1: Start the API Server
    ```bash
    cd /Users/guru/Manufacturing_AIAnalysis
    python3 app/test_server.py
    ```
    
    ### Step 2: Test the Connection
    Click the "Test API" button below to verify the connection.
    
    ### Step 3: Upload Data Files
    Once everything is working, upload your CSV/Excel manufacturing data files.
    """)
    
    if st.button("🔍 Test API Connection"):
        if api_status == "Connected":
            st.success("✅ Great! API is responding correctly.")
            try:
                test_response = requests.get("http://localhost:8000/test")
                if test_response.status_code == 200:
                    data = test_response.json()
                    st.json(data)
            except Exception as e:
                st.warning(f"API connected but test failed: {e}")
        else:
            st.error("❌ API Server is not running. Please start it first.")

with col2:
    st.header("📊 Status")
    
    st.metric("API Status", api_status)
    st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}")
    st.metric("Streamlit", "✅ Working")
    
    st.markdown("---")
    st.markdown("### 🔧 Troubleshooting")
    st.markdown("""
    - **API Not Connected**: Start the server with `python3 app/test_server.py`
    - **Import Errors**: Check virtual environment and dependencies
    - **Port Issues**: Make sure port 8000 is available
    """)

# File upload test
st.header("📁 File Upload Test")
uploaded_file = st.file_uploader(
    "Test file upload functionality",
    type=['csv', 'xlsx', 'xls'],
    help="This is just a test - files won't be processed yet"
)

if uploaded_file:
    st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
    st.write(f"File size: {uploaded_file.size} bytes")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>🏭 Manufacturing AI Analysis - Test Interface</div>",
    unsafe_allow_html=True
)