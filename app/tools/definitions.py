"""OpenAI tool definitions for the ClearJournal AI agent.

Each tool maps to an existing service method. The agent decides which
tools to call based on the user's question.
"""

CLEARJOURNAL_TOOLS = [
    # 1. Overall stats
    {
        "type": "function",
        "function": {
            "name": "get_overall_stats",
            "description": "Get overall trading statistics: total PnL, win rate, profit factor, "
                           "average win/loss, trade count, and more. Use as a default when the "
                           "user asks 'how am I doing?' or wants a general performance overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Last N days to look back. Omit or null for all time.",
                    }
                },
            },
        },
    },
    # 2. Per-symbol performance
    {
        "type": "function",
        "function": {
            "name": "get_symbol_performance",
            "description": "Get win rate, PnL, and trade count broken down by trading symbol. "
                           "Use when the user asks about a specific coin (e.g. 'how is BTC doing?') "
                           "or wants their best/worst symbols.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair, e.g. BTCUSDT. Omit for all symbols.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    },
                },
            },
        },
    },
    # 3. Per-tag (strategy) performance
    {
        "type": "function",
        "function": {
            "name": "get_tag_performance",
            "description": "Get performance breakdown by tag/strategy label. "
                           "Use when the user asks 'which strategy works best?' or mentions tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    }
                },
            },
        },
    },
    # 4. Day-of-week performance
    {
        "type": "function",
        "function": {
            "name": "get_day_of_week_performance",
            "description": "Get trading performance grouped by day of the week. "
                           "Use when the user asks about best/worst trading days (Monday, Tuesday, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    }
                },
            },
        },
    },
    # 5. Time-of-day / session performance
    {
        "type": "function",
        "function": {
            "name": "get_time_of_day_performance",
            "description": "Get trading performance grouped by time-of-day or trading session. "
                           "Use when the user asks about best hours or Asian/European/US sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    }
                },
            },
        },
    },
    # 6. Recent trades
    {
        "type": "function",
        "function": {
            "name": "get_recent_trades",
            "description": "List the user's most recent trades with symbol, side, PnL, and timestamps. "
                           "Use when the user asks 'what did I trade recently?' or 'show my last trades'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of trades to return. Default 10, max 50.",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Filter by symbol, e.g. ETHUSDT. Omit for all.",
                    },
                },
            },
        },
    },
    # 7. Worst trades
    {
        "type": "function",
        "function": {
            "name": "get_worst_trades",
            "description": "List the user's biggest losing trades. "
                           "Use when the user asks about their worst trades or biggest losses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of trades to return. Default 5, max 20.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    },
                },
            },
        },
    },
    # 8. MFE/MAE analysis
    {
        "type": "function",
        "function": {
            "name": "get_mfe_mae_analysis",
            "description": "Get Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) "
                           "analysis. Shows how far trades moved in your favor/adversely before closing. "
                           "Use when the user asks about exit timing, holding too long, or cutting too early.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Filter by symbol. Omit for all.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    },
                },
            },
        },
    },
    # 9. Funding fees
    {
        "type": "function",
        "function": {
            "name": "get_funding_fees",
            "description": "Get funding fee statistics for futures/perpetual trades. "
                           "Shows total funding paid/received and its impact on PnL. "
                           "Use when the user asks about funding costs or fee impact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Filter by symbol. Omit for all.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    },
                },
            },
        },
    },
    # 10. Winning vs Losing characteristics
    {
        "type": "function",
        "function": {
            "name": "get_winning_vs_losing",
            "description": "Compare characteristics of winning trades vs losing trades: "
                           "average size, duration, symbols, sides. "
                           "Use when the user asks 'what do my winners have in common?' "
                           "or 'how are my winners different from losers?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Last N days. Omit or null for all time.",
                    }
                },
            },
        },
    },
    # 11. Open positions
    {
        "type": "function",
        "function": {
            "name": "get_open_positions",
            "description": "Get all currently open positions across exchange and wallet accounts. "
                           "Shows symbol, size, side, entry price, and unrealized PnL. "
                           "Use when the user asks 'what positions do I have open?' or 'am I in any trades?'",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # 12. Portfolio assets
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_assets",
            "description": "Get a consolidated view of all crypto assets the user holds, "
                           "with amounts, values, and which accounts they're in. "
                           "Use when the user asks 'what do I own?' or 'show my portfolio'.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
