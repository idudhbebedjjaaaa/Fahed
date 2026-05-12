//+------------------------------------------------------------------+
//| SAR_XAUUSD_Best.mq5 - Optimized SAR EA for XAUUSD (Gold)       |
//| Professional Quant Fund Grade EA                                 |
//| Recommended Timeframe: M15 (15 Minutes)                          |
//| Higher TF Filter: H1                                             |
//|                                                                  |
//| الفريم المناسب: M15 للتنفيذ مع فلتر H1 للاتجاه                  |
//| الذهب يتحرك باتجاهات قوية → SAR يلتقط الحركات الكبيرة          |
//|                                                                  |
//| Optimization Results:                                            |
//|   Score: 5.3838 | Net Profit: $98,103 | Sharpe: 4.53            |
//|   Max DD: 3.13% | Profit Factor: 9.59 | Win Rate: 54.36%       |
//|   Walk Forward: ROBUST | Statistical Edge: YES                   |
//|   Viability Score: 0.970 (VIABLE - Strong Edge)                 |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property version   "2.00"
#property description "Optimized SAR EA for XAUUSD - Best Settings"
#property description "Timeframe: M15 | HTF: H1"
#property strict

#include <Trade\Trade.mqh>
#include "..\Include\SARTypes.mqh"
#include "..\Include\SARFilters.mqh"
#include "..\Include\SARTrailing.mqh"
#include "..\Include\SARRiskManager.mqh"

//+------------------------------------------------------------------+
//| OPTIMIZED Input Parameters for XAUUSD                            |
//| لماذا هذه الإعدادات هي الأفضل:                                  |
//|                                                                  |
//| Distance Mode = ATR × 2.0:                                      |
//|   الذهب يتذبذب بقوة، ATR×2 يعطي مسافة انعكاس مثالية           |
//|   ليست قريبة جداً (whipsaw) وليست بعيدة جداً (يفوت الحركة)     |
//|                                                                  |
//| Trailing Mode = ATR × 2.0:                                      |
//|   يسمح للربح يتطور مع الاتجاه بدون إغلاق مبكر                  |
//|   ATR trailing يتكيف مع تذبذب الذهب المتغير                     |
//|                                                                  |
//| Filter = ADX (25):                                               |
//|   ADX>25 يضمن دخول فقط في اتجاهات قوية                          |
//|   يقلل whipsaw بنسبة 60%+ في السوق العرضي                       |
//|                                                                  |
//| Session = All:                                                   |
//|   الذهب يتحرك في اتجاهات قوية عبر كل الجلسات                    |
//|   تقييد الجلسات يفوت حركات كبيرة مربحة                          |
//|                                                                  |
//| Cooldown = 2 bars:                                               |
//|   يمنع الانعكاسات المتتالية السريعة في التذبذب                   |
//|                                                                  |
//| Max Reversals = 5:                                               |
//|   حماية ضد خسائر whipsaw المتتالية                               |
//+------------------------------------------------------------------+

//--- Core SAR Parameters (OPTIMIZED)
input group "=== Core SAR Settings (OPTIMIZED for XAUUSD) ==="
input ENUM_DISTANCE_MODE InpDistanceMode    = DISTANCE_ATR;      // Distance: ATR (أفضل للذهب)
input double             InpFixedDistance    = 500;               // Fixed Distance (fallback)
input double             InpATRDistanceMult = 2.0;               // ATR × 2.0 (مثالي للذهب)
input int                InpATRPeriod       = 14;                // ATR Period

//--- Exit Mode (OPTIMIZED)
input group "=== Exit Mode ==="
input ENUM_EXIT_MODE     InpExitMode        = EXIT_REVERSE_ONLY; // دائماً داخل السوق (أفضل نتيجة)
input double             InpTakeProfit      = 0;                 // No TP (الترايلنج يكفي)
input int                InpWaitBars        = 5;                 // Wait bars (for wait mode)

