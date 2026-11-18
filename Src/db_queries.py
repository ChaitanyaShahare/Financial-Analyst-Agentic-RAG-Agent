"""
Database query functions for the Financial Analyst Agentic RAG Agent.

This module provides SQLite database operations for:
- Client portfolio queries
- Market data searches
- Financial metrics retrieval
- Holdings and transactions lookup

Database: data/meridian_wealth.db
Tables: clients, holdings, market_data
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Get database path relative to project root
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "meridian_wealth.db"  # Fixed: meridian (not meridain)


def query_db(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Execute a SQL query against the Meridian Wealth database.
    
    Args:
        sql: SQL query string
        params: Query parameters tuple
        
    Returns:
        List of dictionaries representing query rows
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # CONCEPT: Safety - parameterised SQL
    # Values chosen by the LLM (like a client id) are passed separately in
    # `params` and filled in by SQLite at the "?" placeholders, never pasted into
    # the SQL text. This blocks SQL injection, even if the model is tricked into
    # sending something like "CLT-001'; DROP TABLE clients; --".
    # The tools also only ever run fixed SELECT queries: the agent cannot write
    # its own SQL or change data.
    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_client_portfolio(client_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full portfolio for a client with enriched market data.
    
    Args:
        client_id: Client ID (e.g., 'CLT-001')
        
    Returns:
        Dictionary with client info and holdings, or None if not found
    """
    client = query_db("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    if not client:
        return None

    holdings = query_db("""
        SELECT h.ticker, h.company_name, h.shares, h.avg_cost_basis, h.current_price,
               h.sector, h.purchase_date,
               m.ytd_return_pct, m.pe_ratio, m.analyst_rating, m.high_52w, m.low_52w
        FROM holdings h
        LEFT JOIN market_data m ON h.ticker = m.ticker
        WHERE h.client_id = ?
        ORDER BY (h.shares * h.current_price) DESC
    """, (client_id,))

    return {"client": client[0], "holdings": holdings}


def search_market_data(query: str) -> List[Dict[str, Any]]:
    """
    Search market data by ticker, sector, or company name.
    
    Args:
        query: Search query (ticker, sector, or company name)
        
    Returns:
        List of matching market data records
    """
    q = query.upper().strip()
    results = query_db("SELECT * FROM market_data WHERE ticker = ?", (q,))
    if not results:
        results = query_db(
            "SELECT * FROM market_data WHERE UPPER(sector) LIKE ? OR UPPER(company_name) LIKE ? OR ticker LIKE ?",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        )
    return results


def get_all_clients() -> List[Dict[str, Any]]:
    """Get list of all clients."""
    return query_db("SELECT client_id, name, risk_profile, aum_inr FROM clients")


def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """Get client details by ID."""
    results = query_db("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    return results[0] if results else None


def get_sector_distribution(client_id: str) -> Dict[str, float]:
    """
    Get sector-wise portfolio distribution for a client.
    
    Args:
        client_id: Client ID
        
    Returns:
        Dictionary mapping sectors to their portfolio percentage
    """
    portfolio = get_client_portfolio(client_id)
    if not portfolio:
        return {}
    
    holdings = portfolio["holdings"]
    total_value = sum(h["shares"] * h["current_price"] for h in holdings)
    
    if total_value == 0:
        return {}
    
    sector_values = {}
    for h in holdings:
        val = h["shares"] * h["current_price"]
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + val
    
    return {s: round((v / total_value) * 100, 1) for s, v in sector_values.items()}


def get_holding_concentration(client_id: str, ticker: str) -> Optional[float]:
    """
    Get the concentration percentage of a specific ticker in a client's portfolio.
    
    Args:
        client_id: Client ID
        ticker: Stock ticker symbol
        
    Returns:
        Percentage of portfolio in this holding, or None if not held
    """
    portfolio = get_client_portfolio(client_id)
    if not portfolio:
        return None
    
    holdings = portfolio["holdings"]
    total_value = sum(h["shares"] * h["current_price"] for h in holdings)
    
    if total_value == 0:
        return None
    
    for h in holdings:
        if h["ticker"] == ticker:
            holding_value = h["shares"] * h["current_price"]
            return round((holding_value / total_value) * 100, 2)
    
    return None


def verify_database() -> bool:
    """
    Verify that the database exists and contains required tables.
    
    Returns:
        True if database is valid, False otherwise
    """
    print(f"DEBUG: Looking for database at: {DB_PATH}")
    print(f"DEBUG: Absolute path: {DB_PATH.resolve()}")
    print(f"DEBUG: Database exists: {DB_PATH.exists()}")
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        for table in ["clients", "holdings", "market_data"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
        conn.close()
        print(f"✅ Database verified at {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
