//+------------------------------------------------------------------+
//| SARFilters.mqh - Filter logic for SAR Expert Advisor             |
//| Copyright 2024, Quant SAR Project                                |
//+------------------------------------------------------------------+
#property copyright "Quant SAR Project"
#property strict

#include "SARTypes.mqh"

//+------------------------------------------------------------------+
//| Filter Manager Class                                             |
//+------------------------------------------------------------------+
class CSARFilters
{
private:
   // Indicator handles
   int m_adxHandle;
   int m_emaFastHandle;
   int m_emaSlowHandle;
   int m_atrHandle;
   int m_atrHTFHandle;
   int m_emaHTFHandle;
   int m_volumeHandle;
   
   string m_symbol;
   ENUM_TIMEFRAMES m_period;
   ENUM_TIMEFRAMES m_htfPeriod;
   
   // Filter parameters
   int    m_adxPeriod;
   double m_adxThreshold;
   int    m_emaFastPeriod;
   int    m_emaSlowPeriod;
   int    m_atrPeriod;
   double m_atrExpansionMult;
   int    m_emaHTFPeriod;
   double m_volumeThreshold;
   
   // Cached values
   double m_lastADX;
   double m_lastATR;
   double m_lastATRHTF;
   double m_avgATR;
   
public:
   CSARFilters(void);
   ~CSARFilters(void);
   
   bool Init(string symbol, ENUM_TIMEFRAMES period, ENUM_TIMEFRAMES htfPeriod,
             int adxPeriod, double adxThreshold,
             int emaFastPeriod, int emaSlowPeriod,
             int atrPeriod, double atrExpansionMult,
             int emaHTFPeriod, double volumeThreshold);
   void Deinit(void);
   
   // Individual filters
   bool ADXFilter(int direction);
   bool EMAFilter(int direction);
   bool MarketStructureFilter(int direction);
   bool ATRExpansionFilter(void);
   bool VolumeFilter(void);
   bool SessionFilter(ENUM_SESSION_FILTER sessionMode);
   bool HTFTrendFilter(int direction);
   
   // Composite filter
   bool CompositeFilter(ENUM_TREND_FILTER filterMode, int direction, ENUM_SESSION_FILTER sessionMode);
   
   // Getters
   double GetATR(void);
   double GetATRHTF(void);
   double GetADX(void);
   double GetSpread(void);
   int    GetHTFTrendDirection(void);
};

//+------------------------------------------------------------------+
CSARFilters::CSARFilters(void)
{
   m_adxHandle = INVALID_HANDLE;
   m_emaFastHandle = INVALID_HANDLE;
   m_emaSlowHandle = INVALID_HANDLE;
   m_atrHandle = INVALID_HANDLE;
   m_atrHTFHandle = INVALID_HANDLE;
   m_emaHTFHandle = INVALID_HANDLE;
   m_volumeHandle = INVALID_HANDLE;
}

//+------------------------------------------------------------------+
CSARFilters::~CSARFilters(void)
{
   Deinit();
}

