import pandas as pd
import numpy as np
from strategy import moving_average_strategy
from json_logger import save_model_results
import optuna
import os


def run_backtest(data: pd.DataFrame, initial_capital: float, commission: float, stop_loss_multiplier: float = 1.5,
                 take_profit_multiplier: float = 3.0):
    capital = initial_capital
    assets = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    orders = []

    for i in range(len(data) - 1):
        signal = data['signal'].iloc[i]
        next_open_price = data['open'].iloc[i + 1]
        timestamp = data.index[i + 1].isoformat()
        atr = data['atr'].iloc[i]

        if assets > 0:
            current_price = data['close'].iloc[i]
            if current_price <= stop_loss:
                capital = assets * next_open_price * (1 - commission)
                orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                               "reason": "stop_loss"})
                assets = 0
            elif current_price >= take_profit:
                capital = assets * next_open_price * (1 - commission)
                orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                               "reason": "take_profit"})
                assets = 0

        if signal == 1 and capital > 0:
            assets = capital / next_open_price * (1 - commission)
            capital = 0
            entry_price = next_open_price
            stop_loss = entry_price - atr * stop_loss_multiplier
            take_profit = entry_price + atr * take_profit_multiplier
            orders.append({"action": "buy", "amount": assets, "price": next_open_price, "timestamp": timestamp})
        elif signal == -1 and assets > 0:
            capital = assets * next_open_price * (1 - commission)
            orders.append({"action": "sell", "amount": assets, "price": next_open_price, "timestamp": timestamp,
                           "reason": "signal"})
            assets = 0

        data.loc[data.index[i + 1], 'portfolio_value'] = capital + assets * data['close'].iloc[i + 1]

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
    # Оптимизируемые параметры
    short_period = trial.suggest_int("short_period", 5, 50)
    long_period = trial.suggest_int("long_period", 20, 200)
    limit = trial.suggest_categorical("limit", [200, 500, 1000])  # Увеличен минимальный лимит до 200
    rsi_period = trial.suggest_int("rsi_period", 10, 20)
    atr_period = trial.suggest_int("atr_period", 10, 20)
    buy_rsi_threshold = trial.suggest_float("buy_rsi_threshold", 10, 60)  # Расширен диапазон
    sell_rsi_threshold = trial.suggest_float("sell_rsi_threshold", 40, 90)  # Расширен диапазон
    stop_loss_multiplier = trial.suggest_float("stop_loss_multiplier", 1.0, 3.0)
    take_profit_multiplier = trial.suggest_float("take_profit_multiplier", 2.0, 5.0)
    ema_short_period = trial.suggest_int("ema_short_period", 20, 100)
    ema_long_period = trial.suggest_int("ema_long_period", 100, 300)
    use_trend_filter = trial.suggest_categorical("use_trend_filter", [True, False])
    use_rsi_filter = trial.suggest_categorical("use_rsi_filter", [True, False])

    try:
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, limit)
        strategy_data = moving_average_strategy(data.copy(), short_period, long_period, rsi_period,
                                                atr_period=atr_period,
                                                buy_rsi_threshold=buy_rsi_threshold,
                                                sell_rsi_threshold=sell_rsi_threshold,
                                                ema_short_period=ema_short_period, ema_long_period=ema_long_period,
                                                use_trend_filter=use_trend_filter, use_rsi_filter=use_rsi_filter,
                                                debug=True)
        _, orders, metrics = run_backtest(strategy_data, initial_capital, commission, stop_loss_multiplier,
                                          take_profit_multiplier)

        model_params = {
            "short_period": short_period,
            "long_period": long_period,
            "limit": limit,
            "rsi_period": rsi_period,
            "atr_period": atr_period,
            "buy_rsi_threshold": buy_rsi_threshold,
            "sell_rsi_threshold": sell_rsi_threshold,
            "stop_loss_multiplier": stop_loss_multiplier,
            "take_profit_multiplier": take_profit_multiplier,
            "ema_short_period": ema_short_period,
            "ema_long_period": ema_long_period,
            "use_trend_filter": use_trend_filter,
            "use_rsi_filter": use_rsi_filter
        }
        save_model_results(model_params, metrics["final_value"], orders, symbol, initial_capital)

        return metrics["sharpe_ratio"]
    except Exception as e:
        print(f"Ошибка в trial для {symbol}: {e}")
        return -float('inf')


def optimize_backtest(data_fetcher, symbol, timeframe, initial_capital, commission, n_trials=100):
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
        "atr_period": trial.params["atr_period"],
        "buy_rsi_threshold": trial.params["buy_rsi_threshold"],
        "sell_rsi_threshold": trial.params["sell_rsi_threshold"],
        "stop_loss_multiplier": trial.params["stop_loss_multiplier"],
        "take_profit_multiplier": trial.params["take_profit_multiplier"],
        "ema_short_period": trial.params["ema_short_period"],
        "ema_long_period": trial.params["ema_long_period"],
        "use_trend_filter": trial.params["use_trend_filter"],
        "use_rsi_filter": trial.params["use_rsi_filter"],
        "sharpe_ratio": trial.value
    } for trial in study.trials])
    trials_df.to_csv(f"{trials_folder}/optuna_trials_{symbol.replace('/', '_')}.csv", index=False)

    best_params = study.best_params
    print(f"Лучшие параметры для {symbol}: {best_params}, Sharpe Ratio: {study.best_value:.2f}")

    data = data_fetcher.fetch_ohlcv(symbol, timeframe, best_params["limit"])
    strategy_data = moving_average_strategy(data.copy(), best_params["short_period"], best_params["long_period"],
                                            best_params["rsi_period"], atr_period=best_params["atr_period"],
                                            buy_rsi_threshold=best_params["buy_rsi_threshold"],
                                            sell_rsi_threshold=best_params["sell_rsi_threshold"],
                                            ema_short_period=best_params["ema_short_period"],
                                            ema_long_period=best_params["ema_long_period"],
                                            use_trend_filter=best_params["use_trend_filter"],
                                            use_rsi_filter=best_params["use_rsi_filter"], debug=True)
    backtest_data, orders, metrics = run_backtest(strategy_data, initial_capital, commission,
                                                  best_params["stop_loss_multiplier"],
                                                  best_params["take_profit_multiplier"])

    return backtest_data, orders, metrics