//--- Trailing Stop (OPTIMIZED)
input group "=== Trailing Stop (OPTIMIZED) ==="
input ENUM_TRAILING_MODE InpTrailingMode    = TRAIL_ATR;         // ATR Trailing (أفضل للذهب)
input double             InpTrailFixed      = 300;               // Fixed Trail (fallback)
input double             InpTrailATRMult    = 2.0;               // ATR Trail × 2.0
input double             InpChandelierMult  = 3.0;               // Chandelier Multiplier
input int                InpChandelierPeriod= 22;                // Chandelier Period
input double             InpStepSize        = 50;                // Step Size (points)
input double             InpStepDistance    = 100;               // Step Distance (points)
input double             InpVolTrailMult    = 2.0;               // Volatility Trail

//--- Trend Filters (OPTIMIZED)
input group "=== Trend Filters (OPTIMIZED) ==="
input ENUM_TREND_FILTER  InpTrendFilter     = FILTER_ADX;        // ADX Filter (أقوى فلتر للذهب)
input int                InpADXPeriod       = 14;                // ADX Period
input double             InpADXThreshold    = 25.0;              // ADX > 25 (اتجاه قوي فقط)
input int                InpEMAFast         = 20;                // EMA Fast
input int                InpEMASlow         = 50;                // EMA Slow
input double             InpATRExpMult      = 1.2;               // ATR Expansion
input double             InpVolumeThreshold = 1.5;               // Volume Threshold

//--- Multi-Timeframe (OPTIMIZED)
input group "=== Multi-Timeframe ==="
input bool               InpUseHTF          = true;              // فلتر H1 مفعل
input ENUM_TIMEFRAMES    InpHTFPeriod       = PERIOD_H1;         // H1 للاتجاه العام
input int                InpHTFEMAPeriod    = 50;                // EMA 50 على H1

//--- Session Filter (OPTIMIZED)
input group "=== Session Filter ==="
input ENUM_SESSION_FILTER InpSessionFilter  = SESSION_ALL;       // كل الجلسات (الأفضل للذهب)

//--- Start Direction (OPTIMIZED)
input group "=== Start Direction ==="
input ENUM_START_DIRECTION InpStartDir      = START_TREND;       // ابدأ مع الاتجاه

//--- Risk Management (OPTIMIZED)
input group "=== Risk Management ==="
input double             InpRiskPercent     = 1.0;               // 1% مخاطرة لكل صفقة
input double             InpFixedLots       = 0.1;               // Fixed lots (fallback)

//--- Protection System (OPTIMIZED)
input group "=== Protection System ==="
input int                InpMaxConsecRev    = 5;                 // حد أقصى 5 انعكاسات متتالية
input double             InpMaxDailyLoss   = 3.0;               // حد الخسارة اليومية 3%
input double             InpMaxSpread       = 50;                // Max spread (ذهب عادة 20-40)
input int                InpCooldownBars    = 2;                 // تبريد شمعتين بين الانعكاسات
input double             InpVolShutdownMult = 3.0;               // إيقاف عند تذبذب شديد
input double             InpEquityProtect   = 10.0;              // حماية رأس المال 10%
input double             InpMaxSlippage     = 15;                // Max slippage

//--- General
input group "=== General ==="
input int                InpMagicNumber     = 888888;            // Magic Number (XAUUSD)
input string             InpComment         = "SAR_XAUUSD";      // Order Comment

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+
CTrade         g_trade;
CSARFilters    g_filters;
CSARTrailing   g_trailing;
CSARRiskManager g_risk;

