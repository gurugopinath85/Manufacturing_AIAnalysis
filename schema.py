"""
Schema interpretation service using LLM to understand column meanings.
"""
from typing import Dict, List, Any
from pydantic import BaseModel

from ..models.schema_models import TableSchema, ColumnInfo, DatabaseSchema
from ..core.llm import generate_structured_output
from ..utils.logging import get_logger, log_execution_time
from .ingestion import get_ingestion_service


logger = get_logger(__name__)


class ColumnInterpretation(BaseModel):
    """Schema for LLM output when interpreting column meanings."""
    column_name: str
    interpreted_name: str
    description: str
    business_meaning: str
    likely_values: List[str] = []
    data_quality_notes: str = ""


class TableInterpretation(BaseModel):
    """Schema for complete table interpretation."""
    table_name: str
    table_purpose: str
    columns: List[ColumnInterpretation]
    key_relationships: List[str] = []
    business_context: str = ""


class SchemaInterpretationService:
    """Service for interpreting schema meanings using LLM."""
    
    def __init__(self):
        self.ingestion_service = get_ingestion_service()
    
    def _prepare_column_context(self, column_info: ColumnInfo) -> Dict[str, Any]:
        """Prepare context about a column for LLM interpretation."""
        return {
            "name": column_info.name,
            "data_type": column_info.data_type,
            "nullable": column_info.nullable,
            "sample_values": column_info.sample_values[:10],  # Limit samples
            "unique_count": column_info.unique_count,
            "null_count": column_info.null_count
        }
    
    @log_execution_time
    def interpret_table_schema(self, table_name: str) -> TableInterpretation:
        """
        Interpret the meaning of a table and its columns using LLM.
        
        Args:
            table_name: Name of the table to interpret
            
        Returns:
            TableInterpretation with LLM-generated meanings
        """
        logger.info(f"Interpreting schema for table: {table_name}")
        
        # Get table schema
        schema = self.ingestion_service.get_table_schema(table_name)
        
        # Prepare context for LLM
        table_context = {
            "table_name": table_name,
            "row_count": schema.row_count,
            "columns": [self._prepare_column_context(col) for col in schema.columns]
        }
        
        # Create prompt for LLM
        prompt = f"""
Analyze this manufacturing/business data table and interpret the meaning of each column.

Table: {table_name}
Rows: {schema.row_count}

Columns with sample data:
"""
        
        for col in schema.columns:
            prompt += f"\n- {col.name} ({col.data_type}): {col.sample_values[:5]}"
        
        prompt += """

For each column, provide:
1. A clear, human-readable name
2. A detailed description of what the column contains
3. The business meaning/purpose in a manufacturing context
4. Any data quality observations

Also identify:
- The overall purpose of this table
- Potential key columns for relationships
- Business context (inventory, demand, production, etc.)
"""
        
        system_prompt = """You are an expert in manufacturing data analysis and business intelligence. 
Analyze data schemas and provide clear, actionable interpretations for business users.
Focus on manufacturing concepts like inventory, demand, production, supply chain, etc."""
        
        try:
            # Get interpretation from LLM
            interpretation = generate_structured_output(
                prompt=prompt,
                schema=TableInterpretation,
                system_prompt=system_prompt
            )
            
            result = TableInterpretation(**interpretation)
            logger.info(f"Successfully interpreted schema for table: {table_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to interpret schema for table {table_name}: {str(e)}")
            # Return minimal interpretation as fallback
            return TableInterpretation(
                table_name=table_name,
                table_purpose="Data table requiring manual review",
                columns=[
                    ColumnInterpretation(
                        column_name=col.name,
                        interpreted_name=col.name.replace("_", " ").title(),
                        description=f"Column containing {col.data_type} data",
                        business_meaning="Requires manual interpretation"
                    ) for col in schema.columns
                ],
                business_context="Unknown - requires domain expert review"
            )
    
    @log_execution_time
    def interpret_all_schemas(self) -> Dict[str, TableInterpretation]:
        """
        Interpret all loaded table schemas.
        
        Returns:
            Dictionary mapping table names to their interpretations
        """
        interpretations = {}
        table_names = self.ingestion_service.list_tables()
        
        logger.info(f"Interpreting schemas for {len(table_names)} tables")
        
        for table_name in table_names:
            try:
                interpretation = self.interpret_table_schema(table_name)
                interpretations[table_name] = interpretation
            except Exception as e:
                logger.error(f"Failed to interpret table {table_name}: {str(e)}")
                continue
        
        logger.info(f"Successfully interpreted {len(interpretations)} out of {len(table_names)} tables")
        return interpretations
    
    def update_schema_with_interpretation(
        self, 
        table_name: str, 
        interpretation: TableInterpretation
    ) -> TableSchema:
        """
        Update a TableSchema with LLM interpretation results.
        
        Args:
            table_name: Name of the table
            interpretation: LLM interpretation results
            
        Returns:
            Updated TableSchema with interpretation data
        """
        # Get original schema
        original_schema = self.ingestion_service.get_table_schema(table_name)
        
        # Create updated columns with interpretation
        updated_columns = []
        for original_col in original_schema.columns:
            # Find matching interpretation
            interpretation_col = next(
                (col for col in interpretation.columns if col.column_name == original_col.name),
                None
            )
            
            if interpretation_col:
                # Update with interpretation
                updated_col = ColumnInfo(
                    name=original_col.name,
                    data_type=original_col.data_type,
                    nullable=original_col.nullable,
                    sample_values=original_col.sample_values,
                    unique_count=original_col.unique_count,
                    null_count=original_col.null_count,
                    interpreted_name=interpretation_col.interpreted_name,
                    description=interpretation_col.description,
                    business_meaning=interpretation_col.business_meaning
                )
            else:
                # Keep original if no interpretation found
                updated_col = original_col
            
            updated_columns.append(updated_col)
        
        # Create updated schema
        updated_schema = TableSchema(
            table_name=original_schema.table_name,
            file_path=original_schema.file_path,
            columns=updated_columns,
            row_count=original_schema.row_count,
            file_size_bytes=original_schema.file_size_bytes,
            created_at=original_schema.created_at,
            last_modified=original_schema.last_modified
        )
        
        # Update in ingestion service
        self.ingestion_service.table_schemas[table_name] = updated_schema
        
        return updated_schema
    
    def create_enhanced_database_schema(self) -> DatabaseSchema:
        """
        Create a complete DatabaseSchema with LLM interpretations.
        
        Returns:
            DatabaseSchema with interpreted column meanings
        """
        # Get all interpretations
        interpretations = self.interpret_all_schemas()
        
        # Update all schemas with interpretations
        enhanced_schemas = []
        for table_name, interpretation in interpretations.items():
            try:
                enhanced_schema = self.update_schema_with_interpretation(table_name, interpretation)
                enhanced_schemas.append(enhanced_schema)
            except Exception as e:
                logger.error(f"Failed to enhance schema for {table_name}: {str(e)}")
                # Use original schema as fallback
                original_schema = self.ingestion_service.get_table_schema(table_name)
                enhanced_schemas.append(original_schema)
        
        # Create database schema (relationships will be added by relationship service)
        database_schema = DatabaseSchema(
            tables=enhanced_schemas,
            relationships=[],  # Will be populated by relationship detection
            generated_at=__import__('datetime').datetime.now().isoformat()
        )
        
        return database_schema
    
    def get_business_glossary(self) -> Dict[str, str]:
        """
        Generate a business glossary of all interpreted terms.
        
        Returns:
            Dictionary mapping technical column names to business meanings
        """
        glossary = {}
        table_names = self.ingestion_service.list_tables()
        
        for table_name in table_names:
            try:
                interpretation = self.interpret_table_schema(table_name)
                for col in interpretation.columns:
                    key = f"{table_name}.{col.column_name}"
                    glossary[key] = {
                        'interpreted_name': col.interpreted_name,
                        'description': col.description,
                        'business_meaning': col.business_meaning
                    }
            except Exception as e:
                logger.error(f"Failed to add {table_name} to glossary: {str(e)}")
                continue
        
        return glossary


# Global service instance
_schema_service = None


def get_schema_service() -> SchemaInterpretationService:
    """Get the global schema interpretation service instance."""
    global _schema_service
    if _schema_service is None:
        _schema_service = SchemaInterpretationService()
    return _schema_service