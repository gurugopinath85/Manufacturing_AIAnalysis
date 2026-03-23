"""
Dependency injection for Manufacturing AI Analysis Services.
"""
from functools import lru_cache

from app.services.ingestion import DataIngestionService
from app.services.schema import SchemaInterpretationService
from app.services.relationships import RelationshipDetectionService
from app.services.query_engine import QueryEngineService
from app.services.decision_engine import DecisionEngineService


# Service instances (singleton pattern using lru_cache)

@lru_cache()
def get_ingestion_service() -> DataIngestionService:
    """Get ingestion service instance."""
    return DataIngestionService()


@lru_cache()
def get_schema_service() -> SchemaInterpretationService:
    """Get schema service instance."""
    return SchemaInterpretationService()


@lru_cache()
def get_relationship_service() -> RelationshipDetectionService:
    """Get relationship service instance."""
    return RelationshipDetectionService()


@lru_cache()
def get_query_engine_service() -> QueryEngineService:
    """Get query engine service instance."""
    return QueryEngineService()


@lru_cache()
def get_decision_engine_service() -> DecisionEngineService:
    """Get decision engine service instance."""
    return DecisionEngineService()
