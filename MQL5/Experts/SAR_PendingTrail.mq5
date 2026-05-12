//+------------------------------------------------------------------+
//| SAR_PendingTrail.mq5 - Stop-And-Reverse via Pending Orders       |
//| Uses Sell Stop / Buy Stop as trailing stop replacement            |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property version   "1.00"
#property description "SAR EA: Trailing Stop via Pending Stop Orders"
#property description "Buy → Sell Stop trails up | Sell → Buy Stop trails down"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                 |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input double InpStopDistance     = 100;       // Stop Distance (points)
input double InpLotSize          = 0.1;       // Lot Size
input int    InpMagicNumber      = 888888;    // Magic Number
input string InpComment          = "SAR_PT";  // Order Comment

input group "=== Trailing Settings ==="
input double InpTrailStep        = 10;        // Trailing Step (points) - min price move to update
input bool   InpUseTrailing      = true;      // Enable Trailing of Pending Order

input group "=== Start Direction ==="
input ENUM_ORDER_TYPE InpStartDirection = ORDER_TYPE_BUY; // First Trade Direction (Buy/Sell)

//+------------------------------------------------------------------+
//| Global Variables                                                 |
//+------------------------------------------------------------------+
CTrade g_trade;

int    g_direction;        // 1 = Buy active, -1 = Sell active, 0 = no position
ulong  g_posTicket;        // current position ticket
ulong  g_pendingTicket;    // current pending order ticket
double g_pendingPrice;     // current pending order price
double g_bestPrice;        // best price since entry (for trailing)
bool   g_initialized;      // first trade placed?
int    g_reversalCount;    // total reversals counter

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(10);
   g_trade.SetTypeFilling(ORDER_FILLING_IOC);

   g_direction     = 0;
   g_posTicket     = 0;
   g_pendingTicket = 0;
   g_pendingPrice  = 0;
   g_bestPrice     = 0;
   g_initialized   = false;
   g_reversalCount = 0;

   Print("SAR PendingTrail EA initialized");
   Print("Stop Distance: ", InpStopDistance, " points");
   Print("Trailing: ", InpUseTrailing ? "ON" : "OFF",
         ", Step: ", InpTrailStep, " points");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("SAR PendingTrail EA stopped. Reversals: ", g_reversalCount);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Open first trade
   if(!g_initialized)
   {
      int dir = (InpStartDirection == ORDER_TYPE_BUY) ? 1 : -1;
      if(OpenTrade(dir))
      {
         g_initialized = true;
         PlacePendingOrder();
      }
      return;
   }

   //--- Check if our position still exists
   if(g_posTicket > 0 && !PositionSelectByTicket(g_posTicket))
   {
      // Position closed externally - check if pending triggered
      if(g_pendingTicket > 0 && !OrderSelect(g_pendingTicket))
      {
         // Pending order also gone - likely filled via OnTradeTransaction
         // State is handled there
      }
      else if(g_pendingTicket > 0)
      {
         // Position gone but pending still exists - external close
         // Delete pending and reset
         DeleteAllPending();
         g_direction = 0;
         g_posTicket = 0;
         g_initialized = false;
         Print("Position closed externally - resetting");
      }
      return;
   }

   //--- Ensure pending order exists
   if(g_direction != 0 && g_pendingTicket == 0)
   {
      PlacePendingOrder();
   }

   //--- Trail the pending order
   if(g_direction != 0 && g_pendingTicket > 0 && InpUseTrailing)
   {
      TrailPendingOrder();
   }
}

//+------------------------------------------------------------------+
//| Trade transaction handler - detects pending order fill            |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   // Detect when our pending order is filled
   if(trans.type == TRADE_TRANSACTION_HISTORY_ADD)
   {
      if(trans.order == g_pendingTicket &&
         trans.order_state == ORDER_STATE_FILLED)
      {
         OnPendingFilled(trans);
      }
   }
}

//+------------------------------------------------------------------+
//| Pending order was filled - handle the reversal                   |
//+------------------------------------------------------------------+
void OnPendingFilled(const MqlTradeTransaction& trans)
{
   // Close the old position
   if(g_posTicket > 0 && PositionSelectByTicket(g_posTicket))
   {
      g_trade.PositionClose(g_posTicket);
   }

   // Reverse direction
   g_direction = -g_direction;
   g_posTicket = trans.position;
   g_pendingTicket = 0;
   g_pendingPrice  = 0;
   g_reversalCount++;

   // Reset best price for trailing
   if(g_direction > 0)
      g_bestPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   else
      g_bestPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   Print("=== REVERSAL #", g_reversalCount, " ===",
         " New Direction: ", g_direction > 0 ? "BUY" : "SELL",
         " Price: ", DoubleToString(trans.price, _Digits));

   // Place new pending order in opposite direction
   PlacePendingOrder();
}

