//+------------------------------------------------------------------+
//| SAR_Expert.mq5 - Stop-And-Reverse Expert Advisor                 |
//| Professional Quant Fund Grade EA                                 |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property version   "2.00"
#property description "Professional Stop-And-Reverse EA with Dynamic Filters"
#property strict

#include <Trade\Trade.mqh>
#include "..\Include\SARTypes.mqh"
#include "..\Include\SARFilters.mqh"
#include "..\Include\SARTrailing.mqh"
#include "..\Include\SARRiskManager.mqh"

//+------------------------------------------------------------------+
//| Input Parameters                                                 |
//+------------------------------------------------------------------+
//--- Core SAR Parameters
input group "=== Core SAR Settings ==="
input ENUM_DISTANCE_MODE InpDistanceMode    = DISTANCE_ATR;      // Reversal Distance Mode
input double             InpFixedDistance    = 100;               // Fixed Distance (points)
input double             InpATRDistanceMult = 2.0;               // ATR Distance Multiplier
input int                InpATRPeriod       = 14;                // ATR Period

//--- Exit Mode
input group "=== Exit Mode ==="
input ENUM_EXIT_MODE     InpExitMode        = EXIT_REVERSE_ONLY; // Exit Mode
input double             InpTakeProfit      = 200;               // Take Profit (points, if applicable)
input int                InpWaitBars        = 5;                 // Wait bars before re-entry

//--- Trailing Stop
input group "=== Trailing Stop ==="
input ENUM_TRAILING_MODE InpTrailingMode    = TRAIL_ATR;         // Trailing Stop Mode
input double             InpTrailFixed      = 150;               // Fixed Trail (points)
input double             InpTrailATRMult    = 1.5;               // ATR Trail Multiplier
input double             InpChandelierMult  = 3.0;               // Chandelier Multiplier
input int                InpChandelierPeriod= 22;                // Chandelier Period
input double             InpStepSize        = 20;                // Step Size (points)
input double             InpStepDistance    = 50;                 // Step Distance (points)
input double             InpVolTrailMult    = 2.0;               // Volatility Trail Multiplier

//--- Trend Filters
input group "=== Trend Filters ==="
input ENUM_TREND_FILTER  InpTrendFilter     = FILTER_ADX;        // Trend Filter Mode
input int                InpADXPeriod       = 14;                // ADX Period
input double             InpADXThreshold    = 20.0;              // ADX Threshold
input int                InpEMAFast         = 20;                // EMA Fast Period
input int                InpEMASlow         = 50;                // EMA Slow Period
input double             InpATRExpMult      = 1.2;               // ATR Expansion Multiplier
input double             InpVolumeThreshold = 1.5;               // Volume Threshold Multiplier

//--- Multi-Timeframe
input group "=== Multi-Timeframe ==="
input bool               InpUseHTF          = true;              // Use Higher TF Filter
input ENUM_TIMEFRAMES    InpHTFPeriod       = PERIOD_H1;         // Higher Timeframe
input int                InpHTFEMAPeriod    = 50;                // HTF EMA Period

//--- Session Filter
input group "=== Session Filter ==="
input ENUM_SESSION_FILTER InpSessionFilter  = SESSION_ALL;       // Session Filter

//--- Start Direction
input group "=== Start Direction ==="
input ENUM_START_DIRECTION InpStartDir      = START_TREND;       // Initial Direction

//--- Risk Management
input group "=== Risk Management ==="
input double             InpRiskPercent     = 1.0;               // Risk Per Trade (%)
input double             InpFixedLots       = 0.1;               // Fixed Lot Size (if risk=0)

//--- Protection System
input group "=== Protection System ==="
input int                InpMaxConsecRev    = 5;                 // Max Consecutive Reversals
input double             InpMaxDailyLoss   = 3.0;               // Max Daily Loss (%)
input double             InpMaxSpread       = 30;                // Max Spread (points)
input int                InpCooldownBars    = 3;                 // Cooldown Between Reversals (bars)
input double             InpVolShutdownMult = 3.0;               // Volatility Shutdown Multiplier
input double             InpEquityProtect   = 10.0;              // Equity Protection (% from peak)
input double             InpMaxSlippage     = 10;                // Max Slippage (points)

//--- General
input group "=== General ==="
input int                InpMagicNumber     = 777777;            // Magic Number
input string             InpComment         = "SAR_EA";          // Order Comment

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+
CTrade         g_trade;
CSARFilters    g_filters;
CSARTrailing   g_trailing;
CSARRiskManager g_risk;

