"""
Natural language query engine for converting questions to pandas operations.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import re
from pydantic import BaseModel

from ..models.schema_models import QueryRequest, QueryResult
from ..core.llm import generate_structured_output, generate_response
from ..utils.logging import get_logger, log_execution_time
from .ingestion import get_ingestion_service
from .schema import get_schema_service


logger = get_logger(__name__)


class PandasQuery(BaseModel):
    """Schema for LLM-generated pandas query."""
    code: str
    explanation: str
    tables_used: List[str]
    assumptions: List[str] = []


class QueryEngineService:
    """Service for processing natural language queries."""
    
    def __init__(self):
        self.ingestion_service = get_ingestion_service()
        self.schema_service = get_schema_service()
    
    def _get_table_context(self, table_names: Optional[List[str]] = None) -> str:
        """Generate context about available tables for the LLM."""
        if table_names is None:
            table_names = self.ingestion_service.list_tables()
        
        context = "Available tables and their schemas:\n\n"
        
        for table_name in table_names:
            try:
                schema = self.ingestion_service.get_table_schema(table_name)
                context += f"Table: {table_name}\n"
                context += f"Rows: {schema.row_count}\n"
                context += "Columns:\n"
                
                for col in schema.columns[:10]:  # Limit to first 10 columns
                    interpreted = col.interpreted_name or col.name
                    description = col.description or "No description"
                    sample_values = col.sample_values[:3] if col.sample_values else []
                    
                    context += f"  - {col.name} ({interpreted}): {col.data_type}"
                    if sample_values:
                        context += f" | Examples: {sample_values}"
                    context += f" | {description}\n"
                
                context += "\n"
                
            except Exception as e:
                logger.warning(f"Could not get context for table {table_name}: {str(e)}")
                continue
        
        return context
    
    def _create_safe_execution_environment(self) -> Dict[str, Any]:
        """Create a safe environment for code execution."""
        # Load all tables into the environment
        env = {'pd': pd}
        
        for table_name in self.ingestion_service.list_tables():
            try:
                df = self.ingestion_service.get_table(table_name)
                env[table_name] = df
            except Exception as e:
                logger.error(f"Failed to load table {table_name} into environment: {str(e)}")
        
        return env
    
    def _execute_pandas_code(self, code: str) -> Any:
        """Safely execute pandas code and return results."""
        # Create safe environment
        env = self._create_safe_execution_environment()
        
        # Security check - prevent dangerous operations
        dangerous_patterns = [
            r'import\s+os', r'import\s+sys', r'__import__',
            r'open\s*\(', r'file\s*\(', r'exec\s*\(', r'eval\s*\(',
            r'subprocess', r'os\.', r'sys\.'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous code detected: {pattern}")
        
        try:
            # Execute the code
            exec(code, env)
            
            # Look for a result variable or the last expression
            if 'result' in env:
                return env['result']
            
            # If no result variable, try to find a DataFrame in the environment
            for key, value in env.items():
                if isinstance(value, pd.DataFrame) and key not in self.ingestion_service.list_tables():
                    return value
            
            # If still no result, return None
            return None
            
        except Exception as e:
            logger.error(f"Error executing pandas code: {str(e)}")
            raise ValueError(f"Code execution failed: {str(e)}")
    
    @log_execution_time
    def process_query(self, query_request: QueryRequest) -> QueryResult:
        """Process a natural language query."""
        logger.info(f"Processing query: {query_request.question}")
        
        try:
            # Get table context
            table_context = self._get_table_context(query_request.target_tables)
            
            # Create prompt for LLM
            prompt = f"""
You are a data analyst. Convert this natural language question into pandas code.

{table_context}

Question: {query_request.question}

Generate pandas code that:
1. Uses the available tables (already loaded as DataFrames)
2. Answers the question accurately
3. Stores the final result in a variable called 'result'
4. Returns data in a format suitable for display (limited rows if needed)

Important:
- Table names are already loaded as DataFrame variables
- Use .head() or .tail() to limit large results
- Handle missing data appropriately
- Include appropriate sorting/filtering

