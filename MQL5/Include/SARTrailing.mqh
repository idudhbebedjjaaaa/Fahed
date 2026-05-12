//+------------------------------------------------------------------+
//| SARTrailing.mqh - Trailing Stop Management                       |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property strict

#include "SARTypes.mqh"

//+------------------------------------------------------------------+
//| Trailing Stop Manager Class                                      |
//+------------------------------------------------------------------+
class CSARTrailing
{
private:
   string m_symbol;
   ENUM_TIMEFRAMES m_period;
   int    m_atrHandle;
   int    m_atrPeriod;
   
   // Trailing parameters
   double m_fixedTrailPoints;
   double m_atrMultiplier;
   double m_chandelierMultiplier;
   int    m_chandelierPeriod;
   double m_stepSize;
   double m_stepDistance;
   double m_volatilityMultiplier;
   
   // State tracking
   double m_highestSinceBuy;
   double m_lowestSinceSell;
   double m_currentTrailLevel;
   int    m_stepCount;
   
public:
   CSARTrailing(void);
   ~CSARTrailing(void);
   
   bool Init(string symbol, ENUM_TIMEFRAMES period, int atrPeriod,
             double fixedTrailPoints, double atrMultiplier,
             double chandelierMultiplier, int chandelierPeriod,
             double stepSize, double stepDistance,
             double volatilityMultiplier);
   void Deinit(void);
   
   void Reset(double entryPrice, int direction);
   double CalculateTrailLevel(ENUM_TRAILING_MODE mode, int direction, double currentPrice);
   
   bool ShouldClose(ENUM_TRAILING_MODE mode, int direction, double currentPrice);
   double GetTrailLevel(void) { return m_currentTrailLevel; }
   
private:
   double FixedTrail(int direction, double currentPrice);
   double ATRTrail(int direction, double currentPrice);
   double ChandelierTrail(int direction);
   double StepTrail(int direction, double currentPrice);
   double VolatilityTrail(int direction, double currentPrice);
   double HybridTrail(int direction, double currentPrice);
   double GetATR(void);
};

//+------------------------------------------------------------------+
CSARTrailing::CSARTrailing(void)
{
   m_atrHandle = INVALID_HANDLE;
   m_highestSinceBuy = 0;
   m_lowestSinceSell = DBL_MAX;
   m_currentTrailLevel = 0;
   m_stepCount = 0;
}

//+------------------------------------------------------------------+
CSARTrailing::~CSARTrailing(void)
{
   Deinit();
}

