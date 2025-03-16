import pandas as pd
import pandas_ta as ta

def calculate_moving_averages(data: pd.DataFrame, short_period: int, long_period: int) -> pd.DataFrame:
    """
    Рассчитывает короткую и длинную скользящие средние.

    :param data: DataFrame с колонкой 'close'.
    :param short_period: Период короткой MA.
    :param long_period: Период длинной MA.
    :return: DataFrame с добавленными колонками 'short_ma' и 'long_ma'.
    """
    data['short_ma'] = data['close'].rolling(window=short_period, min_periods=1).mean()
    data['long_ma'] = data['close'].rolling(window=long_period, min_periods=1).mean()
    return data

def calculate_rsi(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Рассчитывает RSI.

    :param data: DataFrame с колонкой 'close'.
    :param period: Период для RSI.
    :return: DataFrame с добавленной колонкой 'rsi'.
    """
    data['rsi'] = ta.rsi(data['close'], length=period)
    return data

def calculate_atr(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Рассчитывает ATR.

    :param data: DataFrame с колонками 'high', 'low', 'close'.
    :param period: Период для ATR.
    :return: DataFrame с добавленной колонкой 'atr'.
    """
    data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=period)
    return data

def calculate_emas(data: pd.DataFrame, short_period: int, long_period: int) -> pd.DataFrame:
    """
    Рассчитывает короткую и длинную EMA.

    :param data: DataFrame с колонкой 'close'.
    :param short_period: Период короткой EMA.
    :param long_period: Период длинной EMA.
    :return: DataFrame с добавленными колонками 'ema_short' и 'ema_long'.
    """
    data['ema_short'] = data['close'].ewm(span=short_period, adjust=False, min_periods=1).mean()
    data['ema_long'] = data['close'].ewm(span=long_period, adjust=False, min_periods=1).mean()
    return data