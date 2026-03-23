"""
Decision Engine Service for production planning and recommendations.
"""
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime
import logging

from app.models.decision_models import (
    RecommendationRequest, 
    RecommendationResponse, 
    ProductionPlan,
    ProductRecommendation,
    PriorityLevel,
    RecommendationReason
)
from app.utils.logging import log_execution_time, get_logger
from app.services.ingestion import DataIngestionService

logger = get_logger(__name__)


class DecisionEngineService:
    """Service for generating production decisions and recommendations."""
    
    def __init__(self):
        self.ingestion_service = DataIngestionService()
    
    def _identify_data_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Identify relevant columns in the dataset."""
        columns = {
            'product_id': None,
            'inventory': None,
            'demand': None,
            'lead_time': None,
            'cost': None,
            'profit': None,
            'capacity': None
        }
        
        # Simple column identification based on common names
        for col in df.columns:
            col_lower = col.lower()
            
            if any(keyword in col_lower for keyword in ['product', 'id', 'sku']):
                columns['product_id'] = col
            elif any(keyword in col_lower for keyword in ['inventory', 'stock', 'quantity']):
                columns['inventory'] = col
            elif any(keyword in col_lower for keyword in ['demand', 'forecast', 'required']):
                columns['demand'] = col
            elif any(keyword in col_lower for keyword in ['lead_time', 'leadtime']):
                columns['lead_time'] = col
            elif any(keyword in col_lower for keyword in ['cost', 'price']):
                columns['cost'] = col
            elif any(keyword in col_lower for keyword in ['profit', 'margin']):
                columns['profit'] = col
            elif any(keyword in col_lower for keyword in ['capacity']):
                columns['capacity'] = col
        
        return columns
    
    def _safe_numeric(self, row: pd.Series, column: Optional[str], default: float = 0) -> float:
        """Safely extract numeric value from a row."""
        if not column or column not in row:
            return default
        
        try:
            value = row[column]
            if pd.isna(value):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _calculate_priority_score(self, row: pd.Series) -> float:
        """Calculate priority score for a product."""
        inventory = row['current_inventory']
        demand = row['forecasted_demand']
        lead_time = row.get('lead_time_days', 7)
        
        # Base score: shortage amount normalized by demand
        shortage = max(0, demand - inventory)
        if demand > 0:
            shortage_ratio = shortage / demand
        else:
            shortage_ratio = 1.0 if inventory <= 0 else 0.0
        
        # Adjust for lead time (longer lead time = higher priority)
        lead_time_factor = min(lead_time / 30, 2.0)  # Cap at 2x multiplier
        
        # Final score calculation
        priority_score = shortage_ratio * lead_time_factor
        
        return min(priority_score, 10.0)  # Cap at 10.0
    
    def _determine_priority_level(self, priority_score: float) -> PriorityLevel:
        """Map priority score to priority level."""
        if priority_score >= 7.0:
            return PriorityLevel.CRITICAL
        elif priority_score >= 4.0:
            return PriorityLevel.HIGH
        elif priority_score >= 2.0:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW
    
    def _generate_reasons(self, row: pd.Series) -> List[RecommendationReason]:
        """Generate reasons for the recommendation."""
        reasons = []
        
        inventory = row['current_inventory']
        demand = row['forecasted_demand']
        
        if inventory < demand:
            shortage = demand - inventory
            if shortage > demand * 0.5:  # More than 50% shortage
                reasons.append(RecommendationReason.INVENTORY_SHORTAGE)
            if demand > inventory * 2:  # High demand relative to inventory
                reasons.append(RecommendationReason.HIGH_DEMAND)
        
        if inventory <= 0:
            reasons.append(RecommendationReason.STOCKOUT_PREVENTION)
        
        if row.get('lead_time_days', 7) > 14:  # Long lead time
            reasons.append(RecommendationReason.LEAD_TIME_OPTIMIZATION)
        
        return reasons or [RecommendationReason.CAPACITY_OPTIMIZATION]
    
    def _generate_explanation(self, row: pd.Series, reasons: List[RecommendationReason]) -> str:
        """Generate explanation for a specific recommendation."""
        inventory = int(row['current_inventory'])
        demand = int(row['forecasted_demand'])
        shortage = max(0, demand - inventory)
        
        if shortage > 0:
            return f"Demand ({demand}) exceeds inventory ({inventory}) by {shortage} units. Immediate production recommended."
        elif demand > inventory * 0.8:
            return f"Inventory level ({inventory}) is adequate but approaching demand ({demand}). Consider production to maintain buffer."
        else:
            return "Based on lead time and profit optimization factors."
    
    @log_execution_time
    def generate_recommendations(self, request: RecommendationRequest) -> ProductionPlan:
        """Generate production recommendations based on current data."""
        logger.info("Generating production recommendations")
        
        try:
            # Get available tables
            tables = self.ingestion_service.list_tables()
            if not tables:
                raise ValueError("No data available for analysis")
            
            # Use the first table for analysis
            main_table = tables[0]
            df = self.ingestion_service.get_table(main_table)
            columns = self._identify_data_columns(df)
            
            # Create normalized DataFrame
            normalized_data = []
            
            for _, row in df.iterrows():
                try:
                    product_id = row[columns['product_id']] if columns['product_id'] else f"product_{len(normalized_data)}"
                    
                    product_data = {
                        'product_id': str(product_id),
                        'current_inventory': self._safe_numeric(row, columns['inventory'], 0),
                        'forecasted_demand': self._safe_numeric(row, columns['demand'], 0),
                        'lead_time_days': self._safe_numeric(row, columns['lead_time'], 7),
                        'unit_cost': self._safe_numeric(row, columns['cost'], 0),
                        'unit_profit': self._safe_numeric(row, columns['profit'], 0),
                        'capacity_required': self._safe_numeric(row, columns['capacity'], 1)
                    }
                    
                    normalized_data.append(product_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing row: {str(e)}")
                    continue
            
            if not normalized_data:
                raise ValueError("No valid product data could be extracted")
            
            product_data = pd.DataFrame(normalized_data)
            
            # Calculate priority scores
            product_data['priority_score'] = product_data.apply(self._calculate_priority_score, axis=1)
            
            # Sort by priority score
            product_data = product_data.sort_values('priority_score', ascending=False)
            
            # Filter based on request parameters
            if request.min_priority_score:
                product_data = product_data[product_data['priority_score'] >= request.min_priority_score]
            
            # Limit to max recommendations
            product_data = product_data.head(request.max_recommendations)
            
            # Generate recommendations
            recommendations = []
            for _, row in product_data.iterrows():
                priority_level = self._determine_priority_level(row['priority_score'])
                
                # Skip low priority if not requested
                if priority_level == PriorityLevel.LOW and not request.include_low_priority:
                    continue
                
                reasons = self._generate_reasons(row)
                
                # Calculate recommended quantity
                shortage = max(0, row['forecasted_demand'] - row['current_inventory'])
                recommended_qty = shortage + int(row['forecasted_demand'] * 0.2)  # Add 20% buffer
                
                recommendation = ProductRecommendation(
                    product_id=row['product_id'],
                    product_name=f"Product {row['product_id']}",
                    priority=priority_level,
                    recommended_quantity=recommended_qty,
                    current_inventory=int(row['current_inventory']),
                    forecasted_demand=int(row['forecasted_demand']),
                    shortage_amount=int(shortage),
                    priority_score=row['priority_score'],
                    reasons=reasons,
                    explanation=self._generate_explanation(row, reasons),
                    lead_time_days=int(row['lead_time_days']),
                    unit_cost=row['unit_cost'],
                    unit_profit=row['unit_profit'],
                    capacity_required=row['capacity_required']
                )
                
                recommendations.append(recommendation)
            
            # Create production plan
            plan = ProductionPlan(
                recommendations=recommendations,
                plan_generated_at=datetime.now().isoformat(),
                planning_horizon_days=request.planning_horizon_days,
                data_sources=tables,
                executive_summary=f"Generated {len(recommendations)} production recommendations",
                key_insights=[f"Analyzed {len(product_data)} products from {main_table}"],
                assumptions=[
                    "Demand forecasts are accurate for the planning period",
                    "Lead times remain constant",
                    "Production capacity is available",
                    "20% safety stock buffer is appropriate"
                ],
                limitations=[
                    "Analysis based on current data snapshot",
                    "Does not account for seasonal variations",
                    "Capacity constraints not modeled"
                ]
            )
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            raise


# Global service instance
_decision_engine_service = None


def get_decision_engine_service() -> DecisionEngineService:
    """Get the global decision engine service instance."""
    global _decision_engine_service
    if _decision_engine_service is None:
        _decision_engine_service = DecisionEngineService()
    return _decision_engine_service
