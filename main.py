"""
Main FastAPI application for Manufacturing AI Analysis.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import get_settings, validate_api_keys
from app.utils.logging import init_logging
from app.api.routes import router

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
    """Root endpoint with API information."""
    return {
        "message": "Manufacturing AI Analysis API",
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
        "api_prefix": "/api/v1"
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.app_title} v{settings.app_version}")
    
    try:
        # Validate API keys
        validate_api_keys()
        logger.info("API keys validated successfully")
        
        # Initialize upload directory
        from app.utils.file_utils import ensure_upload_directory
        upload_dir = ensure_upload_directory()
        logger.info(f"Upload directory ready: {upload_dir}")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        # Don't prevent startup, but log the warning
        logger.warning("Application started with configuration warnings")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Manufacturing AI Analysis API")
    
    # Clean up resources if needed
    try:
        from services.ingestion import get_ingestion_service
        ingestion_service = get_ingestion_service()
        ingestion_service.clear_data()
        logger.info("Cleaned up data services")
    except Exception as e:
        logger.warning(f"Cleanup warning: {str(e)}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please check the logs or contact support.",
            "type": type(exc).__name__
        }
    )


# Development server function
def run_dev_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the development server."""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info" if not settings.debug else "debug"
    )


if __name__ == "__main__":
    run_dev_server()