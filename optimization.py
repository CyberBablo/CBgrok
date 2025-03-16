import optuna
import pandas as pd
from strategy import moving_average_strategy
from backtest import run_backtest
from utils import save_model_results
import os
import json
import hashlib
from datetime import datetime

def optimize_backtest(data_fetcher, symbol, timeframe, initial_capital, commission, n_trials=100, logger=None):
    """
    Оптимизирует параметры стратегии с использованием Optuna и сохраняет лучшие параметры в JSON-файл.

    :param data_fetcher: Объект для загрузки данных.
    :param symbol: Символ торговой пары.
    :param timeframe: Таймфрейм.
    :param initial_capital: Начальный капитал.
    :param commission: Комиссия.
    :param n_trials: Количество испытаний.
    :param logger: Объект для логирования.
    :return: Кортеж (backtest_data, orders, metrics, num_orders) для лучших параметров.
    """
    def objective(trial):
        # Определяем параметры для оптимизации
        params = {
            "short_period": trial.suggest_int("short_period", 5, 50),
            "long_period": trial.suggest_int("long_period", 20, 200),
            "limit": trial.suggest_categorical("limit", [200, 500, 1000]),
            "rsi_period": trial.suggest_int("rsi_period", 10, 20),
            "atr_period": trial.suggest_int("atr_period", 10, 20),
            "buy_rsi_threshold": trial.suggest_float("buy_rsi_threshold", 10, 60),
            "sell_rsi_threshold": trial.suggest_float("sell_rsi_threshold", 40, 90),
            "stop_loss_multiplier": trial.suggest_float("stop_loss_multiplier", 1.0, 3.0),
            "take_profit_multiplier": trial.suggest_float("take_profit_multiplier", 2.0, 5.0),
            "ema_short_period": trial.suggest_int("ema_short_period", 20, 100),
            "ema_long_period": trial.suggest_int("ema_long_period", 100, 300),
            "use_trend_filter": trial.suggest_categorical("use_trend_filter", [True, False]),
            "use_rsi_filter": trial.suggest_categorical("use_rsi_filter", [True, False])
        }

        # Корректируем limit, если он меньше максимального периода
        required_limit = max(params["long_period"], params["ema_long_period"])
        if params["limit"] < required_limit:
            params["limit"] = required_limit

        try:
            # Загружаем данные
            data = data_fetcher.fetch_ohlcv(symbol, timeframe, params["limit"])
            # Применяем стратегию
            strategy_data = moving_average_strategy(
                data.copy(),
                short_period=params["short_period"],
                long_period=params["long_period"],
                rsi_period=params["rsi_period"],
                atr_period=params["atr_period"],
                buy_rsi_threshold=params["buy_rsi_threshold"],
                sell_rsi_threshold=params["sell_rsi_threshold"],
                ema_short_period=params["ema_short_period"],
                ema_long_period=params["ema_long_period"],
                use_trend_filter=params["use_trend_filter"],
                use_rsi_filter=params["use_rsi_filter"],
                debug=False,
                logger=logger
            )
            # Запускаем бэктест
            _, orders, metrics, num_orders = run_backtest(
                strategy_data,
                initial_capital,
                commission,
                params["stop_loss_multiplier"],
                params["take_profit_multiplier"]
            )

            # Сохраняем результаты в order_bin
            save_model_results(params, metrics["final_value"], orders, symbol, initial_capital)

            return metrics["sharpe_ratio"]
        except Exception as e:
            if logger:
                logger.error(f"Ошибка в trial для {symbol}: {e}")
            return -float('inf')

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    # Получаем лучшие параметры
    best_params = study.best_params
    if logger:
        logger.info(f"Лучшие параметры для {symbol}: {best_params}, Sharpe Ratio: {study.best_value:.2f}")

    # Корректируем limit для лучших параметров
    required_limit = max(best_params["long_period"], best_params["ema_long_period"])
    if best_params["limit"] < required_limit:
        best_params["limit"] = required_limit

    # Генерируем хэш только на основе параметров модели
    params_str = json.dumps(best_params, sort_keys=True)
    hash_object = hashlib.sha256(params_str.encode())
    hash_hex = hash_object.hexdigest()[:16]

    # Генерируем временную метку
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Создаём директорию, если её нет
    best_models_folder = "library/best_models_params"
    if not os.path.exists(best_models_folder):
        os.makedirs(best_models_folder)

    # Имя файла: hash_timestamp.json
    best_model_filename = f"{best_models_folder}/{hash_hex}_{timestamp}.json"

    # Сохраняем лучшие параметры вместе с symbol и timeframe
    best_params_with_meta = best_params.copy()
    best_params_with_meta["symbol"] = symbol
    best_params_with_meta["timeframe"] = timeframe
    with open(best_model_filename, 'w') as f:
        json.dump(best_params_with_meta, f, indent=4)

    if logger:
        logger.info(f"Лучшие параметры сохранены в {best_model_filename}")

    # Выполняем финальный бэктест с лучшими параметрами
    data = data_fetcher.fetch_ohlcv(symbol, timeframe, best_params["limit"])
    strategy_data = moving_average_strategy(
        data.copy(),
        short_period=best_params["short_period"],
        long_period=best_params["long_period"],
        rsi_period=best_params["rsi_period"],
        atr_period=best_params["atr_period"],
        buy_rsi_threshold=best_params["buy_rsi_threshold"],
        sell_rsi_threshold=best_params["sell_rsi_threshold"],
        ema_short_period=best_params["ema_short_period"],
        ema_long_period=best_params["ema_long_period"],
        use_trend_filter=best_params["use_trend_filter"],
        use_rsi_filter=best_params["use_rsi_filter"],
        debug=False,
        logger=logger
    )
    return run_backtest(
        strategy_data,
        initial_capital,
        commission,
        best_params["stop_loss_multiplier"],
        best_params["take_profit_multiplier"]
    )