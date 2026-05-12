//+------------------------------------------------------------------+
//| SARRiskManager.mqh - Risk and Protection Management              |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property strict

#include "SARTypes.mqh"

//+------------------------------------------------------------------+
//| Risk Manager Class                                               |
//+------------------------------------------------------------------+
class CSARRiskManager
{
private:
   string m_symbol;
   
   // Protection parameters
   int    m_maxConsecutiveReversals;
   double m_maxDailyLossPercent;
   double m_maxSpreadPoints;
   int    m_cooldownBars;
   double m_volatilityShutdownMult;
   double m_equityProtectionPercent;
   double m_maxSlippagePoints;
   double m_riskPercent;
   
   // State tracking
   int    m_consecutiveReversals;
   double m_dailyLoss;
   double m_dailyStartEquity;
   datetime m_lastReversalTime;
   datetime m_lastTradeDay;
   double m_peakEquity;
   bool   m_isShutdown;
   string m_shutdownReason;
   
   // ATR reference for volatility check
   int    m_atrHandle;
   int    m_atrPeriod;
   ENUM_TIMEFRAMES m_period;
   
public:
   CSARRiskManager(void);
   ~CSARRiskManager(void);
   
   bool Init(string symbol, ENUM_TIMEFRAMES period, int atrPeriod,
             int maxConsecReversals, double maxDailyLossPercent,
             double maxSpreadPoints, int cooldownBars,
             double volatilityShutdownMult, double equityProtectionPercent,
             double maxSlippagePoints, double riskPercent);
   void Deinit(void);
   
   // Protection checks
   bool CanTrade(void);
   bool CheckSpread(void);
   bool CheckCooldown(void);
   bool CheckConsecutiveReversals(void);
   bool CheckDailyLoss(void);
   bool CheckVolatility(void);
   bool CheckEquityProtection(void);
   
   // State updates
   void OnReversal(void);
   void OnTradeClose(double profit);
   void OnNewDay(void);
   void OnTick(void);
   
   // Position sizing
   double CalculateLotSize(double stopDistancePoints);
   
   // Getters
   bool   IsShutdown(void) { return m_isShutdown; }
   string GetShutdownReason(void) { return m_shutdownReason; }
   int    GetConsecutiveReversals(void) { return m_consecutiveReversals; }
   double GetDailyLoss(void) { return m_dailyLoss; }
   
   void   ResetDailyCounters(void);
   void   ResetShutdown(void) { m_isShutdown = false; m_shutdownReason = ""; }
};

//+------------------------------------------------------------------+
CSARRiskManager::CSARRiskManager(void)
{
   m_consecutiveReversals = 0;
   m_dailyLoss = 0;
   m_dailyStartEquity = 0;
   m_lastReversalTime = 0;
   m_lastTradeDay = 0;
   m_peakEquity = 0;
   m_isShutdown = false;
   m_atrHandle = INVALID_HANDLE;
}

//+------------------------------------------------------------------+
CSARRiskManager::~CSARRiskManager(void)
{
   Deinit();
}

