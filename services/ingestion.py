"""
Data ingestion service for loading and processing CSV/Excel files.
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd

from ..models.schema_models import TableSchema, ColumnInfo, DataType
from ..utils.file_utils import read_data_file, get_table_name_from_filename, list_uploaded_files
from ..utils.logging import get_logger, log_execution_time, log_dataframe_info


logger = get_logger(__name__)


class DataIngestionService:
    """Service for ingesting and processing data files."""
    
    def __init__(self):
        self.loaded_tables: Dict[str, pd.DataFrame] = {}
        self.table_schemas: Dict[str, TableSchema] = {}
    
    def _detect_data_type(self, series: pd.Series) -> DataType:
        """Detect the appropriate data type for a pandas Series."""
        # Check for datetime first
        if pd.api.types.is_datetime64_any_dtype(series):
            if hasattr(series.dtype, 'tz') and series.dtype.tz:
                return DataType.DATETIME
            return DataType.DATE
        
        # Check for numeric types
        if pd.api.types.is_integer_dtype(series):
            return DataType.INTEGER
        
        if pd.api.types.is_float_dtype(series):
            return DataType.FLOAT
        
        # Check for boolean
        if pd.api.types.is_bool_dtype(series):
            return DataType.BOOLEAN
        
        # Try to infer datetime from object columns
        if pd.api.types.is_object_dtype(series):
            # Sample a few non-null values to check for dates
            sample_values = series.dropna().head(10)
            if not sample_values.empty:
                try:
                    # Try to parse as datetime
                    pd.to_datetime(sample_values.iloc[0])
                    # If successful, check if it looks like date or datetime
                    parsed = pd.to_datetime(sample_values, errors='coerce')
                    if parsed.notna().all():
                        # Check if times are all midnight (date only)
                        times = parsed.dt.time
                        if all(t == times.iloc[0] for t in times):
                            return DataType.DATE
                        return DataType.DATETIME
                except (ValueError, TypeError):
                    pass
        
        # Default to string for object types
        return DataType.STRING
    
    def _extract_column_info(self, df: pd.DataFrame, column_name: str) -> ColumnInfo:
        """Extract information about a single column."""
        series = df[column_name]
        
        # Basic statistics
        null_count = series.isna().sum()
        unique_count = series.nunique()
        
        # Sample values (convert to Python types for JSON serialization)
        sample_values = []
        non_null_values = series.dropna().head(5)
        for val in non_null_values:
            if pd.isna(val):
                continue
            # Convert pandas/numpy types to Python types
            if hasattr(val, 'item'):
                val = val.item()
            sample_values.append(val)
        
        return ColumnInfo(
            name=column_name,
            data_type=self._detect_data_type(series),
            nullable=null_count > 0,
            sample_values=sample_values,
            unique_count=unique_count,
            null_count=int(null_count)
        )
    
    @log_execution_time
    def load_file(self, file_path: str) -> TableSchema:
        """
        Load a single data file and extract its schema.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            TableSchema with extracted information
        """
        logger.info(f"Loading file: {file_path}")
        
        try:
            # Read the data file
            df = read_data_file(file_path)
            log_dataframe_info(df, f"Loaded file {os.path.basename(file_path)}")
            
            # Generate table name
            table_name = get_table_name_from_filename(file_path)
            
            # Store the DataFrame
            self.loaded_tables[table_name] = df
            
            # Extract column information
            columns = []
            for column_name in df.columns:
                try:
                    column_info = self._extract_column_info(df, column_name)
                    columns.append(column_info)
                except Exception as e:
                    logger.warning(f"Error processing column {column_name}: {str(e)}")
                    # Create a basic column info as fallback
                    columns.append(ColumnInfo(
                        name=column_name,
                        data_type=DataType.UNKNOWN,
                        sample_values=[]
                    ))
            
            # Create table schema
            schema = TableSchema(
                table_name=table_name,
                file_path=file_path,
                columns=columns,
                row_count=len(df),
                file_size_bytes=os.path.getsize(file_path),
                created_at=datetime.now().isoformat(),
                last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            )
            
            # Store schema
            self.table_schemas[table_name] = schema
            
            logger.info(f"Successfully loaded table '{table_name}' with {len(df)} rows and {len(df.columns)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {str(e)}")
            raise
    
    @log_execution_time
    def load_all_files(self, file_paths: List[str] = None) -> List[TableSchema]:
        """
        Load multiple data files.
        
        Args:
            file_paths: List of file paths to load. If None, loads all uploaded files.
            
        Returns:
            List of TableSchema objects
        """
        if file_paths is None:
            # Load all uploaded files
            uploaded_files = list_uploaded_files()
            file_paths = [f['path'] for f in uploaded_files]
        
        schemas = []
        for file_path in file_paths:
            try:
                schema = self.load_file(file_path)
                schemas.append(schema)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {str(e)}")
                # Continue with other files
                continue
        
        logger.info(f"Loaded {len(schemas)} files successfully out of {len(file_paths)} total")
        return schemas
    
    def get_table(self, table_name: str) -> pd.DataFrame:
        """Get a loaded table by name."""
        if table_name not in self.loaded_tables:
            raise ValueError(f"Table '{table_name}' not found. Available tables: {list(self.loaded_tables.keys())}")
        return self.loaded_tables[table_name]
    
    def get_table_schema(self, table_name: str) -> TableSchema:
        """Get schema for a loaded table."""
        if table_name not in self.table_schemas:
            raise ValueError(f"Schema for table '{table_name}' not found")
        return self.table_schemas[table_name]
    
    def list_tables(self) -> List[str]:
        """List all loaded table names."""
        return list(self.loaded_tables.keys())
    
    def get_all_schemas(self) -> List[TableSchema]:
        """Get all table schemas."""
        return list(self.table_schemas.values())
    
    def clear_data(self):
        """Clear all loaded data and schemas."""
        self.loaded_tables.clear()
        self.table_schemas.clear()
        logger.info("Cleared all loaded data")
    
    def reload_file(self, file_path: str) -> TableSchema:
        """Reload a specific file, updating existing data."""
        table_name = get_table_name_from_filename(file_path)
        
        # Remove existing data
        if table_name in self.loaded_tables:
            del self.loaded_tables[table_name]
        if table_name in self.table_schemas:
            del self.table_schemas[table_name]
        
        # Load fresh data
        return self.load_file(file_path)
    
    def get_table_summary(self) -> Dict[str, Any]:
        """Get a summary of all loaded tables."""
        summary = {
            'total_tables': len(self.loaded_tables),
            'total_rows': sum(len(df) for df in self.loaded_tables.values()),
            'total_columns': sum(len(df.columns) for df in self.loaded_tables.values()),
            'tables': []
        }
        
        for table_name, df in self.loaded_tables.items():
            schema = self.table_schemas.get(table_name)
            table_info = {
                'name': table_name,
                'rows': len(df),
                'columns': len(df.columns),
                'file_size_bytes': schema.file_size_bytes if schema else None,
                'file_path': schema.file_path if schema else None
            }
            summary['tables'].append(table_info)
        
        return summary
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """
        Validate data consistency across loaded tables.
        
        Returns:
            Dictionary with validation results and issues found
        """
        issues = []
        warnings = []
        
        for table_name, df in self.loaded_tables.items():
            # Check for empty tables
            if df.empty:
                issues.append(f"Table '{table_name}' is empty")
            
            # Check for duplicate column names
            if len(df.columns) != len(set(df.columns)):
                duplicates = [col for col in df.columns if list(df.columns).count(col) > 1]
                issues.append(f"Table '{table_name}' has duplicate columns: {duplicates}")
            
            # Check for columns with all null values
            all_null_cols = df.columns[df.isnull().all()].tolist()
            if all_null_cols:
                warnings.append(f"Table '{table_name}' has columns with all null values: {all_null_cols}")
            
            # Check data type consistency
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Check if numeric data is stored as strings
                    sample_values = df[col].dropna().head(100)
                    if not sample_values.empty:
                        try:
                            pd.to_numeric(sample_values)
                            warnings.append(f"Table '{table_name}', column '{col}' appears to be numeric but stored as text")
                        except (ValueError, TypeError):
                            pass
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'tables_checked': len(self.loaded_tables)
        }


# Global service instance
_ingestion_service = None


def get_ingestion_service() -> DataIngestionService:
    """Get the global ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DataIngestionService()
    return _ingestion_service