Example format:
```python
# Filter and analyze data
filtered_data = inventory[inventory['quantity'] < 100]
result = filtered_data.groupby('product_id')['quantity'].sum().sort_values(ascending=False).head(10)
```
"""
            
            system_prompt = """
You are an expert data analyst specializing in manufacturing and business data. 
Generate clean, efficient pandas code that answers business questions accurately.
Always include explanations and highlight any assumptions made.
"""
            
            # Generate pandas query
            llm_response = generate_structured_output(
                prompt=prompt,
                schema=PandasQuery,
                system_prompt=system_prompt
            )
            
            pandas_query = PandasQuery(**llm_response)
            logger.info(f"Generated pandas code for query")
            
            # Execute the code
            import time
            start_time = time.time()
            
            result_data = self._execute_pandas_code(pandas_query.code)
            
            execution_time = time.time() - start_time
            
            # Convert result to list of dictionaries for JSON serialization
            if isinstance(result_data, pd.DataFrame):
                results = result_data.to_dict('records')
            elif isinstance(result_data, pd.Series):
                results = result_data.to_dict()
                results = [{'index': k, 'value': v} for k, v in results.items()]
            elif result_data is not None:
                results = [{'result': result_data}]
            else:
                results = []
            
            # Generate explanation if requested
            explanation = None
            if query_request.include_explanation:
                explanation = self._generate_explanation(
                    query_request.question, 
                    pandas_query.code, 
                    results
                )
            
            return QueryResult(
                question=query_request.question,
                generated_code=pandas_query.code,
                results=results,
                explanation=explanation,
                execution_time_seconds=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return QueryResult(
                question=query_request.question,
                generated_code="# Query failed",
                results=[],
                explanation=None,
                execution_time_seconds=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _generate_explanation(self, question: str, code: str, results: List[Dict]) -> str:
        """Generate a human-readable explanation of the query results."""
        try:
            results_summary = f"Found {len(results)} results" if results else "No results found"
            
            prompt = f"""
Explain this data analysis in simple business terms:

Original Question: {question}
Code Executed: {code}
Results: {results_summary}

Provide a clear, non-technical explanation of:
1. What the analysis found
2. Key insights or patterns
3. Business implications
4. Any limitations or caveats

Keep the explanation concise and actionable for business users.
"""
            
            explanation = generate_response(
                prompt=prompt,
                system_prompt="You are a business analyst explaining technical results to non-technical stakeholders."
            )
            
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            return "Analysis completed. Results are available above."
    
    def suggest_queries(self, domain: str = "manufacturing") -> List[str]:
        """Suggest relevant queries based on available data."""
        table_names = self.ingestion_service.list_tables()
        
        suggestions = []
        
        # Generic suggestions
        suggestions.extend([
            "What products have low inventory levels?",
            "Which items have the highest demand?",
            "Show me the top 10 products by volume",
            "What are the current inventory levels?",
            "Which products should we prioritize for production?"
        ])
        
        # Table-specific suggestions
        for table_name in table_names:
            try:
                schema = self.ingestion_service.get_table_schema(table_name)
                
                # Look for common patterns
                column_names = [col.name.lower() for col in schema.columns]
                
                if any('inventory' in name or 'stock' in name for name in column_names):
                    suggestions.append(f"What is the current inventory status in {table_name}?")
                
                if any('demand' in name or 'forecast' in name for name in column_names):
                    suggestions.append(f"Show demand trends from {table_name}")
                
                if any('price' in name or 'cost' in name for name in column_names):
                    suggestions.append(f"Analyze pricing data in {table_name}")
            
            except Exception as e:
                logger.warning(f"Could not generate suggestions for {table_name}: {str(e)}")
                continue
        
        return suggestions[:10]  # Limit to 10 suggestions


# Global service instance
_query_engine_service = None


def get_query_engine_service() -> QueryEngineService:
    """Get the global query engine service instance."""
    global _query_engine_service
    if _query_engine_service is None:
        _query_engine_service = QueryEngineService()
    return _query_engine_service
