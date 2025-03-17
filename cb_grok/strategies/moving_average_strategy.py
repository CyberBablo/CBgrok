import pandas as pd
import pandas_ta as ta
from cb_grok.indicators.indicators import calculate_moving_averages, calculate_rsi, calculate_atr, calculate_emas


def trend_filter(data: pd.DataFrame) -> pd.Series:
    """
    Определяет тренд на основе пересечения EMA.
    """
    return data['ema_short'] > data['ema_long']


def calculate_adx(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Рассчитывает ADX (Average Directional Index).

    :param data: DataFrame с колонками 'high', 'low', 'close'.
    :param period: Период для ADX.
    :return: DataFrame с добавленной колонкой 'adx'.
    """
    adx_df = ta.adx(data['high'], data['low'], data['close'], length=period)
    data['adx'] = adx_df[f'ADX_{period}']
    return data


def generate_signals(data: pd.DataFrame, buy_rsi_threshold: float, sell_rsi_threshold: float,
                     use_trend_filter: bool = True, use_rsi_filter: bool = True,
                     use_adx_filter: bool = False, adx_threshold: float = 25.0) -> pd.DataFrame:
    """
    Генерирует сигналы покупки и продажи на основе условий стратегии.

    :param data: DataFrame с индикаторами.
    :param buy_rsi_threshold: Порог RSI для покупки.
    :param sell_rsi_threshold: Порог RSI для продажи.
    :param use_trend_filter: Использовать фильтр тренда (EMA).
    :param use_rsi_filter: Использовать фильтр RSI.
    :param use_adx_filter: Использовать фильтр ADX.
    :param adx_threshold: Порог ADX для подтверждения тренда.
    :return: DataFrame с колонками 'signal' и 'positions'.
    """
    data['signal'] = 0
    trend = trend_filter(data) if use_trend_filter else pd.Series(True, index=data.index)

    if use_adx_filter:
        if use_rsi_filter:
            buy_condition = (data['short_ma'] > data['long_ma']) & (data['rsi'] < buy_rsi_threshold) & (
                        data['adx'] > adx_threshold) & trend
            sell_condition = (data['short_ma'] < data['long_ma']) & (data['rsi'] > sell_rsi_threshold) & (
                        data['adx'] > adx_threshold) & (~trend)
        else:
            buy_condition = (data['short_ma'] > data['long_ma']) & (data['adx'] > adx_threshold) & trend
            sell_condition = (data['short_ma'] < data['long_ma']) & (data['adx'] > adx_threshold) & (~trend)
    else:
        if use_rsi_filter:
            buy_condition = (data['short_ma'] > data['long_ma']) & (data['rsi'] < buy_rsi_threshold) & trend
            sell_condition = (data['short_ma'] < data['long_ma']) & (data['rsi'] > sell_rsi_threshold) & (~trend)
        else:
            buy_condition = (data['short_ma'] > data['long_ma']) & trend
            sell_condition = (data['short_ma'] < data['long_ma']) & (~trend)

    data.loc[buy_condition, 'signal'] = 1  # Покупка
    data.loc[sell_condition, 'signal'] = -1  # Продажа
    data['positions'] = data['signal'].diff()
    return data


def moving_average_strategy(data: pd.DataFrame, short_period: int, long_period: int, rsi_period: int,
                            atr_period: int = 14,
                            buy_rsi_threshold: float = 45, sell_rsi_threshold: float = 55, ema_short_period: int = 50,
                            ema_long_period: int = 200, use_trend_filter: bool = True, use_rsi_filter: bool = True,
                            adx_period: int = 14, use_adx_filter: bool = False, adx_threshold: float = 25.0,
                            debug: bool = False, logger=None) -> pd.DataFrame:
    """
    Применяет стратегию скользящих средних с дополнительным фильтром ADX.

    :param data: OHLCV DataFrame.
    :param short_period: Период короткой MA.
    :param long_period: Период длинной MA.
    :param rsi_period: Период RSI.
    :param atr_period: Период ATR.
    :param buy_rsi_threshold: Порог RSI для покупки.
    :param sell_rsi_threshold: Порог RSI для продажи.
    :param ema_short_period: Период короткой EMA для фильтра тренда.
    :param ema_long_period: Период длинной EMA для фильтра тренда.
    :param use_trend_filter: Использовать фильтр тренда (EMA).
    :param use_rsi_filter: Использовать фильтр RSI.
    :param adx_period: Период ADX.
    :param use_adx_filter: Использовать фильтр ADX.
    :param adx_threshold: Порог ADX для подтверждения тренда.
    :param debug: Логировать отладочную информацию.
    :param logger: Объект для логирования.
    :return: DataFrame с сигналами.
    """
    required_candles = max(long_period, ema_long_period, adx_period if use_adx_filter else 0)
    if len(data) < required_candles:
        if logger:
            logger.warning(f"Недостаточно данных: требуется {required_candles}, доступно {len(data)}")
        raise ValueError(f"Недостаточно данных: требуется минимум {required_candles} свечей")

    data = calculate_moving_averages(data, short_period, long_period)
    data = calculate_rsi(data, rsi_period)
    data = calculate_atr(data, atr_period)
    data = calculate_emas(data, ema_short_period, ema_long_period)
    if use_adx_filter:
        data = calculate_adx(data, adx_period)
    data = generate_signals(data, buy_rsi_threshold, sell_rsi_threshold, use_trend_filter, use_rsi_filter,
                            use_adx_filter, adx_threshold)

    if debug and logger:
        logger.info("Отладка стратегии:")
        for i in range(len(data)):
            row = data.iloc[i]
            adx_info = f", adx={row['adx']:.2f}" if use_adx_filter else ""
            logger.info(f"Timestamp: {row.name}, close={row['close']:.2f}, short_ma={row['short_ma']:.2f}, "
                        f"long_ma={row['long_ma']:.2f}, rsi={row['rsi']:.2f}, ema_short={row['ema_short']:.2f}, "
                        f"ema_long={row['ema_long']:.2f}{adx_info}, signal={row['signal']}")
        logger.info(f"Сигналы покупки: {(data['signal'] == 1).sum()}, Сигналы продажи: {(data['signal'] == -1).sum()}")

    return data