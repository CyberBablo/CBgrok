import pandas as pd
import numpy as np

def run_backtest(data: pd.DataFrame, initial_capital: float, commission: float, stop_loss_multiplier: float = 1.5,
                 take_profit_multiplier: float = 3.0, slippage_percent: float = 0.001, spread: float = 0.0002):
    """
    Выполняет бэктест с учетом проскальзывания и спреда.

    :param data: DataFrame с колонками 'signal', 'open', 'close', 'atr'.
    :param initial_capital: Начальный капитал.
    :param commission: Комиссия за сделку.
    :param stop_loss_multiplier: Множитель ATR для стоп-лосса.
    :param take_profit_multiplier: Множитель ATR для тейк-профита.
    :param slippage_percent: Процент проскальзывания.
    :param spread: Спред (в процентах).
    :return: Кортеж (backtest_data, orders, metrics, num_orders).
    """
    required_columns = ['signal', 'open', 'close', 'atr']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")

    capital = initial_capital
    assets = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    orders = []

    for i in range(len(data) - 1):
        signal = data['signal'].iloc[i]
        next_open_price = data['open'].iloc[i + 1] * (1 + slippage_percent + spread if signal == 1 else 1 - slippage_percent - spread)
        timestamp = data.index[i + 1].isoformat()
        atr = data['atr'].iloc[i]

        if assets > 0:
            current_price = data['close'].iloc[i]
            if current_price <= stop_loss:
                sell_price = next_open_price * (1 - slippage_percent - spread)
                capital = assets * sell_price * (1 - commission)
                orders.append({"action": "sell", "amount": assets, "price": sell_price, "timestamp": timestamp, "reason": "stop_loss"})
                assets = 0
            elif current_price >= take_profit:
                sell_price = next_open_price * (1 - slippage_percent - spread)
                capital = assets * sell_price * (1 - commission)
                orders.append({"action": "sell", "amount": assets, "price": sell_price, "timestamp": timestamp, "reason": "take_profit"})
                assets = 0

        if signal == 1 and capital > 0:
            buy_price = next_open_price * (1 + slippage_percent + spread)
            assets = capital / buy_price * (1 - commission)
            capital = 0
            entry_price = buy_price
            stop_loss = entry_price - atr * stop_loss_multiplier
            take_profit = entry_price + atr * take_profit_multiplier
            orders.append({"action": "buy", "amount": assets, "price": buy_price, "timestamp": timestamp})
        elif signal == -1 and assets > 0:
            sell_price = next_open_price * (1 - slippage_percent - spread)
            capital = assets * sell_price * (1 - commission)
            orders.append({"action": "sell", "amount": assets, "price": sell_price, "timestamp": timestamp, "reason": "signal"})
            assets = 0

        data.loc[data.index[i + 1], 'portfolio_value'] = capital + assets * data['close'].iloc[i + 1]

    if assets > 0:
        last_price = data['close'].iloc[-1] * (1 - slippage_percent - spread)
        capital = assets * last_price * (1 - commission)
        orders.append({"action": "sell", "amount": assets, "price": last_price, "timestamp": data.index[-1].isoformat(), "reason": "end_of_backtest"})
        assets = 0

    final_value = capital
    equity_series = data['portfolio_value'].dropna()
    if len(equity_series) > 1:
        returns = equity_series.pct_change().dropna()
        total_return = (final_value - initial_capital) / initial_capital * 100
        max_drawdown = ((equity_series.cummax() - equity_series) / equity_series.cummax()).max() * 100
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
    else:
        total_return = 0
        max_drawdown = 0
        sharpe_ratio = 0

    metrics = {
        "final_value": final_value,
        "total_return_percent": total_return,
        "max_drawdown_percent": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }
    num_orders = len(orders)
    return data, orders, metrics, num_orders