"""
FastAPI Application for Financial Analyst Agentic RAG Agent.

This is the main application entry point providing:
- REST API endpoints for agent queries
- WebSocket for streaming responses
- Static file serving (HTML, CSS, JS)
- CORS configuration
- Logging and error handling
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Load environment variables FIRST - use absolute path to .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=str(env_path), override=True)
print(f"📝 Loading environment from: {env_path}")
print(f"   File exists: {env_path.exists()}")

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from Src import agent, schemas, db_queries


# Initialize FastAPI app
app = FastAPI(
    title="Financial Analyst Agentic RAG Agent",
    description="ReAct Agent + Vector RAG + SQL Database + Live Web Search",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent components on startup
@app.on_event("startup")
async def startup_event():
    """Initialize agent and verify database on startup."""
    print("\n" + "="*80)
    print("🚀 Financial Analyst Agent Initialization")
    print("="*80)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    print(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET'}")
    print(f"   TAVILY_API_KEY: {'✅ Set' if os.getenv('TAVILY_API_KEY') else '❌ NOT SET'}")
    
    # Get database path for debugging
    print(f"\n📁 Database Path Check:")
    db_path = Path(__file__).parent / "data" / "meridain_wealth.db"
    print(f"   Looking for: {db_path}")
    print(f"   Exists: {'✅ Yes' if db_path.exists() else '❌ No'}")
    
    # Verify database
    print("\n🗄️  Database Verification:")
    if not db_queries.verify_database():
        print("⚠️  Warning: Database not found or incomplete. Ensure meridain_wealth.db exists.")
    else:
        print("✅ Database verified")
    
    # Initialize agent components
    print("\n🤖 Agent Components:")
    try:
        agent.initialize_agent_components()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    print("="*80 + "\n")


# Serve frontend static files
frontend_dir = Path(__file__).parent / "frontend"
static_dir = frontend_dir / "static"
templates_dir = frontend_dir / "templates"

# Mount static files
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
if templates_dir.exists():
    app.mount("/templates", StaticFiles(directory=str(templates_dir)), name="templates")


# API Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return "<h1>Financial Analyst Agent - No index.html found</h1>"


@app.get("/health")
async def health():
    """
    Health check endpoint - verifies system status.
    
    Returns:
        JSON with status, timestamp, and component information
    """
    db_status = "ok" if db_queries.verify_database() else "error"
    rag_status = "ok" if agent.policy_retriever is not None else "warning"
    
    return {
        "status": "ok",
        "service": "Financial Analyst Agentic RAG Agent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "rag_pipeline": rag_status,
            "llm": "ok" if agent.llm is not None else "error"
        }
    }


@app.get("/api/health")
async def health_check():
    """Legacy health check endpoint (redirects to /health)."""
    return await health()


@app.get("/agent-info")
async def agent_info():
    """
    Get information about the financial analyst agent.
    
    Returns:
        JSON with agent metadata, capabilities, and tools
    """
    tools_info = [
        {
            "name": "portfolio_lookup",
            "description": "Look up a client's portfolio from the database",
            "inputs": ["client_id"]
        },
        {
            "name": "market_data_search",
            "description": "Search market data by ticker, sector, or company name",
            "inputs": ["query"]
        },
        {
            "name": "calculate_metrics",
            "description": "Perform financial calculations (returns, percentages, ratios)",
            "inputs": ["expression"]
        },
        {
            "name": "policy_retriever_tool",
            "description": "Search investment policy PDFs using RAG",
            "inputs": ["query"]
        },
        {
            "name": "web_search",
            "description": "Search for latest market news and RBI updates",
            "inputs": ["query"]
        }
    ]
    
    return {
        "agent_name": "Financial Analyst Agentic RAG Agent",
        "agent_type": "ReAct Agent",
        "version": "1.0.0",
        "organization": "Meridian Wealth Partners",
        "description": "Senior financial analyst with ReAct framework for comprehensive portfolio analysis",
        "capabilities": [
            "portfolio_analysis",
            "market_research",
            "policy_compliance_checking",
            "financial_calculations",
            "real_time_market_intelligence"
        ],
        "data_sources": [
            "SQLite Database (meridain_wealth.db)",
            "FAISS Vector Store (policy documents)",
            "Tavily API (web search)"
        ],
        "tools": tools_info,
        "models": {
            "llm": "gpt-5-mini",
            "embeddings": "text-embedding-3-small",
            "vector_store": "FAISS"
        }
    }


@app.post("/main-chat")
async def main_chat(request: schemas.QueryRequest):
    """
    Main chat endpoint - primary interface for agent queries.
    
    This endpoint processes financial analysis queries using the ReAct agent
    with access to portfolio data, market information, and policy documents.
    
    Args:
        request: QueryRequest with user query and optional metadata
        
    Returns:
        AgentResponse with analysis, tool usage, and reasoning chain
    """
    try:
        # Invoke agent with the query
        result = agent.invoke_agent(request.query)
        
        # Extract final response
        final_msg = result["messages"][-1]
        response_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        
        # Extract tool usage and reasoning
        tool_messages = [m for m in result["messages"] if hasattr(m, 'name')]
        tools_used = [m.name for m in tool_messages]
        
        reasoning_steps = []
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    reasoning_steps.append({
                        "tool": tc['name'],
                        "args": tc.get('args', {}),
                        "description": f"Called {tc['name']} with provided arguments"
                    })
        
        # Build comprehensive response
        response = schemas.AgentResponse(
            query=request.query,
            response=response_text,
            tools_used=tools_used,
            reasoning_steps=[str(s) for s in reasoning_steps],
            sources=[]
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/query")
async def query_agent(request: schemas.QueryRequest):
    """
    Legacy query endpoint (redirects to /main-chat for backward compatibility).
    
    This is maintained for backward compatibility. New clients should use /main-chat.
    """
    return await main_chat(request)


@app.post("/api/query")
async def query_agent(request: schemas.QueryRequest):
    """
    Submit a query to the financial analyst agent.
    
    Args:
        request: QueryRequest containing the user query
        
    Returns:
        AgentResponse with the analysis and tool usage
    """
    try:
        # Invoke agent
        result = agent.invoke_agent(request.query)
        
        # Extract final response
        final_msg = result["messages"][-1]
        response_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        
        # Extract tool usage
        tool_messages = [m for m in result["messages"] if hasattr(m, 'name')]
        tools_used = [m.name for m in tool_messages]
        
        # Extract reasoning (tool calls)
        reasoning_steps = []
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    reasoning_steps.append(f"Called {tc['name']} with args: {tc.get('args', {})}")
        
        response = schemas.AgentResponse(
            query=request.query,
            response=response_text,
            tools_used=tools_used,
            reasoning_steps=reasoning_steps,
            sources=[]  # Can be enhanced to extract source documents
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/api/clients")
async def list_clients():
    """Get list of all available clients."""
    try:
        clients = db_queries.get_all_clients()
        return {
            "count": len(clients),
            "clients": clients
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving clients: {str(e)}")


@app.get("/api/client/{client_id}")
async def get_client_portfolio(client_id: str):
    """Get portfolio details for a specific client."""
    try:
        portfolio = db_queries.get_client_portfolio(client_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving portfolio: {str(e)}")


@app.get("/api/market/{ticker}")
async def get_market_data(ticker: str):
    """Get market data for a ticker."""
    try:
        results = db_queries.search_market_data(ticker)
        if not results:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        return {"data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving market data: {str(e)}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming agent responses.
    
    Allows real-time streaming of agent thinking process and tool execution.
    """
    await websocket.accept()
    try:
        while True:
            # Receive query from client
            data = await websocket.receive_text()
            query_data = json.loads(data)
            query = query_data.get("query", "")
            
            if not query:
                await websocket.send_json({"error": "No query provided"})
                continue
            
            # Send initial acknowledgment
            await websocket.send_json({
                "type": "query_received",
                "query": query,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            try:
                # Invoke agent
                result = agent.invoke_agent(query)
                
                # Stream tool calls and results
                for i, msg in enumerate(result["messages"]):
                    msg_type = type(msg).__name__
                    
                    if msg_type == "AIMessage" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            await websocket.send_json({
                                "type": "tool_call",
                                "tool": tc['name'],
                                "args": tc.get('args', {}),
                                "step": i
                            })
                    
                    elif msg_type == "ToolMessage":
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool": msg.name,
                            "result_preview": str(msg.content)[:500],  # First 500 chars
                            "step": i
                        })
                
                # Send final response
                final_msg = result["messages"][-1]
                response_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
                
                await websocket.send_json({
                    "type": "final_response",
                    "response": response_text,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # Run with: uvicorn app:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