int    g_currentDirection;    // 1=Buy, -1=Sell, 0=Flat
ulong  g_currentTicket;
double g_entryPrice;
double g_pendingPrice;
ulong  g_pendingTicket;
bool   g_initialized;
int    g_totalReversals;
datetime g_lastBarTime;
bool   g_waitingReentry;
int    g_waitBarCount;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints((ulong)InpMaxSlippage);
   g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   
   if(!g_filters.Init(_Symbol, _Period, InpHTFPeriod,
                       InpADXPeriod, InpADXThreshold,
                       InpEMAFast, InpEMASlow,
                       InpATRPeriod, InpATRExpMult,
                       InpHTFEMAPeriod, InpVolumeThreshold))
   {
      Print("Failed to initialize filters");
      return INIT_FAILED;
   }
   
   if(!g_trailing.Init(_Symbol, _Period, InpATRPeriod,
                        InpTrailFixed, InpTrailATRMult,
                        InpChandelierMult, InpChandelierPeriod,
                        InpStepSize, InpStepDistance,
                        InpVolTrailMult))
   {
      Print("Failed to initialize trailing");
      return INIT_FAILED;
   }
   
   if(!g_risk.Init(_Symbol, _Period, InpATRPeriod,
                    InpMaxConsecRev, InpMaxDailyLoss,
                    InpMaxSpread, InpCooldownBars,
                    InpVolShutdownMult, InpEquityProtect,
                    InpMaxSlippage, InpRiskPercent))
   {
      Print("Failed to initialize risk manager");
      return INIT_FAILED;
   }
   
   g_currentDirection = 0;
   g_currentTicket = 0;
   g_pendingTicket = 0;
   g_entryPrice = 0;
   g_initialized = false;
   g_totalReversals = 0;
   g_lastBarTime = 0;
   g_waitingReentry = false;
   g_waitBarCount = 0;
   
   Print("SAR Expert Advisor initialized successfully");
   Print("Distance Mode: ", EnumToString(InpDistanceMode));
   Print("Trailing Mode: ", EnumToString(InpTrailingMode));
   Print("Filter Mode: ", EnumToString(InpTrendFilter));
   Print("Exit Mode: ", EnumToString(InpExitMode));
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   g_filters.Deinit();
   g_trailing.Deinit();
   g_risk.Deinit();
   
   Print("SAR EA deinitialized. Total reversals: ", g_totalReversals);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   g_risk.OnTick();
   
   // Check for new bar
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   bool isNewBar = (currentBarTime != g_lastBarTime);
   if(isNewBar)
      g_lastBarTime = currentBarTime;
   
   // Check if waiting for re-entry
   if(g_waitingReentry)
   {
      if(isNewBar) g_waitBarCount++;
      if(g_waitBarCount < InpWaitBars) return;
      g_waitingReentry = false;
      g_waitBarCount = 0;
   }
   
   // First trade initialization
   if(!g_initialized)
   {
      if(!g_risk.CanTrade()) return;
      
      int direction = DetermineStartDirection();
      if(direction == 0) return;
      
      if(OpenInitialTrade(direction))
      {
         g_initialized = true;
         Print("Initial trade opened: ", direction > 0 ? "BUY" : "SELL");
      }
      return;
   }
   
   // Check if current position still exists
   if(g_currentTicket > 0 && !PositionSelectByTicket(g_currentTicket))
   {
      // Position was closed externally or by TP
      g_currentDirection = 0;
      g_currentTicket = 0;
      
      if(InpExitMode == EXIT_WAIT_REENTRY)
      {
         g_waitingReentry = true;
         g_waitBarCount = 0;
         DeletePendingOrders();
         g_initialized = false;
         return;
      }
   }
   
   // Manage trailing stop
   if(g_currentDirection != 0 && InpTrailingMode != TRAIL_NONE)
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double price = (g_currentDirection > 0) ? bid : ask;
      
      if(g_trailing.ShouldClose(InpTrailingMode, g_currentDirection, price))
      {
         CloseCurrentPosition();
         
         if(InpExitMode == EXIT_TRAIL_ONLY || InpExitMode == EXIT_TP_AND_TRAIL)
         {
            DeletePendingOrders();
            
            if(InpExitMode == EXIT_TRAIL_ONLY)
            {
               g_initialized = false;
               g_waitingReentry = true;
               g_waitBarCount = 0;
            }
            return;
         }
      }
   }
   
   // Check pending order status
   CheckPendingOrders();
   
   // Ensure pending order exists when in position
   if(g_currentDirection != 0 && g_pendingTicket == 0)
   {
      PlaceReversalOrder();
   }
}

//+------------------------------------------------------------------+
//| Trade transaction handler                                        |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_ORDER_DELETE ||
      trans.type == TRADE_TRANSACTION_HISTORY_ADD)
   {
      if(trans.order == g_pendingTicket && trans.order_state == ORDER_STATE_FILLED)
      {
         // Pending order was filled - this is a reversal
         OnReversalTriggered(trans);
      }
   }
}