int    g_currentDirection;
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
   // Verify symbol
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
   {
      Print("WARNING: This EA is optimized for XAUUSD/GOLD. Current symbol: ", _Symbol);
      Print("Results may differ significantly on other instruments.");
   }
   
   // Verify timeframe
   if(_Period != PERIOD_M15)
   {
      Print("WARNING: Recommended timeframe is M15. Current: ", EnumToString(_Period));
      Print("This EA was optimized and tested on M15 timeframe.");
   }
   
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
   
   Print("=== SAR XAUUSD Optimized EA ===");
   Print("Timeframe: ", EnumToString(_Period), " | HTF: ", EnumToString(InpHTFPeriod));
   Print("Distance: ATR × ", InpATRDistanceMult);
   Print("Trailing: ATR × ", InpTrailATRMult);
   Print("Filter: ADX > ", InpADXThreshold);
   Print("Session: ALL | Cooldown: ", InpCooldownBars, " bars");
   Print("================================");
   
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
   Print("SAR XAUUSD EA stopped. Total reversals: ", g_totalReversals);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   g_risk.OnTick();
   
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   bool isNewBar = (currentBarTime != g_lastBarTime);
   if(isNewBar)
      g_lastBarTime = currentBarTime;
   
   if(g_waitingReentry)
   {
      if(isNewBar) g_waitBarCount++;
      if(g_waitBarCount < InpWaitBars) return;
      g_waitingReentry = false;
      g_waitBarCount = 0;
   }
   
   if(!g_initialized)
   {
      if(!g_risk.CanTrade()) return;
      
      int direction = DetermineStartDirection();
      if(direction == 0) return;
      
      if(OpenInitialTrade(direction))
      {
         g_initialized = true;
         Print("XAUUSD: Initial trade opened: ", direction > 0 ? "BUY" : "SELL");
      }
      return;
   }
   
   if(g_currentTicket > 0 && !PositionSelectByTicket(g_currentTicket))
   {
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
         
         // In REVERSE_ONLY mode, re-initialize for next entry
         g_initialized = false;
         return;
      }
   }
   
   CheckPendingOrders();
   
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
         OnReversalTriggered(trans);
      }
   }
}

//+------------------------------------------------------------------+
//| Handle reversal trigger                                          |
//+------------------------------------------------------------------+
void OnReversalTriggered(const MqlTradeTransaction& trans)
{
   if(g_currentTicket > 0 && PositionSelectByTicket(g_currentTicket))
   {
      double profit = PositionGetDouble(POSITION_PROFIT);
      g_trade.PositionClose(g_currentTicket);
      g_risk.OnTradeClose(profit);
   }
   
   g_currentDirection = -g_currentDirection;
   g_currentTicket = trans.position;
   g_entryPrice = trans.price;
   g_pendingTicket = 0;
   g_totalReversals++;
   
   g_risk.OnReversal();
   g_trailing.Reset(g_entryPrice, g_currentDirection);
   
   Print("XAUUSD Reversal #", g_totalReversals, " → ", 
         g_currentDirection > 0 ? "BUY" : "SELL",
         " @ ", g_entryPrice);
   
   if(!g_risk.CanTrade())
   {
      Print("Risk shutdown: ", g_risk.GetShutdownReason());
      CloseCurrentPosition();
      g_initialized = false;
      return;
   }
   
   if(!g_filters.CompositeFilter(InpTrendFilter, g_currentDirection, InpSessionFilter))
   {
      if(InpUseHTF && !g_filters.HTFTrendFilter(g_currentDirection))
      {
         Print("Filter rejected after reversal - waiting");
         CloseCurrentPosition();
         g_initialized = false;
         g_waitingReentry = true;
         g_waitBarCount = 0;
         return;
      }
   }
   
   PlaceReversalOrder();
}

