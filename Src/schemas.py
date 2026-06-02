"""
Pydantic models and schemas for the Financial Analyst Agentic RAG Agent.

This module defines data structures for:
- User query requests
- Agent responses
- Tool execution results
- Database models
- Vector store operations
- Conversation history
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """User query request to the agent."""
    query: str = Field(..., description="The user's financial analysis query")
    client_id: Optional[str] = Field(None, description="Client ID if query is client-specific")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")


class PortfolioHolding(BaseModel):
    """Individual stock holding details."""
    ticker: str
    company: str
    shares: float
    avg_cost: float
    current_price: float
    current_value: float
    unrealized_gain_pct: float
    portfolio_weight_pct: float
    sector: str
    ytd_return: Optional[float]
    analyst_rating: Optional[str]
    purchase_date: Optional[str]


class PortfolioSummary(BaseModel):
    """Complete client portfolio summary."""
    client_id: str
    name: str
    relationship_manager: Optional[str]
    risk_profile: str
    investment_horizon: Optional[str]
    aum_inr: float
    last_review: Optional[str]
    total_portfolio_value: float
    total_cost_basis: float
    overall_return_pct: float
    sector_allocation: Dict[str, float]
    holdings: List[PortfolioHolding]


class MarketData(BaseModel):
    """Market data for a stock/security."""
    ticker: str
    company: str
    sector: str
    price: float
    ytd_return: float
    pe_ratio: Optional[float]
    analyst_rating: Optional[str]
    high_52w: Optional[float]
    low_52w: Optional[float]
    market_cap_cr: Optional[float]


class PolicyDocument(BaseModel):
    """Policy document chunk from RAG."""
    source: str = Field(..., description="PDF filename")
    page: int = Field(..., description="Page number")
    content: str = Field(..., description="Document excerpt")


class AgentResponse(BaseModel):
    """Response from the ReAct agent."""
    query: str
    response: str
    tools_used: List[str] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolExecutionResult(BaseModel):
    """Result from a tool execution."""
    tool_name: str
    status: str  # "success", "error", "partial"
    result: Any
    error_message: Optional[str] = None
    execution_time_ms: float


class ConversationMessage(BaseModel):
    """Single message in conversation history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationHistory(BaseModel):
    """Full conversation history."""
    session_id: str
    client_id: Optional[str]
    messages: List[ConversationMessage]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WebSearchResult(BaseModel):
    """Result from web search (Tavily API)."""
    title: str
    url: str
    content: str
    score: Optional[float]


class CalculationResult(BaseModel):
    """Result from financial calculation."""
    expression: str
    result: str
    calculation_type: str  # "return", "percentage", "compare", "ratio"