//+------------------------------------------------------------------+
//| Handle reversal trigger                                          |
//+------------------------------------------------------------------+
void OnReversalTriggered(const MqlTradeTransaction& trans)
{
   // Close old position
   if(g_currentTicket > 0 && PositionSelectByTicket(g_currentTicket))
   {
      double profit = PositionGetDouble(POSITION_PROFIT);
      g_trade.PositionClose(g_currentTicket);
      g_risk.OnTradeClose(profit);
   }
   
   // Update state
   g_currentDirection = -g_currentDirection;
   g_currentTicket = trans.position;
   g_entryPrice = trans.price;
   g_pendingTicket = 0;
   g_totalReversals++;
   
   g_risk.OnReversal();
   g_trailing.Reset(g_entryPrice, g_currentDirection);
   
   Print("Reversal #", g_totalReversals, " Direction: ", 
         g_currentDirection > 0 ? "BUY" : "SELL",
         " Price: ", g_entryPrice);
   
   // Check if risk allows continued trading
   if(!g_risk.CanTrade())
   {
      Print("Risk manager shutdown: ", g_risk.GetShutdownReason());
      CloseCurrentPosition();
      g_initialized = false;
      return;
   }
   
   // Check filters for new direction
   if(!g_filters.CompositeFilter(InpTrendFilter, g_currentDirection, InpSessionFilter))
   {
      if(InpUseHTF && !g_filters.HTFTrendFilter(g_currentDirection))
      {
         Print("Filter rejected new direction after reversal - closing");
         CloseCurrentPosition();
         g_initialized = false;
         g_waitingReentry = true;
         g_waitBarCount = 0;
         return;
      }
   }
   
   // Place new reversal order
   PlaceReversalOrder();
}

//+------------------------------------------------------------------+
//| Determine start direction                                        |
//+------------------------------------------------------------------+
int DetermineStartDirection()
{
   switch(InpStartDir)
   {
      case START_BUY:
         return 1;
      case START_SELL:
         return -1;
      case START_RANDOM:
         return (MathRand() % 2 == 0) ? 1 : -1;
      case START_TREND:
      {
         int htfDir = g_filters.GetHTFTrendDirection();
         if(htfDir != 0) return htfDir;
         
         // Fallback: use EMA
         double emaFast[], emaSlow[];
         int emaFastH = iMA(_Symbol, _Period, InpEMAFast, 0, MODE_EMA, PRICE_CLOSE);
         int emaSlowH = iMA(_Symbol, _Period, InpEMASlow, 0, MODE_EMA, PRICE_CLOSE);
         
         double ef[1], es[1];
         if(CopyBuffer(emaFastH, 0, 0, 1, ef) > 0 && CopyBuffer(emaSlowH, 0, 0, 1, es) > 0)
         {
            IndicatorRelease(emaFastH);
            IndicatorRelease(emaSlowH);
            return (ef[0] > es[0]) ? 1 : -1;
         }
         
         IndicatorRelease(emaFastH);
         IndicatorRelease(emaSlowH);
         return 1;
      }
      default:
         return 1;
   }
}

//+------------------------------------------------------------------+
//| Open initial trade                                               |
//+------------------------------------------------------------------+
bool OpenInitialTrade(int direction)
{
   // Check filters
   if(!g_filters.CompositeFilter(InpTrendFilter, direction, InpSessionFilter))
      return false;
   
   if(InpUseHTF && !g_filters.HTFTrendFilter(direction))
      return false;
   
   double price, tp = 0;
   double lots = GetLotSize();
   
   if(direction > 0)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price + InpTakeProfit * _Point;
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price - InpTakeProfit * _Point;
   }
   
   bool result;
   if(direction > 0)
      result = g_trade.Buy(lots, _Symbol, price, 0, tp, InpComment);
   else
      result = g_trade.Sell(lots, _Symbol, price, 0, tp, InpComment);
   
   if(result)
   {
      g_currentTicket = g_trade.ResultOrder();
      g_currentDirection = direction;
      g_entryPrice = price;
      g_trailing.Reset(price, direction);
      
      // Place reversal pending order
      PlaceReversalOrder();
      return true;
   }
   
   Print("Failed to open initial trade: ", g_trade.ResultRetcodeDescription());
   return false;
}

