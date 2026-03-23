"""
Relationship detection service for finding connections between tables.
"""
import itertools
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from difflib import SequenceMatcher

from ..models.schema_models import TableRelationship, RelationshipType, DatabaseSchema
from ..utils.logging import get_logger, log_execution_time
from .ingestion import get_ingestion_service


logger = get_logger(__name__)


class RelationshipDetectionService:
    """Service for detecting relationships between tables."""
    
    def __init__(self):
        self.ingestion_service = get_ingestion_service()
        self.similarity_threshold = 0.8
        self.sample_size = 1000  # Number of rows to sample for join quality testing
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _detect_potential_keys(self, df: pd.DataFrame, column_name: str) -> Dict[str, Any]:
        """Analyze a column to determine if it could be a key."""
        column = df[column_name]
        
        total_rows = len(df)
        unique_count = column.nunique()
        null_count = column.isnull().sum()
        
        # Key characteristics
        uniqueness_ratio = unique_count / (total_rows - null_count) if total_rows > null_count else 0
        has_nulls = null_count > 0
        
        # Analyze data pattern
        sample_values = column.dropna().head(10).astype(str).tolist()
        
        return {
            'uniqueness_ratio': uniqueness_ratio,
            'has_nulls': has_nulls,
            'sample_values': sample_values,
            'is_likely_key': uniqueness_ratio > 0.9 and not has_nulls,
            'is_potential_foreign_key': uniqueness_ratio < 0.9 and uniqueness_ratio > 0.1
        }
    
    def _test_join_quality(self, 
                          df1: pd.DataFrame, col1: str,
                          df2: pd.DataFrame, col2: str) -> float:
        """Test the quality of a potential join between two columns."""
        try:
            # Sample data if tables are large
            sample_df1 = df1.sample(min(len(df1), self.sample_size))
            sample_df2 = df2.sample(min(len(df2), self.sample_size))
            
            # Get unique values from both columns
            values1 = set(sample_df1[col1].dropna().astype(str))
            values2 = set(sample_df2[col2].dropna().astype(str))
            
            if not values1 or not values2:
                return 0.0
            
            # Calculate overlap
            intersection = values1.intersection(values2)
            union = values1.union(values2)
            
            # Jaccard similarity
            jaccard_similarity = len(intersection) / len(union) if union else 0.0
            
            # Also consider the proportion of values that match
            match_ratio1 = len(intersection) / len(values1)
            match_ratio2 = len(intersection) / len(values2)
            
            # Combined score
            quality_score = (jaccard_similarity + max(match_ratio1, match_ratio2)) / 2
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"Error testing join quality between {col1} and {col2}: {str(e)}")
            return 0.0
    
    @log_execution_time
    def detect_column_relationships(self) -> List[TableRelationship]:
        """Detect relationships between columns across all tables."""
        relationships = []
        table_names = self.ingestion_service.list_tables()
        
        logger.info(f"Detecting relationships across {len(table_names)} tables")
        
        # Compare each pair of tables
        for table1, table2 in itertools.combinations(table_names, 2):
            try:
                df1 = self.ingestion_service.get_table(table1)
                df2 = self.ingestion_service.get_table(table2)
                
                # Compare each column in table1 with each column in table2
                for col1 in df1.columns:
                    for col2 in df2.columns:
                        # Calculate column name similarity
                        name_similarity = self._calculate_similarity(col1, col2)
                        
                        if name_similarity >= self.similarity_threshold:
                            # Test join quality
                            join_quality = self._test_join_quality(df1, col1, df2, col2)
                            
                            if join_quality > 0.1:  # Minimum threshold for considering a relationship
                                # Analyze key characteristics
                                key_info1 = self._detect_potential_keys(df1, col1)
                                key_info2 = self._detect_potential_keys(df2, col2)
                                
                                # Determine relationship type
                                relationship_type = self._determine_relationship_type(
                                    key_info1, key_info2, join_quality
                                )
                                
                                relationship = TableRelationship(
                                    source_table=table1,
                                    source_column=col1,
                                    target_table=table2,
                                    target_column=col2,
                                    relationship_type=relationship_type,
                                    confidence_score=min(name_similarity, join_quality),
                                    join_sample_quality=join_quality
                                )
                                
                                relationships.append(relationship)
                                
                                logger.info(
                                    f"Found relationship: {table1}.{col1} -> {table2}.{col2} "
                                    f"(confidence: {relationship.confidence_score:.2f})"
                                )
                
            except Exception as e:
                logger.error(f"Error analyzing relationship between {table1} and {table2}: {str(e)}")
                continue
        
        # Sort by confidence score
        relationships.sort(key=lambda r: r.confidence_score, reverse=True)
        
        logger.info(f"Detected {len(relationships)} potential relationships")
        return relationships
    
    def _determine_relationship_type(self, 
                                   key_info1: Dict[str, Any], 
                                   key_info2: Dict[str, Any],
                                   join_quality: float) -> RelationshipType:
        """Determine the type of relationship based on key characteristics."""
        
        # If both are likely keys with high join quality, it's one-to-one
        if (key_info1['is_likely_key'] and key_info2['is_likely_key'] and 
            join_quality > 0.8):
            return RelationshipType.ONE_TO_ONE
        
        # If one is a key and the other is not, it's one-to-many
        if (key_info1['is_likely_key'] and not key_info2['is_likely_key']) or \
           (key_info2['is_likely_key'] and not key_info1['is_likely_key']):
            return RelationshipType.ONE_TO_MANY
        
        # If both are potential foreign keys, it might be many-to-many
        if (key_info1['is_potential_foreign_key'] and 
            key_info2['is_potential_foreign_key']):
            return RelationshipType.MANY_TO_MANY
        
        # Default to unknown
        return RelationshipType.UNKNOWN
    
    def find_common_identifiers(self) -> Dict[str, List[str]]:
        """Find columns that appear across multiple tables (potential common identifiers)."""
        table_names = self.ingestion_service.list_tables()
        column_appearances = {}
        
        # Collect all column names and their appearances
        for table_name in table_names:
            try:
                schema = self.ingestion_service.get_table_schema(table_name)
                for col in schema.columns:
                    # Normalize column name
                    normalized_name = col.name.lower().strip()
                    
                    if normalized_name not in column_appearances:
                        column_appearances[normalized_name] = []
                    
                    column_appearances[normalized_name].append(f"{table_name}.{col.name}")
            except Exception as e:
                logger.error(f"Error processing table {table_name}: {str(e)}")
                continue
        
        # Find columns that appear in multiple tables
        common_identifiers = {}
        for col_name, appearances in column_appearances.items():
            if len(appearances) > 1:
                common_identifiers[col_name] = appearances
        
        return common_identifiers
    
    def enhance_database_schema(self, database_schema: DatabaseSchema) -> DatabaseSchema:
        """Enhance a database schema with detected relationships."""
        relationships = self.detect_column_relationships()
        
        # Update the schema with relationships
        enhanced_schema = DatabaseSchema(
            tables=database_schema.tables,
            relationships=relationships,
            schema_version=database_schema.schema_version,
            generated_at=__import__('datetime').datetime.now().isoformat()
        )
        
        return enhanced_schema
    
    def get_relationship_summary(self) -> Dict[str, Any]:
        """Get a summary of detected relationships."""
        relationships = self.detect_column_relationships()
        common_identifiers = self.find_common_identifiers()
        
        summary = {
            'total_relationships': len(relationships),
            'relationship_types': {},
            'high_confidence_relationships': 0,
            'common_identifiers': len(common_identifiers),
            'table_connectivity': {}
        }
        
        # Analyze relationship types
        for rel in relationships:
            rel_type = rel.relationship_type.value
            if rel_type not in summary['relationship_types']:
                summary['relationship_types'][rel_type] = 0
            summary['relationship_types'][rel_type] += 1
            
            if rel.confidence_score > 0.8:
                summary['high_confidence_relationships'] += 1
        
        # Analyze table connectivity
        table_names = self.ingestion_service.list_tables()
        for table in table_names:
            connected_tables = set()
            for rel in relationships:
                if rel.source_table == table:
                    connected_tables.add(rel.target_table)
                elif rel.target_table == table:
                    connected_tables.add(rel.source_table)
            
            summary['table_connectivity'][table] = len(connected_tables)
        
        return summary


# Global service instance
_relationship_service = None


def get_relationship_service() -> RelationshipDetectionService:
    """Get the global relationship detection service instance."""
    global _relationship_service
    if _relationship_service is None:
        _relationship_service = RelationshipDetectionService()
    return _relationship_service