import optuna
import pandas as pd
from strategy import moving_average_strategy
from backtest import run_backtest
from utils import save_model_results
import os

def objective(trial, data_fetcher, symbol, timeframe, initial_capital, commission, logger):
    """Целевая функция для оптимизации параметров стратегии."""
    short_period = trial.suggest_int("short_period", 5, 50)
    long_period = trial.suggest_int("long_period", 20, 200)
    limit = trial.suggest_categorical("limit", [200, 500, 1000])
    rsi_period = trial.suggest_int("rsi_period", 10, 20)
    atr_period = trial.suggest_int("atr_period", 10, 20)
    buy_rsi_threshold = trial.suggest_float("buy_rsi_threshold", 10, 60)
    sell_rsi_threshold = trial.suggest_float("sell_rsi_threshold", 40, 90)
    stop_loss_multiplier = trial.suggest_float("stop_loss_multiplier", 1.0, 3.0)
    take_profit_multiplier = trial.suggest_float("take_profit_multiplier", 2.0, 5.0)
    ema_short_period = trial.suggest_int("ema_short_period", 20, 100)
    ema_long_period = trial.suggest_int("ema_long_period", 100, 300)
    use_trend_filter = trial.suggest_categorical("use_trend_filter", [True, False])
    use_rsi_filter = trial.suggest_categorical("use_rsi_filter", [True, False])

    # Корректируем limit, если он меньше максимального периода
    required_limit = max(long_period, ema_long_period)
    if limit < required_limit:
        limit = required_limit

    try:
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, limit)
        strategy_data = moving_average_strategy(data.copy(), short_period, long_period, rsi_period,
                                                atr_period=atr_period,
                                                buy_rsi_threshold=buy_rsi_threshold,
                                                sell_rsi_threshold=sell_rsi_threshold,
                                                ema_short_period=ema_short_period, ema_long_period=ema_long_period,
                                                use_trend_filter=use_trend_filter, use_rsi_filter=use_rsi_filter,
                                                debug=False, logger=logger)
        _, orders, metrics, num_orders = run_backtest(strategy_data, initial_capital, commission, stop_loss_multiplier,
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
        if logger:
            logger.error(f"Ошибка в trial для {symbol}: {e}")
        return -float('inf')

def optimize_backtest(data_fetcher, symbol, timeframe, initial_capital, commission, n_trials=100, logger=None):
    """
    Оптимизирует параметры стратегии с использованием Optuna.

    :param data_fetcher: Объект для загрузки данных.
    :param symbol: Символ торговой пары.
    :param timeframe: Таймфрейм.
    :param initial_capital: Начальный капитал.
    :param commission: Комиссия.
    :param n_trials: Количество испытаний.
    :param logger: Объект для логирования.
    :return: Кортеж (backtest_data, orders, metrics, num_orders) для лучших параметров.
    """
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, data_fetcher, symbol, timeframe, initial_capital, commission, logger),
                   n_trials=n_trials)

    trials_folder = "trials"
    if not os.path.exists(trials_folder):
        os.makedirs(trials_folder)

    trials_df = pd.DataFrame([{
        "trial_number": trial.number,
        **trial.params,
        "sharpe_ratio": trial.value
    } for trial in study.trials])
    trials_df.to_csv(f"{trials_folder}/optuna_trials_{symbol.replace('/', '_')}.csv", index=False)

    best_params = study.best_params
    if logger:
        logger.info(f"Лучшие параметры для {symbol}: {best_params}, Sharpe Ratio: {study.best_value:.2f}")

    # Корректируем limit для лучших параметров
    required_limit = max(best_params["long_period"], best_params["ema_long_period"])
    if best_params["limit"] < required_limit:
        best_params["limit"] = required_limit

    data = data_fetcher.fetch_ohlcv(symbol, timeframe, best_params["limit"])
    strategy_data = moving_average_strategy(data.copy(), best_params["short_period"], best_params["long_period"],
                                            best_params["rsi_period"], atr_period=best_params["atr_period"],
                                            buy_rsi_threshold=best_params["buy_rsi_threshold"],
                                            sell_rsi_threshold=best_params["sell_rsi_threshold"],
                                            ema_short_period=best_params["ema_short_period"],
                                            ema_long_period=best_params["ema_long_period"],
                                            use_trend_filter=best_params["use_trend_filter"],
                                            use_rsi_filter=best_params["use_rsi_filter"], debug=False, logger=logger)
    return run_backtest(strategy_data, initial_capital, commission,
                        best_params["stop_loss_multiplier"],
                        best_params["take_profit_multiplier"])