"""
Manufacturing AI Analysis - Streamlit Web Interface
"""
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from typing import Optional, Tuple, Any


# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"


def make_api_request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Tuple[Optional[dict], Optional[str]]:
    """Make request to the FastAPI backend."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            return None, f"Unsupported method: {method}"
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API Error: {response.status_code} - {response.text}"
    
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to API server. Please ensure the backend is running."
    except Exception as e:
        return None, f"Request failed: {str(e)}"


def upload_files_to_api(files) -> Optional[dict]:
    """Upload files to the API."""
    try:
        files_data = []
        for file in files:
            files_data.append(('files', (file.name, file.getvalue(), file.type)))
        
        url = f"{API_BASE_URL}/upload"
        response = requests.post(url, files=files_data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return None


def get_system_status():
    """Get and cache system status."""
    status, error = make_api_request("/status")
    if status:
        st.session_state.system_status = status
    return status, error


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Manufacturing AI Analysis",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1e88e5;
        text-align: center;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        border-left: 4px solid #1e88e5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'system_status' not in st.session_state:
        st.session_state.system_status = {}
    
    # Header
    st.markdown('<h1 class="main-header">🏭 Manufacturing AI Analysis</h1>', unsafe_allow_html=True)
    st.markdown("**AI-powered manufacturing decision assistant for optimized production planning**")
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # System status
        status, error = get_system_status()
        if status:
            st.success("✅ System Online")
            st.write(f"Tables loaded: {status.get('tables_loaded', 0)}")
            if status.get('table_names'):
                st.write("Available tables:")
                for table in status['table_names']:
                    st.write(f"  • {table}")
        else:
            st.error("❌ System Offline")
            st.write(f"Error: {error}")
        
        st.markdown("---")
        
        # Quick actions
        if st.button("🔄 Refresh Status"):
            get_system_status()
            st.experimental_rerun()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Upload & Process", "🔍 Explore Data", "💬 AI Chat", "📊 Recommendations"])
    
    with tab1:
        st.header("📁 Data Upload & Processing")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Upload Files")
            uploaded_files = st.file_uploader(
                "Choose CSV or Excel files",
                accept_multiple_files=True,
                type=['csv', 'xlsx', 'xls']
            )
            
            if uploaded_files:
                st.write(f"Selected {len(uploaded_files)} files:")
                for file in uploaded_files:
                    st.write(f"  • {file.name} ({file.size} bytes)")
                
                if st.button("📤 Upload Files"):
                    with st.spinner("Uploading files..."):
                        result = upload_files_to_api(uploaded_files)
                        if result:
                            st.success(f"✅ Uploaded {len(result['uploaded_files'])} files successfully!")
                            get_system_status()  # Refresh status
        
        with col2:
            st.subheader("Processing Options")
            
            if st.button("🔍 Extract Schema"):
                with st.spinner("Analyzing data structure..."):
                    schema_result, error = make_api_request("/schema/extract", "POST", {})
                    if schema_result:
                        st.success(f"✅ Processed {len(schema_result.get('processed_files', []))} files")
                        get_system_status()
                    else:
                        st.error(f"Schema extraction failed: {error}")
    
    with tab2:
        st.header("🔍 Data Exploration")
        
        if st.session_state.system_status.get('tables_loaded', 0) > 0:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Natural Language Queries")
                
                custom_query = st.text_input(
                    "Enter your question:",
                    placeholder="e.g., Which products have low inventory?"
                )
                
                if st.button("🚀 Execute Query") and custom_query:
                    with st.spinner("Processing query..."):
                        query_data = {"question": custom_query, "include_explanation": True}
                        result, error = make_api_request("/query", "POST", query_data)
                        if result:
                            st.success("✅ Query completed!")
                            
                            if result.get('explanation'):
                                st.markdown("**📝 Explanation:**")
                                st.write(result['explanation'])
                            
                            if result.get('results'):
                                st.markdown("**📊 Results:**")
                                df = pd.DataFrame(result['results'])
                                st.dataframe(df, use_container_width=True)
                        else:
                            st.error(f"❌ Query failed: {error}")
            
            with col2:
                st.subheader("Data Schema")
                
                schema_data, error = make_api_request("/schema")
                if schema_data and 'schemas' in schema_data:
                    for schema in schema_data['schemas']:
                        with st.expander(f"📋 {schema['table_name']} ({schema['row_count']} rows)"):
                            st.write(f"**File:** {schema['file_path']}")
                            st.write(f"**Columns:** {len(schema['columns'])}")
        else:
            st.info("📁 Please upload and process data files first to explore your data.")
    
    with tab3:
        st.header("💬 AI Chat Assistant")
        
        # Display chat history
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'**👤 You:** {message["content"]}')
            else:
                st.markdown(f'**🤖 Assistant:** {message["content"]}')
        
        # Chat input
        user_input = st.text_input(
            "Ask the AI assistant about your data:",
            placeholder="e.g., What's the current inventory status? Which products should we prioritize?",
            key="chat_input"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            send_button = st.button("📤 Send")
        
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.experimental_rerun()
        
        if send_button and user_input:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get AI response
            with st.spinner("🤖 AI is thinking..."):
                chat_data = {"message": user_input}
                response, error = make_api_request("/chat", "POST", chat_data)
                
                if response:
                    ai_response = response.get("response", "No response received")
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                else:
                    error_msg = f"❌ Sorry, I encountered an error: {error}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            st.experimental_rerun()
    
    with tab4:
        st.header("📊 Production Recommendations")
        
        if st.session_state.system_status.get('tables_loaded', 0) > 0:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("⚙️ Settings")
                
                planning_horizon = st.slider("Planning Horizon (days)", 7, 365, 30)
                max_recommendations = st.slider("Max Recommendations", 5, 50, 20)
                include_low_priority = st.checkbox("Include Low Priority Items", False)
                
                if st.button("🎯 Generate Recommendations"):
                    with st.spinner("Generating recommendations..."):
                        rec_data = {
                            "planning_horizon_days": planning_horizon,
                            "max_recommendations": max_recommendations,
                            "include_low_priority": include_low_priority
                        }
                        
                        result, error = make_api_request("/recommend", "POST", rec_data)
                        
                        if result:
                            st.session_state.recommendations = result
                            plan = result.get('production_plan', {})
                            recommendations = plan.get('recommendations', [])
                            st.success(f"✅ Generated {len(recommendations)} recommendations!")
                        else:
                            st.error(f"❌ Failed to generate recommendations: {error}")
            
            with col2:
                if 'recommendations' in st.session_state:
                    st.subheader("📋 Production Plan")
                    
                    plan = st.session_state.recommendations.get('production_plan', {})
                    
                    # Executive summary
                    if plan.get('executive_summary'):
                        st.markdown("**📝 Executive Summary:**")
                        st.info(plan['executive_summary'])
                    
                    # Recommendations table
                    recommendations = plan.get('recommendations', [])
                    if recommendations:
                        rec_df = pd.DataFrame(recommendations)
                        selected_cols = ['product_id', 'priority', 'recommended_quantity', 'current_inventory']
                        available_cols = [col for col in selected_cols if col in rec_df.columns]
                        
                        if available_cols:
                            st.dataframe(rec_df[available_cols], use_container_width=True)
                    
                    # Key insights
                    if plan.get('key_insights'):
                        st.markdown("**💡 Key Insights:**")
                        for insight in plan['key_insights']:
                            st.write(f"• {insight}")
                else:
                    st.info("👆 Configure settings and click 'Generate Recommendations' to see production planning insights.")
        else:
            st.info("📁 Please upload and process data files first to get production recommendations.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>🏭 Manufacturing AI Assistant - Powered by AI & Data Science</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()