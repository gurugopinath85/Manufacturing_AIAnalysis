"""
Enhanced Streamlit UI for Manufacturing AI Analysis.
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="Manufacturing AI Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .sidebar-info {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .metric-container {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e1e8ed;
        margin: 0.5rem 0;
    }
    
    .recommendation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .chat-message {
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "system_status" not in st.session_state:
    st.session_state.system_status = {}

def make_api_request(endpoint, method="GET", data=None, files=None):
    """Helper function to make API requests."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API. Please ensure the FastAPI server is running."
    except Exception as e:
        return None, f"Request failed: {str(e)}"

def get_system_status():
    """Get system status from API."""
    status, error = make_api_request("/status")
    if status:
        st.session_state.system_status = status
        return status
    else:
        st.error(f"Failed to get system status: {error}")
        return None

def upload_files_to_api(uploaded_files):
    """Upload files to the API."""
    files = []
    for uploaded_file in uploaded_files:
        files.append(("files", (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)))
    
    result, error = make_api_request("/upload", method="POST", files=files)
    if result:
        st.session_state.uploaded_files.extend(result["uploaded_files"])
        return result
    else:
        st.error(f"Upload failed: {error}")
        return None

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🏭 Manufacturing AI Assistant</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("System Status")
        
        # System status check
        if st.button("🔄 Refresh Status"):
            get_system_status()
        
        # Display system info
        if st.session_state.system_status:
            status = st.session_state.system_status
            st.markdown(f"""
            <div class="sidebar-info">
                <h4>📊 Data Overview</h4>
                <p><strong>Tables Loaded:</strong> {status.get('tables_loaded', 0)}</p>
                <p><strong>System:</strong> {status.get('system_status', 'Unknown').title()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if status.get('table_names'):
                st.markdown("**Available Tables:**")
                for table in status['table_names']:
                    st.markdown(f"• {table}")
        
        # Settings
        st.header("⚙️ Settings")
        
        # API connection test
        if st.button("🔍 Test Connection"):
            health, error = make_api_request("/health")
            if health:
                st.success("✅ API Connected")
            else:
                st.error(f"❌ Connection Failed: {error}")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Data Upload", "🔍 Explore Data", "💬 Chat Assistant", "📊 Recommendations", "📈 Analytics"])
    
    with tab1:
        st.header("📁 Data Upload & Processing")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Upload Files")
            uploaded_files = st.file_uploader(
                "Upload CSV or Excel files",
                type=['csv', 'xlsx', 'xls'],
                accept_multiple_files=True,
                help="Upload your manufacturing data files (inventory, demand, production, etc.)"
            )
            
            if uploaded_files:
                st.write("Files to upload:")
                for file in uploaded_files:
                    st.write(f"• {file.name} ({file.size} bytes)")
                
                if st.button("📤 Upload Files"):
                    with st.spinner("Uploading files..."):
                        result = upload_files_to_api(uploaded_files)
                        if result:
                            st.success(f"✅ Uploaded {len(result['uploaded_files'])} files successfully!")
                            
                            # Auto-process schema
                            if st.checkbox("Auto-process schema", value=True):
                                with st.spinner("Processing schema..."):\n                                    schema_result, error = make_api_request(\"/schema/extract\", \"POST\", {\"force_reprocess\": True})\n                                    if schema_result:\n                                        st.success(\"✅ Schema processed successfully!\")\n                                        get_system_status()  # Refresh status\n                                    else:\n                                        st.warning(f\"Schema processing failed: {error}\")\n        \n        with col2:\n            st.subheader(\"Processing Options\")\n            \n            if st.button(\"🔍 Extract Schema\"):\n                with st.spinner(\"Analyzing data structure...\"):\n                    schema_result, error = make_api_request(\"/schema/extract\", \"POST\", {})\n                    if schema_result:\n                        st.success(f\"✅ Processed {len(schema_result['processed_files'])} files\")\n                        st.write(f\"Processing time: {schema_result['processing_time_seconds']:.2f}s\")\n                        get_system_status()\n                    else:\n                        st.error(f\"Schema extraction failed: {error}\")\n            \n            if st.session_state.system_status.get('tables_loaded', 0) > 0:\n                st.markdown(\"### 📋 Quick Actions\")\n                \n                if st.button(\"📊 View Data Summary\"):\n                    status = st.session_state.system_status\n                    if status.get('data_summary'):\n                        summary = status['data_summary']\n                        st.json(summary)\n    \n    with tab2:\n        st.header(\"🔍 Data Exploration\")\n        \n        if st.session_state.system_status.get('tables_loaded', 0) > 0:\n            col1, col2 = st.columns([1, 1])\n            \n            with col1:\n                st.subheader(\"Natural Language Queries\")\n                \n                # Query suggestions\n                suggestions, error = make_api_request(\"/query/suggestions\")\n                if suggestions:\n                    st.markdown(\"**💡 Suggested Queries:**\")\n                    for suggestion in suggestions['suggestions'][:5]:\n                        if st.button(suggestion, key=f\"suggest_{suggestion}\"):\n                            # Execute the suggested query\n                            query_data = {\"question\": suggestion, \"include_explanation\": True}\n                            result, error = make_api_request(\"/query\", \"POST\", query_data)\n                            if result:\n                                st.success(\"Query executed successfully!\")\n                                if result['explanation']:\n                                    st.write(result['explanation'])\n                                if result['results']:\n                                    df = pd.DataFrame(result['results'])\n                                    st.dataframe(df, use_container_width=True)\n                            else:\n                                st.error(f\"Query failed: {error}\")\n                \n                # Custom query input\n                st.markdown(\"**🔍 Ask Your Own Question:**\")\n                custom_query = st.text_input(\n                    \"Enter your question:\",\n                    placeholder=\"e.g., Which products have low inventory?\"\n                )\n                \n                if st.button(\"🚀 Execute Query\") and custom_query:\n                    with st.spinner(\"Processing query...\"):\n                        query_data = {\"question\": custom_query, \"include_explanation\": True}\n                        result, error = make_api_request(\"/query\", \"POST\", query_data)\n                        if result:\n                            st.success(\"✅ Query completed!\")\n                            \n                            if result['explanation']:\n                                st.markdown(\"**📝 Explanation:**\")\n                                st.write(result['explanation'])\n                            \n                            if result['results']:\n                                st.markdown(\"**📊 Results:**\")\n                                df = pd.DataFrame(result['results'])\n                                st.dataframe(df, use_container_width=True)\n                                \n                                # Simple visualization\n                                if len(df.columns) >= 2:\n                                    numeric_cols = df.select_dtypes(include=['number']).columns\n                                    if len(numeric_cols) >= 1:\n                                        fig = px.bar(df.head(10), x=df.columns[0], y=numeric_cols[0])\n                                        st.plotly_chart(fig, use_container_width=True)\n                        else:\n                            st.error(f\"❌ Query failed: {error}\")\n            \n            with col2:\n                st.subheader(\"Data Schema\")\n                \n                schema_data, error = make_api_request(\"/schema\")\n                if schema_data and 'schemas' in schema_data:\n                    for schema in schema_data['schemas']:\n                        with st.expander(f\"📋 {schema['table_name']} ({schema['row_count']} rows)\"):\n                            st.write(f\"**File:** {schema['file_path']}\")\n                            st.write(f\"**Columns:** {len(schema['columns'])}\")\n                            \n                            # Column details\n                            for col in schema['columns'][:10]:  # Show first 10 columns\n                                interpreted = col.get('interpreted_name', col['name'])\n                                st.write(f\"• **{col['name']}** ({interpreted}): {col['data_type']}\")\n                                if col.get('description'):\n                                    st.write(f\"  _{col['description']}_\")\n        else:\n            st.info(\"📁 Please upload and process data files first to explore your data.\")\n    \n    with tab3:\n        st.header(\"💬 AI Chat Assistant\")\n        \n        # Chat interface\n        chat_container = st.container()\n        \n        # Display chat history\n        with chat_container:\n            for message in st.session_state.messages:\n                if message[\"role\"] == \"user\":\n                    st.markdown(f'<div class=\"chat-message user-message\">👤 **You:** {message[\"content\"]}</div>', unsafe_allow_html=True)\n                else:\n                    st.markdown(f'<div class=\"chat-message assistant-message\">🤖 **Assistant:** {message[\"content\"]}</div>', unsafe_allow_html=True)\n        \n        # Chat input\n        with st.container():\n            user_input = st.text_input(\n                \"Ask the AI assistant about your data:\",\n                placeholder=\"e.g., What's the current inventory status? Which products should we prioritize?\",\n                key=\"chat_input\"\n            )\n            \n            col1, col2, col3 = st.columns([1, 1, 4])\n            \n            with col1:\n                send_button = st.button(\"📤 Send\")\n            \n            with col2:\n                if st.button(\"🗑️ Clear Chat\"):\n                    st.session_state.messages = []\n                    st.experimental_rerun()\n        \n        if send_button and user_input:\n            # Add user message\n            st.session_state.messages.append({\"role\": \"user\", \"content\": user_input})\n            \n            # Get AI response\n            with st.spinner(\"🤖 AI is thinking...\"):\n                chat_data = {\"message\": user_input, \"include_context\": True}\n                response, error = make_api_request(\"/chat\", \"POST\", chat_data)\n                \n                if response:\n                    AI_response = response[\"response\"]\n                    st.session_state.messages.append({\"role\": \"assistant\", \"content\": ai_response})\n                else:\n                    error_msg = f\"❌ Sorry, I encountered an error: {error}\"\n                    st.session_state.messages.append({\"role\": \"assistant\", \"content\": error_msg})\n            \n            st.experimental_rerun()\n    \n    with tab4:\n        st.header(\"📊 Production Recommendations\")\n        \n        if st.session_state.system_status.get('tables_loaded', 0) > 0:\n            col1, col2 = st.columns([1, 2])\n            \n            with col1:\n                st.subheader(\"⚙️ Recommendation Settings\")\n                \n                planning_horizon = st.slider(\"Planning Horizon (days)\", 7, 365, 30)\n                max_recommendations = st.slider(\"Max Recommendations\", 5, 50, 20)\n                include_low_priority = st.checkbox(\"Include Low Priority Items\", False)\n                \n                if st.button(\"🎯 Generate Recommendations\"):\n                    with st.spinner(\"Analyzing data and generating recommendations...\"):\n                        rec_data = {\n                            \"planning_horizon_days\": planning_horizon,\n                            \"max_recommendations\": max_recommendations,\n                            \"include_low_priority\": include_low_priority\n                        }\n                        \n                        result, error = make_api_request(\"/recommend\", \"POST\", rec_data)\n                        \n                        if result:\n                            st.session_state.recommendations = result\n                            st.success(f\"✅ Generated {len(result['production_plan']['recommendations'])} recommendations!\")\n                        else:\n                            st.error(f\"❌ Failed to generate recommendations: {error}\")\n            \n            with col2:\n                if 'recommendations' in st.session_state:\n                    st.subheader(\"📋 Production Plan\")\n                    \n                    plan = st.session_state.recommendations['production_plan']\n                    \n                    # Executive summary\n                    if plan.get('executive_summary'):\n                        st.markdown(f\"**📝 Executive Summary:**\")\n                        st.info(plan['executive_summary'])\n                    \n                    # Priority distribution chart\n                    if plan['recommendations']:\n                        priority_counts = {}\n                        for rec in plan['recommendations']:\n                            priority = rec['priority']\n                            priority_counts[priority] = priority_counts.get(priority, 0) + 1\n                        \n                        fig = px.pie(\n                            values=list(priority_counts.values()),\n                            names=list(priority_counts.keys()),\n                            title=\"Recommendations by Priority\"\n                        )\n                        st.plotly_chart(fig, use_container_width=True)\n                        \n                        # Recommendations table  \n                        rec_df = pd.DataFrame(plan['recommendations'])\n                        st.dataframe(\n                            rec_df[['product_id', 'priority', 'recommended_quantity', 'current_inventory', 'shortage_amount']],\n                            use_container_width=True\n                        )\n                    \n                    # Key insights\n                    if plan.get('key_insights'):\n                        st.markdown(\"**💡 Key Insights:**\")\n                        for insight in plan['key_insights']:\n                            st.write(f\"• {insight}\")\n                else:\n                    st.info(\"👆 Configure settings and click 'Generate Recommendations' to see production planning insights.\")\n        else:\n            st.info(\"📁 Please upload and process data files first to get production recommendations.\")\n    \n    with tab5:\n        st.header(\"📈 Analytics Dashboard\")\n        \n        if st.session_state.system_status.get('tables_loaded', 0) > 0:\n            # System metrics\n            col1, col2, col3, col4 = st.columns(4)\n            \n            status = st.session_state.system_status\n            \n            with col1:\n                st.markdown(f\"\"\"\n                <div class=\"metric-container\">\n                    <h3>📊 Tables</h3>\n                    <h1>{status.get('tables_loaded', 0)}</h1>\n                </div>\n                \"\"\", unsafe_allow_html=True)\n            \n            with col2:\n                total_rows = status.get('data_summary', {}).get('total_rows', 0)\n                st.markdown(f\"\"\"\n                <div class=\"metric-container\">\n                    <h3>📋 Total Rows</h3>\n                    <h1>{total_rows:,}</h1>\n                </div>\n                \"\"\", unsafe_allow_html=True)\n            \n            with col3:\n                relationships = status.get('relationships', {}).get('total_relationships', 0)\n                st.markdown(f\"\"\"\n                <div class=\"metric-container\">\n                    <h3>🔗 Relationships</h3>\n                    <h1>{relationships}</h1>\n                </div>\n                \"\"\", unsafe_allow_html=True)\n            \n            with col4:\n                processing_time = st.session_state.get('recommendations', {}).get('processing_time_seconds', 0)\n                st.markdown(f\"\"\"\n                <div class=\"metric-container\">\n                    <h3>⚡ Response Time</h3>\n                    <h1>{processing_time:.2f}s</h1>\n                </div>\n                \"\"\", unsafe_allow_html=True)\n            \n            # Data quality indicators\n            if status.get('data_summary'):\n                st.subheader(\"📊 Data Overview\")\n                \n                summary = status['data_summary']\n                tables_info = summary.get('tables', [])\n                \n                if tables_info:\n                    df = pd.DataFrame(tables_info)\n                    \n                    # Table sizes chart\n                    fig = px.bar(df, x='name', y='rows', title=\"Rows by Table\")\n                    st.plotly_chart(fig, use_container_width=True)\n                    \n                    # Detailed table info\n                    st.dataframe(df, use_container_width=True)\n        else:\n            st.info(\"📁 Upload and process data to see analytics.\")\n    \n    # Footer\n    st.markdown(\"---\")\n    st.markdown(\n        \"<div style='text-align: center; color: #666;'>🏭 Manufacturing AI Assistant - Powered by AI & Data Science</div>\",\n        unsafe_allow_html=True\n    )\n\nif __name__ == \"__main__\":\n    main()