//+------------------------------------------------------------------+
bool CSARTrailing::Init(string symbol, ENUM_TIMEFRAMES period, int atrPeriod,
                        double fixedTrailPoints, double atrMultiplier,
                        double chandelierMultiplier, int chandelierPeriod,
                        double stepSize, double stepDistance,
                        double volatilityMultiplier)
{
   m_symbol = symbol;
   m_period = period;
   m_atrPeriod = atrPeriod;
   m_fixedTrailPoints = fixedTrailPoints;
   m_atrMultiplier = atrMultiplier;
   m_chandelierMultiplier = chandelierMultiplier;
   m_chandelierPeriod = chandelierPeriod;
   m_stepSize = stepSize;
   m_stepDistance = stepDistance;
   m_volatilityMultiplier = volatilityMultiplier;
   
   m_atrHandle = iATR(m_symbol, m_period, m_atrPeriod);
   if(m_atrHandle == INVALID_HANDLE)
   {
      Print("Failed to create ATR handle for trailing");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
void CSARTrailing::Deinit(void)
{
   if(m_atrHandle != INVALID_HANDLE)
      IndicatorRelease(m_atrHandle);
}

//+------------------------------------------------------------------+
void CSARTrailing::Reset(double entryPrice, int direction)
{
   if(direction > 0)
   {
      m_highestSinceBuy = entryPrice;
      m_lowestSinceSell = DBL_MAX;
   }
   else
   {
      m_lowestSinceSell = entryPrice;
      m_highestSinceBuy = 0;
   }
   m_currentTrailLevel = 0;
   m_stepCount = 0;
}

//+------------------------------------------------------------------+
double CSARTrailing::CalculateTrailLevel(ENUM_TRAILING_MODE mode, int direction, double currentPrice)
{
   // Update high/low tracking
   if(direction > 0)
   {
      if(currentPrice > m_highestSinceBuy)
         m_highestSinceBuy = currentPrice;
   }
   else
   {
      if(currentPrice < m_lowestSinceSell)
         m_lowestSinceSell = currentPrice;
   }
   
   double newLevel = 0;
   
   switch(mode)
   {
      case TRAIL_NONE:
         return 0;
      case TRAIL_FIXED:
         newLevel = FixedTrail(direction, currentPrice);
         break;
      case TRAIL_ATR:
         newLevel = ATRTrail(direction, currentPrice);
         break;
      case TRAIL_CHANDELIER:
         newLevel = ChandelierTrail(direction);
         break;
      case TRAIL_STEP:
         newLevel = StepTrail(direction, currentPrice);
         break;
      case TRAIL_VOLATILITY:
         newLevel = VolatilityTrail(direction, currentPrice);
         break;
      case TRAIL_HYBRID:
         newLevel = HybridTrail(direction, currentPrice);
         break;
   }
   
   // Only move trail in favorable direction
   if(direction > 0)
   {
      if(newLevel > m_currentTrailLevel || m_currentTrailLevel == 0)
         m_currentTrailLevel = newLevel;
   }
   else
   {
      if(newLevel < m_currentTrailLevel || m_currentTrailLevel == 0)
         m_currentTrailLevel = newLevel;
   }
   
   return m_currentTrailLevel;
}

//+------------------------------------------------------------------+
bool CSARTrailing::ShouldClose(ENUM_TRAILING_MODE mode, int direction, double currentPrice)
{
   if(mode == TRAIL_NONE) return false;
   
   double level = CalculateTrailLevel(mode, direction, currentPrice);
   if(level == 0) return false;
   
   if(direction > 0 && currentPrice <= level) return true;
   if(direction < 0 && currentPrice >= level) return true;
   
   return false;
}

//+------------------------------------------------------------------+
double CSARTrailing::FixedTrail(int direction, double currentPrice)
{
   double point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
   double dist = m_fixedTrailPoints * point;
   
   if(direction > 0)
      return m_highestSinceBuy - dist;
   else
      return m_lowestSinceSell + dist;
}

//+------------------------------------------------------------------+
double CSARTrailing::ATRTrail(int direction, double currentPrice)
{
   double atr = GetATR();
   if(atr == 0) return 0;
   
   double dist = atr * m_atrMultiplier;
   
   if(direction > 0)
      return m_highestSinceBuy - dist;
   else
      return m_lowestSinceSell + dist;
}

//+------------------------------------------------------------------+
double CSARTrailing::ChandelierTrail(int direction)
{
   double atr = GetATR();
   if(atr == 0) return 0;
   
   double high[], low[];
   int copied_h = CopyHigh(m_symbol, m_period, 0, m_chandelierPeriod, high);
   int copied_l = CopyLow(m_symbol, m_period, 0, m_chandelierPeriod, low);
   
   if(copied_h <= 0 || copied_l <= 0) return 0;
   
   if(direction > 0)
   {
      double highestHigh = high[ArrayMaximum(high)];
      return highestHigh - atr * m_chandelierMultiplier;
   }
   else
   {
      double lowestLow = low[ArrayMinimum(low)];
      return lowestLow + atr * m_chandelierMultiplier;
   }
}

//+------------------------------------------------------------------+
double CSARTrailing::StepTrail(int direction, double currentPrice)
{
   double point = SymbolInfoDouble(m_symbol, SYMBOL_POINT);
   double step = m_stepSize * point;
   double dist = m_stepDistance * point;
   
   if(direction > 0)
   {
      int newSteps = (int)((m_highestSinceBuy - currentPrice + dist) / step);
      if(newSteps < 0) newSteps = 0;
      double steppedHigh = m_highestSinceBuy - newSteps * step;
      return steppedHigh - dist;
   }
   else
   {
      int newSteps = (int)((currentPrice - m_lowestSinceSell + dist) / step);
      if(newSteps < 0) newSteps = 0;
      double steppedLow = m_lowestSinceSell + newSteps * step;
      return steppedLow + dist;
   }
}

//+------------------------------------------------------------------+
double CSARTrailing::VolatilityTrail(int direction, double currentPrice)
{
   double atr = GetATR();
   if(atr == 0) return 0;
   
   // Dynamic multiplier based on volatility regime
   double atrArr[50];
   if(CopyBuffer(m_atrHandle, 0, 0, 50, atrArr) <= 0) return 0;
   
   double avgATR = 0;
   for(int i = 0; i < 50; i++)
      avgATR += atrArr[i];
   avgATR /= 50.0;
   
   double volRatio = atr / avgATR;
   double dynamicMult = m_volatilityMultiplier * volRatio;
   
   // Clamp multiplier
   if(dynamicMult < 1.0) dynamicMult = 1.0;
   if(dynamicMult > 5.0) dynamicMult = 5.0;
   
   double dist = atr * dynamicMult;
   
   if(direction > 0)
      return m_highestSinceBuy - dist;
   else
      return m_lowestSinceSell + dist;
}

//+------------------------------------------------------------------+
double CSARTrailing::HybridTrail(int direction, double currentPrice)
{
   double atrLevel = ATRTrail(direction, currentPrice);
   double stepLevel = StepTrail(direction, currentPrice);
   
   // Use the tighter of the two
   if(direction > 0)
      return MathMax(atrLevel, stepLevel);
   else
      return MathMin(atrLevel, stepLevel);
}

//+------------------------------------------------------------------+
double CSARTrailing::GetATR(void)
{
   double atr[1];
   if(CopyBuffer(m_atrHandle, 0, 0, 1, atr) <= 0) return 0;
   return atr[0];
}
//+------------------------------------------------------------------+
