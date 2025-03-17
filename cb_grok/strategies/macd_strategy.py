import pandas as pd
import pandas_ta as ta


def calculate_macd(data: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.DataFrame:
    macd = ta.macd(data['close'], fast=fast, slow=slow, signal=signal)
    data['macd'] = macd[f'MACD_{fast}_{slow}_{signal}']
    data['macd_signal'] = macd[f'MACDs_{fast}_{slow}_{signal}']
    data['macd_hist'] = macd[f'MACDh_{fast}_{slow}_{signal}']
    return data


def calculate_bollinger_bands(data: pd.DataFrame, period: int, std_dev: float) -> pd.DataFrame:
    bb = ta.bbands(data['close'], length=period, std=std_dev)
    data['bb_upper'] = bb[f'BBU_{period}_{std_dev}']
    data['bb_lower'] = bb[f'BBL_{period}_{std_dev}']
    data['bb_mid'] = bb[f'BBM_{period}_{std_dev}']
    return data


def calculate_atr(data: pd.DataFrame, period: int) -> pd.DataFrame:
    data['atr'] = ta.atr(data['high'], data['low'], data['close'], length=period)
    return data


def macd_strategy(data: pd.DataFrame, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9,
                  bb_period: int = 20, bb_std: float = 2.0, atr_period: int = 14, logger=None) -> pd.DataFrame:
    """
    Стратегия на основе MACD и Bollinger Bands.

    :param data: OHLCV DataFrame.
    :param macd_fast: Быстрый период MACD.
    :param macd_slow: Медленный период MACD.
    :param macd_signal: Период сигнальной линии MACD.
    :param bb_period: Период Bollinger Bands.
    :param bb_std: Стандартное отклонение для BB.
    :param atr_period: Период ATR.
    :param logger: Объект для логирования.
    :return: DataFrame с сигналами.
    """
    required_candles = max(macd_slow, bb_period, atr_period)
    if len(data) < required_candles:
        if logger:
            logger.warning(f"Недостаточно данных: требуется {required_candles}, доступно {len(data)}")
        raise ValueError(f"Недостаточно данных: требуется минимум {required_candles} свечей")

    data = calculate_macd(data, macd_fast, macd_slow, macd_signal)
    data = calculate_bollinger_bands(data, bb_period, bb_std)
    data = calculate_atr(data, atr_period)

    data['signal'] = 0
    buy_condition = (data['macd'] > data['macd_signal']) & (data['close'] < data['bb_lower'])
    sell_condition = (data['macd'] < data['macd_signal']) & (data['close'] > data['bb_upper'])

    data.loc[buy_condition, 'signal'] = 1
    data.loc[sell_condition, 'signal'] = -1
    data['positions'] = data['signal'].diff()

    if logger:
        logger.info(f"Сигналы покупки: {(data['signal'] == 1).sum()}, Сигналы продажи: {(data['signal'] == -1).sum()}")

    return data