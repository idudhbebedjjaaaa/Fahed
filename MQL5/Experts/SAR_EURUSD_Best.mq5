//+------------------------------------------------------------------+
//| SAR_EURUSD_Best.mq5 - Optimized SAR EA for EURUSD               |
//| Professional Quant Fund Grade EA                                 |
//| Recommended Timeframe: M15 (15 Minutes)                          |
//| Higher TF Filter: H1                                             |
//|                                                                  |
//| الفريم المناسب: M15 للتنفيذ مع فلتر H1 للاتجاه                  |
//| ⚠ تحذير: EURUSD أضعف من XAUUSD - استخدم مع حذر                  |
//|                                                                  |
//| Optimization Results:                                            |
//|   Score: 0.5915 | Net Profit: $455 | Sharpe: 0.78               |
//|   Max DD: ~10% | Walk Forward: NOT Robust                        |
//|   Viability Score: 0.365 (MARGINAL)                              |
//|                                                                  |
//| لماذا EURUSD أضعف:                                               |
//|   - أقل اتجاهية من الذهب                                         |
//|   - أكثر عرضة للتذبذب العرضي (whipsaw)                           |
//|   - تكاليف التداول تأكل جزء كبير من الأرباح                      |
//|   - يحتاج فلاتر أقوى (Composite) للحماية                         |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property version   "2.00"
#property description "Optimized SAR EA for EURUSD - Best Settings"
#property description "Timeframe: M15 | HTF: H1"
#property description "WARNING: Marginal edge - use with caution"
#property strict

#include <Trade\Trade.mqh>
#include "..\Include\SARTypes.mqh"
#include "..\Include\SARFilters.mqh"
#include "..\Include\SARTrailing.mqh"
#include "..\Include\SARRiskManager.mqh"

//+------------------------------------------------------------------+
//| OPTIMIZED Input Parameters for EURUSD                            |
//| لماذا هذه الإعدادات هي الأفضل:                                  |
//|                                                                  |
//| Distance Mode = Volatility Adaptive × 3.0:                      |
//|   أوسع من ATR العادي لتقليل whipsaw                              |
//|   × 3.0 يعطي هامش أمان ضد التذبذب العرضي                        |
//|   Adaptive يتكيف تلقائياً مع تغير volatility                     |
//|                                                                  |
//| Trailing Mode = Volatility:                                      |
//|   يتكيف مع ظروف السوق المتغيرة                                   |
//|   أفضل من ATR الثابت لأن EURUSD يمر بفترات تذبذب مختلفة         |
//|                                                                  |
//| Filter = Composite (ADX + EMA + ATR Expansion):                  |
//|   أقوى فلتر متاح - يجمع 3 شروط                                   |
//|   ضروري لـ EURUSD لتجنب الأسواق العرضية                          |
//|   يقلل عدد الصفقات لكن يحسن الجودة بشكل كبير                    |
//|                                                                  |
//| Session = London+NY Overlap:                                     |
//|   أعلى احتمال لحركات اتجاهية قوية                                |
//|   أقل whipsaw مقارنة بالتداول طوال اليوم                         |
//|   حجم تداول أكبر = سبريد أقل                                     |
//|                                                                  |
//| Cooldown = 2 bars:                                               |
//|   يمنع الانعكاسات المتتالية السريعة                               |
//|                                                                  |
//| Max Reversals = 5:                                               |
//|   حد أقصى للحماية من whipsaw المدمر                              |
//+------------------------------------------------------------------+

//--- Core SAR Parameters (OPTIMIZED)
input group "=== Core SAR Settings (OPTIMIZED for EURUSD) ==="
input ENUM_DISTANCE_MODE InpDistanceMode    = DISTANCE_VOLATILITY; // Volatility Adaptive (أفضل لـ EURUSD)
input double             InpFixedDistance    = 200;               // Fixed Distance (fallback)
input double             InpATRDistanceMult = 3.0;               // ATR × 3.0 (أوسع = أقل whipsaw)
input int                InpATRPeriod       = 14;                // ATR Period

//--- Exit Mode (OPTIMIZED)
input group "=== Exit Mode ==="
input ENUM_EXIT_MODE     InpExitMode        = EXIT_REVERSE_ONLY; // دائماً داخل السوق
input double             InpTakeProfit      = 0;                 // No TP
input int                InpWaitBars        = 5;                 // Wait bars

