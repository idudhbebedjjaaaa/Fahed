//+------------------------------------------------------------------+
//| SARTypes.mqh - Type definitions for SAR Expert Advisor           |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property strict

//--- Enumerations
enum ENUM_DISTANCE_MODE
{
   DISTANCE_FIXED = 0,        // Fixed distance in points
   DISTANCE_ATR = 1,          // ATR-based dynamic distance
   DISTANCE_VOLATILITY = 2,   // Volatility adaptive distance
   DISTANCE_SESSION = 3,      // Session-based distance
   DISTANCE_SPREAD_ADJ = 4    // Spread-adjusted distance
};

enum ENUM_TRAILING_MODE
{
   TRAIL_NONE = 0,            // No trailing
   TRAIL_FIXED = 1,           // Fixed trailing stop
   TRAIL_ATR = 2,             // ATR-based trailing
   TRAIL_CHANDELIER = 3,      // Chandelier Exit
   TRAIL_STEP = 4,            // Step trailing
   TRAIL_VOLATILITY = 5,      // Volatility trailing
   TRAIL_HYBRID = 6           // Hybrid trailing (ATR + Step)
};

enum ENUM_EXIT_MODE
{
   EXIT_REVERSE_ONLY = 0,     // Only reverse (always in market)
   EXIT_TP_AND_TRAIL = 1,     // Take Profit + Trailing
   EXIT_TRAIL_ONLY = 2,       // Trailing only
   EXIT_WAIT_REENTRY = 3      // Exit and wait before re-entry
};

enum ENUM_TREND_FILTER
{
   FILTER_NONE = 0,           // No filter
   FILTER_ADX = 1,            // ADX filter
   FILTER_EMA_CROSS = 2,      // EMA crossover filter
   FILTER_MARKET_STRUCT = 3,  // Market structure filter
   FILTER_ATR_EXPANSION = 4,  // ATR expansion filter
   FILTER_COMPOSITE = 5       // Composite filter (multiple)
};

enum ENUM_START_DIRECTION
{
   START_BUY = 0,             // Always start with Buy
   START_SELL = 1,            // Always start with Sell
   START_RANDOM = 2,          // Random start
   START_TREND = 3            // Trend-based start
};

enum ENUM_SESSION_FILTER
{
   SESSION_ALL = 0,           // Trade all sessions
   SESSION_LONDON = 1,        // London session only
   SESSION_NEWYORK = 2,       // New York session only
   SESSION_ASIAN = 3,         // Asian session only
   SESSION_LONDON_NY = 4      // London + NY overlap
};

//--- Structure definitions
struct TradeStats
{
   int    totalTrades;
   int    winTrades;
   int    lossTrades;
   double grossProfit;
   double grossLoss;
   double netProfit;
   double maxDrawdown;
   double maxDrawdownPercent;
   int    maxConsecLosses;
   int    maxConsecWins;
   int    consecutiveReversals;
   double dailyLoss;
   double peakEquity;
};

struct SessionTime
{
   int startHour;
   int startMinute;
   int endHour;
   int endMinute;
};
//+------------------------------------------------------------------+
