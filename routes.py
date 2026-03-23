"""
API routes for Manufacturing AI Analysis System.
"""

import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from ..models.schema_models import FileUploadResponse, SchemaExtractionRequest, SchemaExtractionResponse
from ..models.schema_models import QueryRequest, QueryResult
from ..models.decision_models import RecommendationRequest, RecommendationResponse
from ..models.schema_models import ChatMessage, ChatResponse
from ..utils.file_utils import save_uploaded_file, list_uploaded_files
from ..utils.logging import get_logger, log_api_request
from ..core.dependencies import (
    get_ingestion_service,
    get_schema_service,
    get_relationship_service,
    get_query_engine_service,
    get_decision_engine_service
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload CSV/Excel files for analysis."""
    log_api_request("/upload", "POST")
    
    try:
        uploaded_files = []
        file_sizes = {}
        
        for file in files:
            # Read file content
            content = await file.read()
            
            # Save file
            file_path, file_size = save_uploaded_file(content, file.filename)
            
            uploaded_files.append(file.filename)
            file_sizes[file.filename] = file_size
            
            logger.info(f"Uploaded file: {file.filename} ({file_size} bytes)")
        
        return FileUploadResponse(
            uploaded_files=uploaded_files,
            file_sizes=file_sizes
        )
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files")
async def list_files():
    """List all uploaded files."""
    log_api_request("/files", "GET")
    
    try:
        files = list_uploaded_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema/extract", response_model=SchemaExtractionResponse)
async def extract_schema(request: SchemaExtractionRequest, background_tasks: BackgroundTasks):
    """Extract and interpret schema from uploaded files."""
    log_api_request("/schema/extract", "POST", request.dict())
    
    try:
        start_time = time.time()
        
        # Get services
        ingestion_service = get_ingestion_service()
        schema_service = get_schema_service()
        relationship_service = get_relationship_service()
        
        # Load files
        if request.file_names:
            # Load specific files
            uploaded_files = list_uploaded_files()
            file_paths = []
            for file_info in uploaded_files:
                if file_info['name'] in request.file_names:
                    file_paths.append(file_info['path'])
            
            if not file_paths:
                raise HTTPException(status_code=404, detail="Specified files not found")
                
            schemas = ingestion_service.load_all_files(file_paths)
        else:
            # Load all files
            schemas = ingestion_service.load_all_files()
        
        if not schemas:
            raise HTTPException(status_code=400, detail="No valid files found to process")
        
        # Create enhanced database schema with interpretations and relationships
        database_schema = schema_service.create_enhanced_database_schema()
        enhanced_schema = relationship_service.enhance_database_schema(database_schema)
        
        processing_time = time.time() - start_time
        processed_files = [schema.table_name for schema in schemas]
        
        return SchemaExtractionResponse(
            processed_files=processed_files,
            schema=enhanced_schema,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Schema extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_current_schema():
    """Get the current database schema."""
    log_api_request("/schema", "GET")
    
    try:
        ingestion_service = get_ingestion_service()
        schemas = ingestion_service.get_all_schemas()
        
        if not schemas:
            return {"message": "No schema available. Upload and process files first."}
        
        return {
            "tables": len(schemas),
            "schemas": [schema.dict() for schema in schemas]
        }
        
    except Exception as e:
        logger.error(f"Failed to get schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResult)
async def execute_query(request: QueryRequest):
    """Execute a natural language query."""
    log_api_request("/query", "POST", {"question": request.question})
    
    try:
        query_engine = get_query_engine_service()
        result = query_engine.process_query(request)
        return result
        
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/suggestions")
async def get_query_suggestions():
    """Get suggested queries based on available data."""
    log_api_request("/query/suggestions", "GET")
    
    try:
        query_engine = get_query_engine_service()
        suggestions = query_engine.suggest_queries()
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Failed to get query suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Generate production recommendations."""
    log_api_request("/recommend", "POST", request.dict())
    
    try:
        start_time = time.time()
        
        decision_engine = get_decision_engine_service()
        production_plan = decision_engine.generate_recommendations(request)
        
        processing_time = time.time() - start_time
        
        return RecommendationResponse(
            production_plan=production_plan,
            processing_time_seconds=processing_time,
            request_parameters=request
        )
        
    except Exception as e:
        logger.error(f"Recommendation generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_interface(message: ChatMessage):
    """Chat interface for natural language interaction."""
    log_api_request("/chat", "POST", {"message": message.message})
    
    try:
        # Determine if this is a query or general question
        query_keywords = ['show', 'list', 'find', 'what', 'which', 'how many', 'analyze']
        is_query = any(keyword in message.message.lower() for keyword in query_keywords)
        
        if is_query:
            # Process as a data query
            query_engine = get_query_engine_service()
            query_request = QueryRequest(
                question=message.message,
                include_explanation=True
            )
            
            result = query_engine.process_query(query_request)
            
            if result.success:
                response_text = f"I found the following information:\n\n"
                if result.explanation:
                    response_text += result.explanation
                
                if result.results:
                    response_text += f"\n\nResults: {len(result.results)} items found."
                
                return ChatResponse(
                    response=response_text,
                    query_executed=True,
                    results_included=bool(result.results)
                )
            else:
                return ChatResponse(
                    response=f"I encountered an error processing your query: {result.error_message}",
                    query_executed=False
                )
        else:
            # Handle as general conversation
            from ..core.llm import generate_response
            
            # Get context about available data
            ingestion_service = get_ingestion_service()
            tables = ingestion_service.list_tables()
            
            context_prompt = f"""
You are an AI assistant for manufacturing data analysis.

Available data tables: {tables if tables else 'No data loaded yet'}

User message: {message.message}

Provide a helpful response. If the user needs data analysis, suggest specific queries they could ask.
If no data is loaded, guide them to upload CSV/Excel files first.
"""
            
            response_text = generate_response(
                prompt=context_prompt,
                system_prompt="You are a helpful manufacturing data analysis assistant."
            )
            
            return ChatResponse(
                response=response_text,
                query_executed=False
            )
        
    except Exception as e:
        logger.error(f"Chat interface error: {str(e)}")
        return ChatResponse(
            response="I apologize, but I encountered an error processing your message. Please try again or contact support.",
            query_executed=False
        )


@router.get("/status")
async def get_status():
    """Get system status and statistics."""
    log_api_request("/status", "GET")
    
    try:
        ingestion_service = get_ingestion_service()
        
        # Get basic stats
        tables = ingestion_service.list_tables()
        summary = ingestion_service.get_table_summary() if tables else None
        
        # Get relationship stats
        relationship_service = get_relationship_service()
        relationship_summary = relationship_service.get_relationship_summary() if tables else {}
        
        return {
            "system_status": "operational",
            "tables_loaded": len(tables),
            "table_names": tables,
            "data_summary": summary,
            "relationships": relationship_summary,
            "services_available": {
                "ingestion": True,
                "schema_interpretation": True,
                "relationship_detection": True,
                "query_engine": True,
                "decision_engine": True
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}