//+------------------------------------------------------------------+
//| Calculate reversal distance                                      |
//+------------------------------------------------------------------+
double GetReversalDistance()
{
   double distance = 0;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   switch(InpDistanceMode)
   {
      case DISTANCE_FIXED:
         distance = InpFixedDistance * point;
         break;
         
      case DISTANCE_ATR:
      {
         double atr = g_filters.GetATR();
         if(atr > 0)
            distance = atr * InpATRDistanceMult;
         else
            distance = InpFixedDistance * point;
         break;
      }
      
      case DISTANCE_VOLATILITY:
      {
         double atr = g_filters.GetATR();
         double atrHTF = g_filters.GetATRHTF();
         if(atr > 0 && atrHTF > 0)
         {
            double volRatio = atr / atrHTF;
            distance = atr * InpATRDistanceMult * (1.0 + volRatio);
         }
         else
            distance = InpFixedDistance * point;
         break;
      }
      
      case DISTANCE_SESSION:
      {
         MqlDateTime dt;
         TimeCurrent(dt);
         double atr = g_filters.GetATR();
         
         // Adjust distance by session volatility
         double sessionMult = 1.0;
         if(dt.hour >= 8 && dt.hour < 12)       sessionMult = 1.2;  // London morning
         else if(dt.hour >= 13 && dt.hour < 17)  sessionMult = 1.3;  // London+NY overlap
         else if(dt.hour >= 17 && dt.hour < 22)  sessionMult = 1.0;  // NY afternoon
         else                                     sessionMult = 0.8;  // Asian
         
         if(atr > 0)
            distance = atr * InpATRDistanceMult * sessionMult;
         else
            distance = InpFixedDistance * point * sessionMult;
         break;
      }
      
      case DISTANCE_SPREAD_ADJ:
      {
         double spread = g_filters.GetSpread();
         double atr = g_filters.GetATR();
         if(atr > 0)
            distance = atr * InpATRDistanceMult + spread * 2;
         else
            distance = InpFixedDistance * point + spread * 2;
         break;
      }
   }
   
   // Minimum distance: at least 2x spread
   double minDist = g_filters.GetSpread() * 3;
   if(distance < minDist)
      distance = minDist;
   
   return distance;
}

//+------------------------------------------------------------------+
//| Place reversal pending order                                     |
//+------------------------------------------------------------------+
bool PlaceReversalOrder()
{
   // Delete existing pending orders first
   DeletePendingOrders();
   
   double distance = GetReversalDistance();
   double lots = GetLotSize();
   double price, tp = 0;
   
   if(g_currentDirection > 0)
   {
      // Currently long - place Sell Stop below
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID) - distance;
      price = NormalizeDouble(price, _Digits);
      
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price - InpTakeProfit * _Point;
      
      if(!g_trade.SellStop(lots, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, InpComment + "_REV"))
      {
         Print("Failed to place Sell Stop: ", g_trade.ResultRetcodeDescription());
         return false;
      }
   }
   else
   {
      // Currently short - place Buy Stop above
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + distance;
      price = NormalizeDouble(price, _Digits);
      
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price + InpTakeProfit * _Point;
      
      if(!g_trade.BuyStop(lots, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, InpComment + "_REV"))
      {
         Print("Failed to place Buy Stop: ", g_trade.ResultRetcodeDescription());
         return false;
      }
   }
   
   g_pendingTicket = g_trade.ResultOrder();
   g_pendingPrice = price;
   
   return true;
}

//+------------------------------------------------------------------+
//| Check pending order status                                       |
//+------------------------------------------------------------------+
void CheckPendingOrders()
{
   if(g_pendingTicket == 0) return;
   
   if(!OrderSelect(g_pendingTicket))
   {
      // Order no longer exists - was filled or deleted
      g_pendingTicket = 0;
   }
}

//+------------------------------------------------------------------+
//| Close current position                                           |
//+------------------------------------------------------------------+
void CloseCurrentPosition()
{
   if(g_currentTicket > 0 && PositionSelectByTicket(g_currentTicket))
   {
      double profit = PositionGetDouble(POSITION_PROFIT);
      g_trade.PositionClose(g_currentTicket);
      g_risk.OnTradeClose(profit);
   }
   
   g_currentTicket = 0;
   g_currentDirection = 0;
   g_entryPrice = 0;
   
   DeletePendingOrders();
}

//+------------------------------------------------------------------+
//| Delete all pending orders                                        |
//+------------------------------------------------------------------+
void DeletePendingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderGetInteger(ORDER_MAGIC) == InpMagicNumber &&
            OrderGetString(ORDER_SYMBOL) == _Symbol)
         {
            g_trade.OrderDelete(ticket);
         }
      }
   }
   g_pendingTicket = 0;
}

//+------------------------------------------------------------------+
//| Get lot size based on risk settings                              |
//+------------------------------------------------------------------+
double GetLotSize()
{
   if(InpRiskPercent > 0)
   {
      double distance = GetReversalDistance();
      double distPoints = distance / _Point;
      return g_risk.CalculateLotSize(distPoints);
   }
   return InpFixedLots;
}
//+------------------------------------------------------------------+