//+------------------------------------------------------------------+
//| Open a market order                                              |
//+------------------------------------------------------------------+
bool OpenTrade(int direction)
{
   double price;
   bool ok;

   if(direction > 0)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      ok = g_trade.Buy(InpLotSize, _Symbol, price, 0, 0, InpComment);
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      ok = g_trade.Sell(InpLotSize, _Symbol, price, 0, 0, InpComment);
   }

   if(ok)
   {
      g_posTicket = g_trade.ResultOrder();
      g_direction = direction;
      g_bestPrice = price;

      Print("Opened ", direction > 0 ? "BUY" : "SELL",
            " at ", DoubleToString(price, _Digits),
            " Ticket: ", g_posTicket);
      return true;
   }

   Print("Failed to open trade: ", g_trade.ResultRetcodeDescription());
   return false;
}

//+------------------------------------------------------------------+
//| Place a pending stop order opposite to current direction         |
//+------------------------------------------------------------------+
bool PlacePendingOrder()
{
   DeleteAllPending();

   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double dist    = InpStopDistance * point;
   double price;
   bool ok;

   if(g_direction > 0)
   {
      // Long position → place Sell Stop below current price
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID) - dist;
      price = NormalizeDouble(price, _Digits);

      // Validate minimum distance from current price
      double minStopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(bid - price < minStopLevel)
         price = NormalizeDouble(bid - minStopLevel - point, _Digits);

      ok = g_trade.SellStop(InpLotSize, price, _Symbol,
                            0, 0, ORDER_TIME_GTC, 0,
                            InpComment + "_REV");
   }
   else
   {
      // Short position → place Buy Stop above current price
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + dist;
      price = NormalizeDouble(price, _Digits);

      double minStopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(price - ask < minStopLevel)
         price = NormalizeDouble(ask + minStopLevel + point, _Digits);

      ok = g_trade.BuyStop(InpLotSize, price, _Symbol,
                           0, 0, ORDER_TIME_GTC, 0,
                           InpComment + "_REV");
   }

   if(ok)
   {
      g_pendingTicket = g_trade.ResultOrder();
      g_pendingPrice  = price;

      Print("Placed ", g_direction > 0 ? "SELL STOP" : "BUY STOP",
            " at ", DoubleToString(price, _Digits),
            " Ticket: ", g_pendingTicket);
      return true;
   }

   Print("Failed to place pending order: ", g_trade.ResultRetcodeDescription());
   return false;
}

//+------------------------------------------------------------------+
//| Trail the pending order as price moves in our favor              |
//+------------------------------------------------------------------+
void TrailPendingOrder()
{
   if(g_pendingTicket == 0) return;
   if(!OrderSelect(g_pendingTicket)) { g_pendingTicket = 0; return; }

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double dist  = InpStopDistance * point;
   double step  = InpTrailStep * point;
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   double newPrice = 0;

   if(g_direction > 0)
   {
      // Long: if price went up, trail Sell Stop upward
      if(bid > g_bestPrice + step)
      {
         g_bestPrice = bid;
         newPrice = NormalizeDouble(bid - dist, _Digits);

         // Only move UP (tighter), never down
         if(newPrice <= g_pendingPrice)
            return;
      }
      else
         return;
   }
   else
   {
      // Short: if price went down, trail Buy Stop downward
      if(ask < g_bestPrice - step)
      {
         g_bestPrice = ask;
         newPrice = NormalizeDouble(ask + dist, _Digits);

         // Only move DOWN (tighter), never up
         if(newPrice >= g_pendingPrice)
            return;
      }
      else
         return;
   }

   // Validate minimum distance
   double minStopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(g_direction > 0)
   {
      if(bid - newPrice < minStopLevel)
         return;
   }
   else
   {
      if(newPrice - ask < minStopLevel)
         return;
   }

   // Modify the pending order price
   if(g_trade.OrderModify(g_pendingTicket, newPrice, 0, 0, ORDER_TIME_GTC, 0))
   {
      Print("Trailed ", g_direction > 0 ? "SELL STOP" : "BUY STOP",
            " from ", DoubleToString(g_pendingPrice, _Digits),
            " to ", DoubleToString(newPrice, _Digits));
      g_pendingPrice = newPrice;
   }
}

//+------------------------------------------------------------------+
//| Delete all pending orders belonging to this EA                   |
//+------------------------------------------------------------------+
void DeleteAllPending()
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
   g_pendingPrice  = 0;
}
//+------------------------------------------------------------------+
