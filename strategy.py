import pandas as pd
import numpy as np
import pandas_ta as ta


def moving_average_strategy(data: pd.DataFrame, short_period: int, long_period: int, rsi_period: int) -> pd.DataFrame:
    # Рассчитываем скользящие средние
    data['short_ma'] = data['close'].rolling(window=short_period, min_periods=1).mean()
    data['long_ma'] = data['close'].rolling(window=long_period, min_periods=1).mean()

    # Рассчитываем RSI
    data['rsi'] = ta.rsi(data['close'], length=rsi_period)

    # Инициализируем столбец для сигналов
    data['signal'] = 0

    # Условия для покупки: short_ma > long_ma и RSI < 30 (перепроданность)
    buy_condition = (data['short_ma'] > data['long_ma']) & (data['rsi'] < 30)
    # Условия для продажи: short_ma < long_ma и RSI > 70 (перекупленность)
    sell_condition = (data['short_ma'] < data['long_ma']) & (data['rsi'] > 70)

    # Применяем сигналы
    data.loc[buy_condition, 'signal'] = 1
    data.loc[sell_condition, 'signal'] = -1

    # Рассчитываем позиции
    data['positions'] = data['signal'].diff()

    return data