"""
Pydantic models for production decisions and recommendations.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class PriorityLevel(str, Enum):
    """Priority levels for production recommendations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationReason(str, Enum):
    """Reasons for production recommendations."""
    INVENTORY_SHORTAGE = "inventory_shortage"
    HIGH_DEMAND = "high_demand"
    EXPIRING_MATERIALS = "expiring_materials"
    CAPACITY_OPTIMIZATION = "capacity_optimization"
    LEAD_TIME_OPTIMIZATION = "lead_time_optimization"
    PROFIT_MAXIMIZATION = "profit_maximization"
    SEASONAL_DEMAND = "seasonal_demand"
    STOCKOUT_PREVENTION = "stockout_prevention"


class ProductRecommendation(BaseModel):
    """Recommendation for a single product."""
    product_id: str
    product_name: Optional[str] = None
    priority: PriorityLevel
    recommended_quantity: Optional[int] = None
    current_inventory: Optional[int] = None
    forecasted_demand: Optional[int] = None
    shortage_amount: Optional[int] = None
    
    # Scoring and reasoning
    priority_score: float = Field(ge=0.0, description="Numerical priority score")
    reasons: List[RecommendationReason]
    explanation: str
    
    # Additional context
    lead_time_days: Optional[int] = None
    unit_cost: Optional[float] = None
    unit_profit: Optional[float] = None
    capacity_required: Optional[float] = None
    
    # Risk factors
    risk_factors: List[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.8)


class ProductionPlan(BaseModel):
    """Complete production plan with multiple product recommendations."""
    recommendations: List[ProductRecommendation]
    plan_generated_at: str
    planning_horizon_days: int = 30
    
    # Summary statistics
    total_products: int
    critical_products: int = 0
    high_priority_products: int = 0
    
    # Plan metadata
    data_sources: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    
    # Overall insights
    executive_summary: Optional[str] = None
    key_insights: List[str] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate summary stats
        self.total_products = len(self.recommendations)
        self.critical_products = sum(1 for r in self.recommendations if r.priority == PriorityLevel.CRITICAL)
        self.high_priority_products = sum(1 for r in self.recommendations if r.priority == PriorityLevel.HIGH)


class RecommendationRequest(BaseModel):
    """Request for production recommendations."""
    planning_horizon_days: int = Field(default=30, ge=1, le=365)
    max_recommendations: int = Field(default=20, ge=1, le=100)
    include_low_priority: bool = False
    focus_areas: Optional[List[str]] = None  # e.g., ["inventory", "demand", "capacity"]
    
    # Filtering options
    product_categories: Optional[List[str]] = None
    exclude_products: Optional[List[str]] = None
    min_priority_score: Optional[float] = None


class RecommendationResponse(BaseModel):
    """Response containing production recommendations."""
    production_plan: ProductionPlan
    processing_time_seconds: float
    success: bool = True
    message: str = "Recommendations generated successfully"
    
    # Request context
    request_parameters: Optional[RecommendationRequest] = None


class AnalyticsInsight(BaseModel):
    """Single analytical insight about the manufacturing data."""
    title: str
    description: str
    insight_type: str  # e.g., "trend", "outlier", "correlation", "forecast"
    confidence: float = Field(ge=0.0, le=1.0)
    impact_level: PriorityLevel
    
    # Supporting data
    supporting_data: Optional[Dict[str, Any]] = None
    visualization_hint: Optional[str] = None  # Suggestion for chart type


class AnalyticsReport(BaseModel):
    """Comprehensive analytics report."""
    insights: List[AnalyticsInsight]
    report_generated_at: str
    data_coverage_period: Optional[str] = None
    
    # Data quality metrics
    data_completeness_score: float = Field(ge=0.0, le=1.0, default=1.0)
    data_freshness_days: Optional[int] = None
    
    # Executive summary
    executive_summary: str
    top_recommendations: List[str] = Field(default_factory=list)


# Optimization models (for future OR-Tools integration)

class OptimizationObjective(str, Enum):
    """Optimization objectives."""
    MAXIMIZE_PROFIT = "maximize_profit"
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_LEAD_TIME = "minimize_lead_time"
    MAXIMIZE_CAPACITY_UTILIZATION = "maximize_capacity_utilization"
    MINIMIZE_INVENTORY = "minimize_inventory"


class OptimizationConstraint(BaseModel):
    """Optimization constraint definition."""
    name: str
    constraint_type: str  # e.g., "capacity", "budget", "material", "time"
    limit_value: float
    unit: str
    description: Optional[str] = None


class OptimizationRequest(BaseModel):
    """Request for optimization-based production planning."""
    objective: OptimizationObjective
    constraints: List[OptimizationConstraint]
    planning_horizon_days: int = 30
    include_uncertainty: bool = False


class OptimizationResult(BaseModel):
    """Result from optimization model."""
    optimal_production_plan: ProductionPlan
    objective_value: float
    solver_status: str
    solve_time_seconds: float
    
    # Sensitivity analysis
    constraint_utilization: Dict[str, float] = Field(default_factory=dict)
    shadow_prices: Dict[str, float] = Field(default_factory=dict)