//--- Trailing Stop (OPTIMIZED)
input group "=== Trailing Stop (OPTIMIZED) ==="
input ENUM_TRAILING_MODE InpTrailingMode    = TRAIL_VOLATILITY;  // Volatility Trailing (أفضل لـ EURUSD)
input double             InpTrailFixed      = 150;               // Fixed Trail (fallback)
input double             InpTrailATRMult    = 1.5;               // ATR Trail × 1.5
input double             InpChandelierMult  = 3.0;               // Chandelier
input int                InpChandelierPeriod= 22;                // Chandelier Period
input double             InpStepSize        = 20;                // Step Size
input double             InpStepDistance    = 50;                // Step Distance
input double             InpVolTrailMult    = 2.0;               // Volatility Trail × 2.0

//--- Trend Filters (OPTIMIZED)
input group "=== Trend Filters (OPTIMIZED) ==="
input ENUM_TREND_FILTER  InpTrendFilter     = FILTER_COMPOSITE;  // Composite (أقوى فلتر ضد whipsaw)
input int                InpADXPeriod       = 14;                // ADX Period
input double             InpADXThreshold    = 20.0;              // ADX > 20
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
input ENUM_SESSION_FILTER InpSessionFilter  = SESSION_LONDON_NY; // London+NY فقط (أفضل لـ EURUSD)

//--- Start Direction (OPTIMIZED)
input group "=== Start Direction ==="
input ENUM_START_DIRECTION InpStartDir      = START_TREND;       // ابدأ مع الاتجاه

//--- Risk Management (OPTIMIZED)
input group "=== Risk Management ==="
input double             InpRiskPercent     = 0.5;               // 0.5% فقط (حذر - edge ضعيف)
input double             InpFixedLots       = 0.05;              // Fixed lots (أصغر حجم)

//--- Protection System (OPTIMIZED)
input group "=== Protection System ==="
input int                InpMaxConsecRev    = 5;                 // حد أقصى 5 انعكاسات
input double             InpMaxDailyLoss   = 2.0;               // حد الخسارة 2% (أشد حماية)
input double             InpMaxSpread       = 20;                // Max spread (EURUSD عادة 1-3)
input int                InpCooldownBars    = 2;                 // تبريد شمعتين
input double             InpVolShutdownMult = 3.0;               // إيقاف عند تذبذب شديد
input double             InpEquityProtect   = 8.0;               // حماية 8% (أشد من XAUUSD)
input double             InpMaxSlippage     = 5;                 // Max slippage

//--- General
input group "=== General ==="
input int                InpMagicNumber     = 777777;            // Magic Number (EURUSD)
input string             InpComment         = "SAR_EURUSD";      // Order Comment

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
   if(StringFind(_Symbol, "EUR") < 0)
   {
      Print("WARNING: This EA is optimized for EURUSD. Current symbol: ", _Symbol);
      Print("Results may differ significantly on other instruments.");
   }
   
   // Verify timeframe
   if(_Period != PERIOD_M15)
   {
      Print("WARNING: Recommended timeframe is M15. Current: ", EnumToString(_Period));
   }
   
   Print("=== ⚠ IMPORTANT WARNING ⚠ ===");
   Print("EURUSD SAR has MARGINAL edge (Score: 0.365)");
   Print("Walk Forward test: NOT Robust");
   Print("Use with strict risk management and small lot sizes");
   Print("Consider this as supplementary strategy only");
   Print("================================");
   
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
   
   Print("=== SAR EURUSD Optimized EA ===");
   Print("Timeframe: ", EnumToString(_Period), " | HTF: ", EnumToString(InpHTFPeriod));
   Print("Distance: Volatility × ", InpATRDistanceMult);
   Print("Trailing: Volatility × ", InpVolTrailMult);
   Print("Filter: COMPOSITE (ADX+EMA+ATR Expansion)");
   Print("Session: London+NY Overlap only");
   Print("Risk: ", InpRiskPercent, "% (conservative)");
   Print("================================");
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   g_filters.Deinit();
   g_trailing.Deinit();
   g_risk.Deinit();
   Print("SAR EURUSD EA stopped. Total reversals: ", g_totalReversals);
}

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
         Print("EURUSD: Initial trade: ", direction > 0 ? "BUY" : "SELL");
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
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_ORDER_DELETE ||
      trans.type == TRADE_TRANSACTION_HISTORY_ADD)
   {
      if(trans.order == g_pendingTicket && trans.order_state == ORDER_STATE_FILLED)
         OnReversalTriggered(trans);
   }
}

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
   
   Print("EURUSD Reversal #", g_totalReversals, " → ", 
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
         Print("Filter rejected - waiting");
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
   Print("Failed: ", g_trade.ResultRetcodeDescription());
   return false;
}

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
