"""
Main FastAPI application for Manufacturing AI Analysis.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from core.config import get_settings, validate_api_keys
from utils.logging import init_logging
from api.routes import router

# Initialize logging
logger = init_logging()

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="""
    AI-powered manufacturing decision assistant that helps optimize production planning 
    through automated data analysis and intelligent recommendations.
    
    ## Features
    
    * **Data Ingestion**: Upload and process CSV/Excel files
    * **Schema Interpretation**: AI-powered understanding of data structure
    * **Relationship Detection**: Automatic discovery of table relationships  
    * **Natural Language Queries**: Ask questions in plain English
    * **Production Recommendations**: Smart manufacturing decisions
    * **Chat Interface**: Conversational data interaction
    
    ## Getting Started
    
    1. Upload your manufacturing data files via `/upload`
    2. Process the schema with `/schema/extract`
    3. Ask questions via `/query` or `/chat`
    4. Get production recommendations via `/recommend`
    """,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    \"\"\"Root endpoint with API information.\"\"\"\n    return {\n        \"message\": \"Manufacturing AI Analysis API\",\n        \"version\": settings.app_version,\n        \"status\": \"operational\",\n        \"docs\": \"/docs\",\n        \"api_prefix\": \"/api/v1\"\n    }\n\n\n@app.on_event(\"startup\")\nasync def startup_event():\n    \"\"\"Application startup event.\"\"\"\n    logger.info(f\"Starting {settings.app_title} v{settings.app_version}\")\n    \n    try:\n        # Validate API keys\n        validate_api_keys()\n        logger.info(\"API keys validated successfully\")\n        \n        # Initialize upload directory\n        from utils.file_utils import ensure_upload_directory\n        upload_dir = ensure_upload_directory()\n        logger.info(f\"Upload directory ready: {upload_dir}\")\n        \n        logger.info(\"Application startup completed successfully\")\n        \n    except Exception as e:\n        logger.error(f\"Startup failed: {str(e)}\")\n        # Don't prevent startup, but log the warning\n        logger.warning(\"Application started with configuration warnings\")\n\n\n@app.on_event(\"shutdown\")\nasync def shutdown_event():\n    \"\"\"Application shutdown event.\"\"\"\n    logger.info(\"Shutting down Manufacturing AI Analysis API\")\n    \n    # Clean up resources if needed\n    try:\n        from services.ingestion import get_ingestion_service\n        ingestion_service = get_ingestion_service()\n        ingestion_service.clear_data()\n        logger.info(\"Cleaned up data services\")\n    except Exception as e:\n        logger.warning(f\"Cleanup warning: {str(e)}\")\n\n\n# Global exception handler\n@app.exception_handler(Exception)\nasync def global_exception_handler(request, exc):\n    \"\"\"Global exception handler for unhandled errors.\"\"\"\n    logger.error(f\"Unhandled exception: {str(exc)}\", exc_info=True)\n    \n    return JSONResponse(\n        status_code=500,\n        content={\n            \"error\": \"Internal server error\",\n            \"message\": \"An unexpected error occurred. Please check the logs or contact support.\",\n            \"type\": type(exc).__name__\n        }\n    )\n\n\n# Development server function\ndef run_dev_server(host: str = \"0.0.0.0\", port: int = 8000):\n    \"\"\"Run the development server.\"\"\"\n    uvicorn.run(\n        \"app.main:app\",\n        host=host,\n        port=port,\n        reload=True,\n        log_level=\"info\" if not settings.debug else \"debug\"\n    )\n\n\nif __name__ == \"__main__\":\n    run_dev_server()