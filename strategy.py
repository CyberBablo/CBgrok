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


def moving_average_strategy(data: pd.DataFrame, short_period: int, long_period: int, rsi_period: int,
                            atr_period: int = 14, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9,
                            debug: bool = False) -> pd.DataFrame:
    data['short_ma'] = data['close'].rolling(window=short_period, min_periods=1).mean()
    data['long_ma'] = data['close'].rolling(window=long_period, min_periods=1).mean()
    data['rsi'] = ta.rsi(data['close'], length=rsi_period)
    data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=atr_period)
    macd = ta.macd(data['close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    data['macd'] = macd['MACD_' + str(macd_fast) + '_' + str(macd_slow) + '_' + str(macd_signal)]
    data['macd_signal'] = macd['MACDs_' + str(macd_fast) + '_' + str(macd_slow) + '_' + str(macd_signal)]

    data['signal'] = 0
    # Условия для покупки: short_ma > long_ma, RSI < 45 (смягчено)
    buy_condition = (data['short_ma'] > data['long_ma']) & (data['rsi'] < 45)
    # Условия для продажи: short_ma < long_ma, RSI > 55 (смягчено), MACD < MACD_signal
    sell_condition = (data['short_ma'] < data['long_ma']) & (data['rsi'] > 55) & (data['macd'] < data['macd_signal'])

    data.loc[buy_condition, 'signal'] = 1
    data.loc[sell_condition, 'signal'] = -1
    data['positions'] = data['signal'].diff()

    if debug:
        logging.info("Debugging strategy:")
        logging.info(
            data[['close', 'short_ma', 'long_ma', 'rsi', 'macd', 'macd_signal', 'signal']].tail(20).to_string())
        logging.info(f"Buy conditions met: {buy_condition.sum()}, Sell conditions met: {sell_condition.sum()}")

    return data