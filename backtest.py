import pandas as pd
import numpy as np
from strategy import moving_average_strategy
from json_logger import save_model_results
import optuna
import os


def run_backtest(data: pd.DataFrame, initial_capital: float, commission: float, stop_loss_pct: float = 0.02,
                 take_profit_pct: float = 0.05):
    capital = initial_capital
    assets = 0
    entry_price = 0  # Цена входа для расчета стоп-лосса и тейк-профита
    orders = []

    for i in range(len(data) - 1):  # Исключаем последнюю свечу
        signal = data['signal'].iloc[i]
        next_open_price = data['open'].iloc[i + 1]  # Цена открытия следующей свечи
        timestamp = data.index[i + 1].isoformat()

        # Проверка стоп-лосса и тейк-профита для открытой позиции
        if assets > 0:
            current_price = data['close'].iloc[i]  # Текущая цена для проверки условий
            if current_price <= entry_price * (1 - stop_loss_pct):  # Стоп-лосс
                capital = assets * next_open_price * (1 - commission)  # Исполнение на следующей свече
                orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                               "reason": "stop_loss"})
                assets = 0
            elif current_price >= entry_price * (1 + take_profit_pct):  # Тейк-профит
                capital = assets * next_open_price * (1 - commission)  # Исполнение на следующей свече
                orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                               "reason": "take_profit"})
                assets = 0

        # Обработка сигналов стратегии
        if signal == 1 and capital > 0:  # Покупка
            assets = capital / next_open_price * (1 - commission)  # Исполнение на следующей свече
            capital = 0
            entry_price = next_open_price  # Запоминаем цену входа
            orders.append({"action": "buy", "amount": assets, "price": next_open_price, "timestamp": timestamp})
        elif signal == -1 and assets > 0:  # Продажа
            capital = assets * next_open_price * (1 - commission)  # Исполнение на следующей свече
            orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                           "reason": "signal"})
            assets = 0

        # Обновление портфеля
        data.loc[data.index[i + 1], 'portfolio_value'] = capital + assets * data['close'].iloc[i + 1]

    # Расчет метрик
    final_value = capital + assets * data['close'].iloc[-1] if assets > 0 else capital
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
    return data, orders, metrics


def objective(trial, data_fetcher, symbol, timeframe, initial_capital, commission):
    short_period = trial.suggest_int("short_period", 5, 30)
    long_period = trial.suggest_int("long_period", 30, 150)
    limit = trial.suggest_categorical("limit", [100, 200, 500])
    rsi_period = trial.suggest_int("rsi_period", 10, 20)

    try:
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, limit)
        strategy_data = moving_average_strategy(data.copy(), short_period, long_period, rsi_period)
        _, orders, metrics = run_backtest(strategy_data, initial_capital, commission)

        model_params = {
            "short_period": short_period,
            "long_period": long_period,
            "limit": limit,
            "rsi_period": rsi_period
        }
        save_model_results(model_params, metrics["final_value"], orders, symbol, initial_capital)

        return metrics["sharpe_ratio"]
    except Exception:
        return -float('inf')


def optimize_backtest(data_fetcher, symbol, timeframe, initial_capital, commission, n_trials=50):
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, data_fetcher, symbol, timeframe, initial_capital, commission),
                   n_trials=n_trials)

    trials_folder = "trials"
    if not os.path.exists(trials_folder):
        os.makedirs(trials_folder)

    trials_df = pd.DataFrame([{
        "trial_number": trial.number,
        "short_period": trial.params["short_period"],
        "long_period": trial.params["long_period"],
        "limit": trial.params["limit"],
        "rsi_period": trial.params["rsi_period"],
        "sharpe_ratio": trial.value
    } for trial in study.trials])
    trials_df.to_csv(f"{trials_folder}/optuna_trials_{symbol.replace('/', '_')}.csv", index=False)

    best_params = study.best_params
    print(f"Лучшие параметры для {symbol}: {best_params}, Sharpe Ratio: {study.best_value:.2f}")

    data = data_fetcher.fetch_ohlcv(symbol, timeframe, best_params["limit"])
    strategy_data = moving_average_strategy(data.copy(), best_params["short_period"], best_params["long_period"],
                                            best_params["rsi_period"])
    backtest_data, orders, metrics = run_backtest(strategy_data, initial_capital, commission)

    return backtest_data, orders, metrics