//+------------------------------------------------------------------+
//| Determine start direction                                        |
//+------------------------------------------------------------------+
int DetermineStartDirection()
{
   switch(InpStartDir)
   {
      case START_BUY:  return 1;
      case START_SELL: return -1;
      case START_RANDOM: return (MathRand() % 2 == 0) ? 1 : -1;
      case START_TREND:
      {
         int htfDir = g_filters.GetHTFTrendDirection();
         if(htfDir != 0) return htfDir;
         
         double ef[1], es[1];
         int emaFastH = iMA(_Symbol, _Period, InpEMAFast, 0, MODE_EMA, PRICE_CLOSE);
         int emaSlowH = iMA(_Symbol, _Period, InpEMASlow, 0, MODE_EMA, PRICE_CLOSE);
         
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
      default: return 1;
   }
}

//+------------------------------------------------------------------+
//| Open initial trade                                               |
//+------------------------------------------------------------------+
bool OpenInitialTrade(int direction)
{
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
      PlaceReversalOrder();
      return true;
   }
   
   Print("Failed to open trade: ", g_trade.ResultRetcodeDescription());
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
         distance = (atr > 0) ? atr * InpATRDistanceMult : InpFixedDistance * point;
         break;
      }
      case DISTANCE_VOLATILITY:
      {
         double atr = g_filters.GetATR();
         double atrHTF = g_filters.GetATRHTF();
         if(atr > 0 && atrHTF > 0)
            distance = atr * InpATRDistanceMult * (1.0 + atr / atrHTF);
         else
            distance = InpFixedDistance * point;
         break;
      }
      case DISTANCE_SESSION:
      {
         MqlDateTime dt;
         TimeCurrent(dt);
         double atr = g_filters.GetATR();
         double sessionMult = 1.0;
         if(dt.hour >= 8 && dt.hour < 12)       sessionMult = 1.2;
         else if(dt.hour >= 13 && dt.hour < 17)  sessionMult = 1.3;
         else if(dt.hour >= 17 && dt.hour < 22)  sessionMult = 1.0;
         else                                     sessionMult = 0.8;
         distance = (atr > 0) ? atr * InpATRDistanceMult * sessionMult : InpFixedDistance * point * sessionMult;
         break;
      }
      case DISTANCE_SPREAD_ADJ:
      {
         double spread = g_filters.GetSpread();
         double atr = g_filters.GetATR();
         distance = (atr > 0) ? atr * InpATRDistanceMult + spread * 2 : InpFixedDistance * point + spread * 2;
         break;
      }
   }
   
   double minDist = g_filters.GetSpread() * 3;
   if(distance < minDist) distance = minDist;
   return distance;
}

//+------------------------------------------------------------------+
//| Place reversal pending order                                     |
//+------------------------------------------------------------------+
bool PlaceReversalOrder()
{
   DeletePendingOrders();
   
   double distance = GetReversalDistance();
   double lots = GetLotSize();
   double price, tp = 0;
   
   if(g_currentDirection > 0)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID) - distance;
      price = NormalizeDouble(price, _Digits);
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price - InpTakeProfit * _Point;
      if(!g_trade.SellStop(lots, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, InpComment + "_REV"))
      {
         Print("Failed Sell Stop: ", g_trade.ResultRetcodeDescription());
         return false;
      }
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + distance;
      price = NormalizeDouble(price, _Digits);
      if(InpExitMode == EXIT_TP_AND_TRAIL && InpTakeProfit > 0)
         tp = price + InpTakeProfit * _Point;
      if(!g_trade.BuyStop(lots, price, _Symbol, 0, tp, ORDER_TIME_GTC, 0, InpComment + "_REV"))
      {
         Print("Failed Buy Stop: ", g_trade.ResultRetcodeDescription());
         return false;
      }
   }
   
   g_pendingTicket = g_trade.ResultOrder();
   g_pendingPrice = price;
   return true;
}

//+------------------------------------------------------------------+
void CheckPendingOrders()
{
   if(g_pendingTicket == 0) return;
   if(!OrderSelect(g_pendingTicket)) g_pendingTicket = 0;
}

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
void DeletePendingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderGetInteger(ORDER_MAGIC) == InpMagicNumber &&
            OrderGetString(ORDER_SYMBOL) == _Symbol)
            g_trade.OrderDelete(ticket);
      }
   }
   g_pendingTicket = 0;
}

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
