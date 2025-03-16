import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime
import os

# Настройка логирования
log_folder = "log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{log_folder}/strategy_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def calculate_indicators(data: pd.DataFrame, short_period: int, long_period: int, rsi_period: int, atr_period: int,
                         ema_short_period: int = 50, ema_long_period: int = 200) -> pd.DataFrame:
    """Рассчитывает технические индикаторы для данных."""
    data['short_ma'] = data['close'].rolling(window=short_period, min_periods=1).mean()
    data['long_ma'] = data['close'].rolling(window=long_period, min_periods=1).mean()
    data['rsi'] = ta.rsi(data['close'], length=rsi_period)
    data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=atr_period)
    data['ema_short'] = data['close'].ewm(span=ema_short_period, adjust=False, min_periods=1).mean()
    data['ema_long'] = data['close'].ewm(span=ema_long_period, adjust=False, min_periods=1).mean()
    return data

def trend_filter(data: pd.DataFrame) -> pd.Series:
    """Возвращает фильтр тренда: True для бычьего тренда (EMA50 > EMA200), False для медвежьего."""
    return data['ema_short'] > data['ema_long']

def generate_signals(data: pd.DataFrame, buy_rsi_threshold: float, sell_rsi_threshold: float, use_trend_filter: bool = True) -> pd.DataFrame:
    """Генерирует сигналы на основе условий."""
    data['signal'] = 0
    trend = trend_filter(data) if use_trend_filter else pd.Series(True, index=data.index)

    buy_condition = (data['short_ma'] > data['long_ma']) & (data['rsi'] < buy_rsi_threshold) & trend
    sell_condition = (data['short_ma'] < data['long_ma']) & (data['rsi'] > sell_rsi_threshold) & (~trend)

    data.loc[buy_condition, 'signal'] = 1  # Покупка
    data.loc[sell_condition, 'signal'] = -1  # Продажа
    data['positions'] = data['signal'].diff()
    return data

def moving_average_strategy(data: pd.DataFrame, short_period: int, long_period: int, rsi_period: int, atr_period: int = 14,
                            buy_rsi_threshold: float = 45, sell_rsi_threshold: float = 55, ema_short_period: int = 50,
                            ema_long_period: int = 200, use_trend_filter: bool = True, debug: bool = False) -> pd.DataFrame:
    """Основная функция стратегии с возможностью включения/выключения фильтра тренда."""
    # Рассчитываем индикаторы
    data = calculate_indicators(data, short_period, long_period, rsi_period, atr_period, ema_short_period, ema_long_period)
    # Генерируем сигналы
    data = generate_signals(data, buy_rsi_threshold, sell_rsi_threshold, use_trend_filter)

    if debug:
        logging.info("Debugging strategy:")
        for i in range(len(data)):
            close = data['close'].iloc[i]
            short_ma = data['short_ma'].iloc[i]
            long_ma = data['long_ma'].iloc[i]
            rsi = data['rsi'].iloc[i]
            ema_short = data['ema_short'].iloc[i]
            ema_long = data['ema_long'].iloc[i]
            signal = data['signal'].iloc[i]
            logging.info(f"Timestamp: {data.index[i]}, close={close:.2f}, short_ma={short_ma:.2f}, long_ma={long_ma:.2f}, "
                         f"rsi={rsi:.2f}, ema_short={ema_short:.2f}, ema_long={ema_long:.2f}, signal={signal}")
        logging.info(f"Buy conditions met: {(data['signal'] == 1).sum()}, Sell conditions met: {(data['signal'] == -1).sum()}")

    return data