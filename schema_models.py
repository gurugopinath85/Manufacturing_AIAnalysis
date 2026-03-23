"""
Pydantic models for schema representation and data structures.
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class DataType(str, Enum):
    """Supported data types."""
    STRING = "string"
    INTEGER = "integer" 
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    UNKNOWN = "unknown"


class ColumnInfo(BaseModel):
    """Information about a single column."""
    name: str
    data_type: DataType
    nullable: bool = True
    sample_values: List[Any] = Field(default_factory=list)
    unique_count: Optional[int] = None
    null_count: Optional[int] = None
    
    # LLM-interpreted meaning
    interpreted_name: Optional[str] = None
    description: Optional[str] = None
    business_meaning: Optional[str] = None


class TableSchema(BaseModel):
    """Schema information for a table/file."""
    table_name: str
    file_path: str
    columns: List[ColumnInfo]
    row_count: int
    file_size_bytes: int
    
    # Metadata
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    
    class Config:
        json_encoders = {
            # Handle any special serialization if needed
        }


class RelationshipType(str, Enum):
    """Types of relationships between tables."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
    UNKNOWN = "unknown"


class TableRelationship(BaseModel):
    """Relationship between two tables."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: RelationshipType = RelationshipType.UNKNOWN
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    join_sample_quality: Optional[float] = None  # Quality of sample join results


class DatabaseSchema(BaseModel):
    """Complete schema information for all tables."""
    tables: List[TableSchema]
    relationships: List[TableRelationship]
    schema_version: str = "1.0"
    generated_at: Optional[str] = None
    
    def get_table_by_name(self, table_name: str) -> Optional[TableSchema]:
        """Get a table schema by name."""
        for table in self.tables:
            if table.table_name == table_name:
                return table
        return None
    
    def get_relationships_for_table(self, table_name: str) -> List[TableRelationship]:
        """Get all relationships involving a specific table."""
        return [
            rel for rel in self.relationships 
            if rel.source_table == table_name or rel.target_table == table_name
        ]


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    uploaded_files: List[str]
    file_sizes: Dict[str, int]
    success: bool = True
    message: str = "Files uploaded successfully"


class SchemaExtractionRequest(BaseModel):
    """Request to extract schema from uploaded files."""
    file_names: Optional[List[str]] = None  # If None, process all files
    force_reprocess: bool = False


class SchemaExtractionResponse(BaseModel):
    """Response from schema extraction."""
    processed_files: List[str]
    schema: DatabaseSchema
    processing_time_seconds: float
    success: bool = True
    message: str = "Schema extraction completed"


class QueryRequest(BaseModel):
    """Natural language query request."""
    question: str
    target_tables: Optional[List[str]] = None
    include_explanation: bool = True


class QueryResult(BaseModel):
    """Result from executing a query."""
    question: str
    generated_code: str
    results: List[Dict[str, Any]]
    explanation: Optional[str] = None
    execution_time_seconds: float
    success: bool = True
    error_message: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message for conversational interface."""
    message: str
    include_context: bool = True


class ChatResponse(BaseModel):
    """Response from chat interface."""
    response: str
    query_executed: Optional[bool] = None
    results_included: Optional[bool] = None