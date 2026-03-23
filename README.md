# Manufacturing AI Analysis

AI-powered manufacturing decision assistant that helps optimize production planning through automated data analysis and intelligent recommendations.

## 🚀 Features

- **Data Ingestion**: Upload and process CSV/Excel files
- **Schema Interpretation**: AI-powered understanding of data structure and column meanings
- **Relationship Detection**: Automatic discovery of relationships between tables
- **Natural Language Queries**: Ask questions about your data in plain English
- **Production Recommendations**: Smart manufacturing decisions based on inventory, demand, and capacity
- **Chat Interface**: Conversational data interaction
- **Modern UI**: Clean Streamlit interface with analytics dashboard

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Data Processing**: Pandas, NumPy
- **AI/LLM**: OpenAI GPT-4 or Anthropic Claude
- **UI**: Streamlit with Plotly visualizations
- **Data Models**: Pydantic for validation
- **Optional**: OR-Tools for optimization, SQLite for persistence

## 📋 Quick Start

### 1. Environment Setup

```bash
# Clone and navigate to project
cd Manufacturing_AIAnalysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# Required: At least one LLM API key
OPENAI_API_KEY=your_openai_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional settings
DEFAULT_LLM_PROVIDER=openai  # or "anthropic"
DEBUG=false
MAX_FILE_SIZE_MB=100
```

### 3. Run the Application

**Start the FastAPI backend:**
```bash
cd app
python main.py
# Or with uvicorn: uvicorn main:app --reload
```

**Start the Streamlit UI (in a new terminal):**
```bash
streamlit run streamlit_app.py
```

### 4. Access the Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **API Endpoints**: http://localhost:8000/api/v1/

## 📊 Usage Workflow

1. **Upload Data**: Use the Streamlit interface to upload CSV/Excel files
2. **Process Schema**: Let AI interpret your data structure and column meanings
3. **Explore Data**: Ask natural language questions about your data
4. **Get Recommendations**: Generate intelligent production planning recommendations
5. **Chat Interface**: Interactive conversation with your manufacturing data

## 🔧 API Endpoints

- `POST /api/v1/upload` - Upload data files
- `POST /api/v1/schema/extract` - Extract and interpret schema
- `GET /api/v1/schema` - Get current schema information
- `POST /api/v1/query` - Execute natural language queries
- `POST /api/v1/recommend` - Generate production recommendations
- `POST /api/v1/chat` - Chat interface
- `GET /api/v1/status` - System status and metrics

## 💡 Example Use Cases

- **Inventory Management**: "Which products are running low in inventory?"
- **Production Planning**: "What should we manufacture next based on demand?"
- **Supply Chain**: "Which items have long lead times and need early ordering?"
- **Analytics**: "Show me the top 10 products by demand volume"

## 🏗️ Architecture

```
app/
├── main.py                 # FastAPI application entry point
├── api/
│   └── routes.py          # API endpoints
├── core/
│   ├── config.py          # Configuration management
│   └── llm.py            # LLM integration
├── services/
│   ├── ingestion.py       # Data loading and processing
│   ├── schema.py          # AI schema interpretation
│   ├── relationships.py   # Relationship detection
│   ├── query_engine.py    # Natural language queries
│   └── decision_engine.py # Production recommendations
├── models/
│   ├── schema_models.py   # Data structure models
│   └── decision_models.py # Recommendation models
├── utils/
│   ├── file_utils.py      # File operations
│   └── logging.py         # Logging utilities
└── data/
    └── uploads/           # Uploaded files storage
```

## 🤖 AI Integration

The system uses Large Language Models (LLMs) for:

- **Schema Interpretation**: Understanding column meanings and business context
- **Query Generation**: Converting natural language to pandas operations
- **Explanation Generation**: Creating human-readable explanations of results
- **Relationship Detection**: Identifying connections between data tables

## 🔒 Security & Configuration

- File upload validation and sanitization
- Safe code execution environment for queries
- Environment-based configuration
- API key management through environment variables

## 📈 Future Enhancements

- OR-Tools integration for advanced optimization
- Real-time data streaming
- Advanced forecasting models
- Multi-tenant support
- Graph database integration for complex relationships
- Automated report generation

## 🐛 Troubleshooting

**API Connection Issues:**
- Ensure FastAPI server is running on port 8000
- Check that your LLM API keys are properly configured

**File Upload Problems:**
- Verify file format (CSV, XLSX, XLS)
- Check file size limits in configuration
- Ensure proper column headers in data files

**Query Failures:**
- Verify data has been uploaded and processed
- Check that schema extraction was successful
- Review query syntax or try simpler questions

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

**Built with ❤️ for modern manufacturing data analysis**