//+------------------------------------------------------------------+
bool CSARFilters::Init(string symbol, ENUM_TIMEFRAMES period, ENUM_TIMEFRAMES htfPeriod,
                       int adxPeriod, double adxThreshold,
                       int emaFastPeriod, int emaSlowPeriod,
                       int atrPeriod, double atrExpansionMult,
                       int emaHTFPeriod, double volumeThreshold)
{
   m_symbol = symbol;
   m_period = period;
   m_htfPeriod = htfPeriod;
   m_adxPeriod = adxPeriod;
   m_adxThreshold = adxThreshold;
   m_emaFastPeriod = emaFastPeriod;
   m_emaSlowPeriod = emaSlowPeriod;
   m_atrPeriod = atrPeriod;
   m_atrExpansionMult = atrExpansionMult;
   m_emaHTFPeriod = emaHTFPeriod;
   m_volumeThreshold = volumeThreshold;
   
   m_adxHandle = iADX(m_symbol, m_period, m_adxPeriod);
   m_emaFastHandle = iMA(m_symbol, m_period, m_emaFastPeriod, 0, MODE_EMA, PRICE_CLOSE);
   m_emaSlowHandle = iMA(m_symbol, m_period, m_emaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE);
   m_atrHandle = iATR(m_symbol, m_period, m_atrPeriod);
   m_atrHTFHandle = iATR(m_symbol, m_htfPeriod, m_atrPeriod);
   m_emaHTFHandle = iMA(m_symbol, m_htfPeriod, m_emaHTFPeriod, 0, MODE_EMA, PRICE_CLOSE);
   m_volumeHandle = iVolumes(m_symbol, m_period, VOLUME_TICK);
   
   if(m_adxHandle == INVALID_HANDLE || m_emaFastHandle == INVALID_HANDLE ||
      m_emaSlowHandle == INVALID_HANDLE || m_atrHandle == INVALID_HANDLE ||
      m_atrHTFHandle == INVALID_HANDLE || m_emaHTFHandle == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
void CSARFilters::Deinit(void)
{
   if(m_adxHandle != INVALID_HANDLE) IndicatorRelease(m_adxHandle);
   if(m_emaFastHandle != INVALID_HANDLE) IndicatorRelease(m_emaFastHandle);
   if(m_emaSlowHandle != INVALID_HANDLE) IndicatorRelease(m_emaSlowHandle);
   if(m_atrHandle != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
   if(m_atrHTFHandle != INVALID_HANDLE) IndicatorRelease(m_atrHTFHandle);
   if(m_emaHTFHandle != INVALID_HANDLE) IndicatorRelease(m_emaHTFHandle);
   if(m_volumeHandle != INVALID_HANDLE) IndicatorRelease(m_volumeHandle);
}

//+------------------------------------------------------------------+
bool CSARFilters::ADXFilter(int direction)
{
   double adx[1], plusDI[1], minusDI[1];
   if(CopyBuffer(m_adxHandle, 0, 0, 1, adx) <= 0) return true;
   if(CopyBuffer(m_adxHandle, 1, 0, 1, plusDI) <= 0) return true;
   if(CopyBuffer(m_adxHandle, 2, 0, 1, minusDI) <= 0) return true;
   
   m_lastADX = adx[0];
   
   if(adx[0] < m_adxThreshold)
      return false;
   
   if(direction > 0 && plusDI[0] <= minusDI[0])
      return false;
   if(direction < 0 && minusDI[0] <= plusDI[0])
      return false;
   
   return true;
}

//+------------------------------------------------------------------+
bool CSARFilters::EMAFilter(int direction)
{
   double emaFast[1], emaSlow[1];
   if(CopyBuffer(m_emaFastHandle, 0, 0, 1, emaFast) <= 0) return true;
   if(CopyBuffer(m_emaSlowHandle, 0, 0, 1, emaSlow) <= 0) return true;
   
   if(direction > 0 && emaFast[0] <= emaSlow[0])
      return false;
   if(direction < 0 && emaFast[0] >= emaSlow[0])
      return false;
   
   return true;
}

//+------------------------------------------------------------------+
bool CSARFilters::MarketStructureFilter(int direction)
{
   double high[20], low[20], close[3];
   if(CopyHigh(m_symbol, m_period, 0, 20, high) <= 0) return true;
   if(CopyLow(m_symbol, m_period, 0, 20, low) <= 0) return true;
   if(CopyClose(m_symbol, m_period, 0, 3, close) <= 0) return true;
   
   // Higher highs and higher lows for uptrend
   double recentHigh = high[ArrayMaximum(high, 0, 10)];
   double prevHigh = high[ArrayMaximum(high, 10, 10)];
   double recentLow = low[ArrayMinimum(low, 0, 10)];
   double prevLow = low[ArrayMinimum(low, 10, 10)];
   
   bool uptrend = (recentHigh > prevHigh && recentLow > prevLow);
   bool downtrend = (recentHigh < prevHigh && recentLow < prevLow);
   
   if(direction > 0 && !uptrend) return false;
   if(direction < 0 && !downtrend) return false;
   
   return true;
}

//+------------------------------------------------------------------+
bool CSARFilters::ATRExpansionFilter(void)
{
   double atr[20];
   if(CopyBuffer(m_atrHandle, 0, 0, 20, atr) <= 0) return true;
   
   m_lastATR = atr[19];
   
   double avgATR = 0;
   for(int i = 0; i < 20; i++)
      avgATR += atr[i];
   avgATR /= 20.0;
   m_avgATR = avgATR;
   
   return (m_lastATR > avgATR * m_atrExpansionMult);
}

//+------------------------------------------------------------------+
bool CSARFilters::VolumeFilter(void)
{
   if(m_volumeHandle == INVALID_HANDLE) return true;
   
   double vol[20];
   if(CopyBuffer(m_volumeHandle, 0, 0, 20, vol) <= 0) return true;
   
   double avgVol = 0;
   for(int i = 0; i < 20; i++)
      avgVol += vol[i];
   avgVol /= 20.0;
   
   return (vol[19] > avgVol * m_volumeThreshold);
}

//+------------------------------------------------------------------+
bool CSARFilters::SessionFilter(ENUM_SESSION_FILTER sessionMode)
{
   if(sessionMode == SESSION_ALL) return true;
   
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;
   
   switch(sessionMode)
   {
      case SESSION_LONDON:
         return (hour >= 8 && hour < 17);
      case SESSION_NEWYORK:
         return (hour >= 13 && hour < 22);
      case SESSION_ASIAN:
         return (hour >= 0 && hour < 9);
      case SESSION_LONDON_NY:
         return (hour >= 13 && hour < 17);
      default:
         return true;
   }
}

//+------------------------------------------------------------------+
bool CSARFilters::HTFTrendFilter(int direction)
{
   double emaHTF[1];
   double close[1];
   
   if(CopyBuffer(m_emaHTFHandle, 0, 0, 1, emaHTF) <= 0) return true;
   if(CopyClose(m_symbol, m_htfPeriod, 0, 1, close) <= 0) return true;
   
   if(direction > 0 && close[0] <= emaHTF[0]) return false;
   if(direction < 0 && close[0] >= emaHTF[0]) return false;
   
   return true;
}

//+------------------------------------------------------------------+
bool CSARFilters::CompositeFilter(ENUM_TREND_FILTER filterMode, int direction, ENUM_SESSION_FILTER sessionMode)
{
   if(!SessionFilter(sessionMode))
      return false;
   
   switch(filterMode)
   {
      case FILTER_NONE:
         return true;
      case FILTER_ADX:
         return ADXFilter(direction);
      case FILTER_EMA_CROSS:
         return EMAFilter(direction);
      case FILTER_MARKET_STRUCT:
         return MarketStructureFilter(direction);
      case FILTER_ATR_EXPANSION:
         return ATRExpansionFilter();
      case FILTER_COMPOSITE:
         return (ADXFilter(direction) && EMAFilter(direction) && ATRExpansionFilter());
      default:
         return true;
   }
}

//+------------------------------------------------------------------+
double CSARFilters::GetATR(void)
{
   double atr[1];
   if(CopyBuffer(m_atrHandle, 0, 0, 1, atr) <= 0) return 0;
   return atr[0];
}

//+------------------------------------------------------------------+
double CSARFilters::GetATRHTF(void)
{
   double atr[1];
   if(CopyBuffer(m_atrHTFHandle, 0, 0, 1, atr) <= 0) return 0;
   return atr[0];
}

//+------------------------------------------------------------------+
double CSARFilters::GetADX(void)
{
   return m_lastADX;
}

//+------------------------------------------------------------------+
double CSARFilters::GetSpread(void)
{
   return (double)SymbolInfoInteger(m_symbol, SYMBOL_SPREAD) * SymbolInfoDouble(m_symbol, SYMBOL_POINT);
}

//+------------------------------------------------------------------+
int CSARFilters::GetHTFTrendDirection(void)
{
   double emaHTF[1], close[1];
   if(CopyBuffer(m_emaHTFHandle, 0, 0, 1, emaHTF) <= 0) return 0;
   if(CopyClose(m_symbol, m_htfPeriod, 0, 1, close) <= 0) return 0;
   
   if(close[0] > emaHTF[0]) return 1;
   if(close[0] < emaHTF[0]) return -1;
   return 0;
}
//+------------------------------------------------------------------+