//+------------------------------------------------------------------+
bool CSARRiskManager::Init(string symbol, ENUM_TIMEFRAMES period, int atrPeriod,
                           int maxConsecReversals, double maxDailyLossPercent,
                           double maxSpreadPoints, int cooldownBars,
                           double volatilityShutdownMult, double equityProtectionPercent,
                           double maxSlippagePoints, double riskPercent)
{
   m_symbol = symbol;
   m_period = period;
   m_atrPeriod = atrPeriod;
   m_maxConsecutiveReversals = maxConsecReversals;
   m_maxDailyLossPercent = maxDailyLossPercent;
   m_maxSpreadPoints = maxSpreadPoints;
   m_cooldownBars = cooldownBars;
   m_volatilityShutdownMult = volatilityShutdownMult;
   m_equityProtectionPercent = equityProtectionPercent;
   m_maxSlippagePoints = maxSlippagePoints;
   m_riskPercent = riskPercent;
   
   m_dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   m_peakEquity = m_dailyStartEquity;
   
   m_atrHandle = iATR(m_symbol, m_period, m_atrPeriod);
   if(m_atrHandle == INVALID_HANDLE)
   {
      Print("RiskManager: Failed to create ATR handle");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
void CSARRiskManager::Deinit(void)
{
   if(m_atrHandle != INVALID_HANDLE)
      IndicatorRelease(m_atrHandle);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CanTrade(void)
{
   if(m_isShutdown) return false;
   
   if(!CheckSpread())
   {
      m_shutdownReason = "Spread too high";
      return false;
   }
   
   if(!CheckCooldown())
      return false;
   
   if(!CheckConsecutiveReversals())
   {
      m_isShutdown = true;
      m_shutdownReason = "Max consecutive reversals reached";
      return false;
   }
   
   if(!CheckDailyLoss())
   {
      m_isShutdown = true;
      m_shutdownReason = "Daily loss limit reached";
      return false;
   }
   
   if(!CheckVolatility())
   {
      m_shutdownReason = "Volatility too high - shutdown";
      return false;
   }
   
   if(!CheckEquityProtection())
   {
      m_isShutdown = true;
      m_shutdownReason = "Equity protection triggered";
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckSpread(void)
{
   if(m_maxSpreadPoints <= 0) return true;
   
   double spread = (double)SymbolInfoInteger(m_symbol, SYMBOL_SPREAD);
   return (spread <= m_maxSpreadPoints);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckCooldown(void)
{
   if(m_cooldownBars <= 0) return true;
   if(m_lastReversalTime == 0) return true;
   
   datetime currentBarTime = iTime(m_symbol, m_period, 0);
   datetime cooldownEnd = m_lastReversalTime + m_cooldownBars * PeriodSeconds(m_period);
   
   return (currentBarTime >= cooldownEnd);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckConsecutiveReversals(void)
{
   if(m_maxConsecutiveReversals <= 0) return true;
   return (m_consecutiveReversals < m_maxConsecutiveReversals);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckDailyLoss(void)
{
   if(m_maxDailyLossPercent <= 0) return true;
   
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double lossPercent = (m_dailyStartEquity - equity) / m_dailyStartEquity * 100.0;
   
   return (lossPercent < m_maxDailyLossPercent);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckVolatility(void)
{
   if(m_volatilityShutdownMult <= 0) return true;
   
   double atr[50];
   if(CopyBuffer(m_atrHandle, 0, 0, 50, atr) <= 0) return true;
   
   double avgATR = 0;
   for(int i = 0; i < 49; i++)
      avgATR += atr[i];
   avgATR /= 49.0;
   
   return (atr[49] <= avgATR * m_volatilityShutdownMult);
}

//+------------------------------------------------------------------+
bool CSARRiskManager::CheckEquityProtection(void)
{
   if(m_equityProtectionPercent <= 0) return true;
   
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > m_peakEquity)
      m_peakEquity = equity;
   
   double drawdown = (m_peakEquity - equity) / m_peakEquity * 100.0;
   return (drawdown < m_equityProtectionPercent);
}

//+------------------------------------------------------------------+
void CSARRiskManager::OnReversal(void)
{
   m_consecutiveReversals++;
   m_lastReversalTime = TimeCurrent();
}

//+------------------------------------------------------------------+
void CSARRiskManager::OnTradeClose(double profit)
{
   if(profit > 0)
      m_consecutiveReversals = 0;
   
   m_dailyLoss += (profit < 0) ? MathAbs(profit) : 0;
}

//+------------------------------------------------------------------+
void CSARRiskManager::OnNewDay(void)
{
   ResetDailyCounters();
}

//+------------------------------------------------------------------+
void CSARRiskManager::OnTick(void)
{
   MqlDateTime dt;
   TimeCurrent(dt);
   
   datetime today = StringToTime(IntegerToString(dt.year) + "." + 
                                  IntegerToString(dt.mon) + "." + 
                                  IntegerToString(dt.day));
   
   if(m_lastTradeDay != today)
   {
      m_lastTradeDay = today;
      OnNewDay();
   }
   
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > m_peakEquity)
      m_peakEquity = equity;
}

//+------------------------------------------------------------------+
double CSARRiskManager::CalculateLotSize(double stopDistancePoints)
{
   if(m_riskPercent <= 0 || stopDistancePoints <= 0)
      return SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
   
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskAmount = equity * m_riskPercent / 100.0;
   
   double tickValue = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(m_symbol, SYMBOL_TRADE_TICK_SIZE);
   double point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
   
   if(tickValue == 0 || tickSize == 0) 
      return SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
   
   double pointValue = tickValue * point / tickSize;
   double lots = riskAmount / (stopDistancePoints * pointValue);
   
   double minLot = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP);
   
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(lots, minLot);
   lots = MathMin(lots, maxLot);
   
   return lots;
}

//+------------------------------------------------------------------+
void CSARRiskManager::ResetDailyCounters(void)
{
   m_dailyLoss = 0;
   m_dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   m_consecutiveReversals = 0;
   
   if(!m_isShutdown || m_shutdownReason == "Daily loss limit reached")
      ResetShutdown();
}
//+------------------------------------------------------------------+
