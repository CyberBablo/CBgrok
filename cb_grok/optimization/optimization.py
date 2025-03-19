import optuna
import pandas as pd
from cb_grok.strategies.moving_average_strategy import moving_average_strategy
from cb_grok.backtest.backtest import run_backtest
from cb_grok.utils.utils import save_model_results
import os
import json
import hashlib
from datetime import datetime

def optimize_backtest(data_fetcher, symbol, timeframe, initial_capital, commission, n_trials=100, logger=None):
    """
    Оптимизирует параметры стратегии с использованием Optuna на обучающем наборе и валидирует на валидационном наборе.

    :param data_fetcher: Объект для загрузки данных.
    :param symbol: Символ торговой пары.
    :param timeframe: Таймфрейм.
    :param initial_capital: Начальный капитал.
    :param commission: Комиссия.
    :param n_trials: Количество испытаний.
    :param logger: Объект для логирования.
    :return: Кортеж (backtest_data, orders, metrics, num_orders) для лучших параметров на валидационном наборе.
    """
    # Определение даты разделения: 1 марта 2025 года
    split_date = pd.to_datetime("2025-03-01 00:00:00")
    # Загрузка данных для обучения и валидации
    full_data = data_fetcher.fetch_ohlcv(symbol, timeframe, limit=15000, total_limit=15000)  # Увеличен лимит до 10,000 свечей
    train_data = full_data[full_data.index < split_date]
    val_data = full_data[full_data.index >= split_date]
    print(val_data.head())
    print(val_data.tail())

    print(len(full_data), len(train_data), len(val_data))

    # exit(0)
    # Проверка минимального объема данных
    # if len(train_data) < 5000 or len(val_data) < 1000:
    #     if logger:
    #         logger.error(f"Недостаточно данных: Обучающий набор = {len(train_data)} свечей, "
    #                      f"Валидационный набор = {len(val_data)} свечей. Требуется минимум 5000 и 1000 соответственно.")
    #     raise ValueError(f"Недостаточно данных: Обучающий набор = {len(train_data)} свечей, "
    #                      f"Валидационный набор = {len(val_data)} свечей.")



    if logger:
        logger.info(f"Обучающий набор: {len(train_data)} свечей, Валидационный набор: {len(val_data)} свечей")



    def objective(trial):
        # Определяем параметры для оптимизации с расширенными диапазонами
        params = {
            "short_period": trial.suggest_int("short_period", 5, 15),
            "long_period": trial.suggest_int("long_period", 20, 50),
            "limit": trial.suggest_categorical("limit", [1000, 2000, 3000]),
            "rsi_period": trial.suggest_int("rsi_period", 8, 16),
            "atr_period": trial.suggest_int("atr_period", 8, 16),
            "buy_rsi_threshold": trial.suggest_float("buy_rsi_threshold", 15, 35),  # Расширен диапазон
            "sell_rsi_threshold": trial.suggest_float("sell_rsi_threshold", 65, 85),  # Расширен диапазон
            "stop_loss_multiplier": trial.suggest_float("stop_loss_multiplier", 0.8, 2.0),
            "take_profit_multiplier": trial.suggest_float("take_profit_multiplier", 1.5, 3.5),
            "ema_short_period": trial.suggest_int("ema_short_period", 15, 40),
            "ema_long_period": trial.suggest_int("ema_long_period", 80, 150),
            "use_trend_filter": trial.suggest_categorical("use_trend_filter", [True, False]),
            "use_rsi_filter": trial.suggest_categorical("use_rsi_filter", [True, False]),
            "adx_period": trial.suggest_int("adx_period", 8, 16),
            "adx_threshold": trial.suggest_float("adx_threshold", 15, 30),
            "use_adx_filter": trial.suggest_categorical("use_adx_filter", [True, False]),
            "atr_threshold": trial.suggest_float("atr_threshold", 0.0, 1.0)  # Расширен диапазон
        }
        # Штраф за сложность модели
        complexity_penalty = (int(params["use_trend_filter"]) + int(params["use_rsi_filter"]) +
                              int(params["use_adx_filter"])) * -0.05

        try:
            # Тестирование на обучающем наборе
            strategy_data_train = moving_average_strategy(
                train_data.copy(),
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
                adx_period=params["adx_period"],
                use_adx_filter=params["use_adx_filter"],
                adx_threshold=params["adx_threshold"],
                atr_threshold=params["atr_threshold"],
                debug=False,
                logger=logger
            )
            _, _, metrics_train, num_orders_train = run_backtest(
                strategy_data_train,
                initial_capital,
                commission,
                params["stop_loss_multiplier"],
                params["take_profit_multiplier"]
            )
            if num_orders_train < 10:
                if logger:
                    logger.debug(f"Trial {trial.number}: Недостаточно ордеров на обучении ({num_orders_train})")
                return -float('inf')

            # Тестирование на валидационном наборе
            strategy_data_val = moving_average_strategy(
                val_data.copy(),
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
                adx_period=params["adx_period"],
                use_adx_filter=params["use_adx_filter"],
                adx_threshold=params["adx_threshold"],
                atr_threshold=params["atr_threshold"],
                debug=False,
                logger=logger
            )
            _, _, metrics_val, num_orders_val = run_backtest(
                strategy_data_val,
                initial_capital,
                commission,
                params["stop_loss_multiplier"],
                params["take_profit_multiplier"]
            )
            if num_orders_val < 5:
                if logger:
                    logger.debug(f"Trial {trial.number}: Недостаточно ордеров на валидации ({num_orders_val})")
                return -float('inf')

            # Целевая функция: Среднее Sharpe Ratio с учетом числа сделок
            sharpe_combined = (metrics_train["sharpe_ratio"] + metrics_val["sharpe_ratio"]) / 2
            return sharpe_combined + complexity_penalty

        except Exception as e:
            if logger:
                logger.error(f"Ошибка в trial {trial.number} для {symbol}: {e}")
            return -float('inf')

    # Настройка логирования Optuna
    optuna.logging.set_verbosity(optuna.logging.INFO)
    if logger:
        optuna.logging.enable_default_handler()
        optuna.logging.enable_propagation()

    # Создание и запуск оптимизации
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    if logger:
        logger.info(f"Лучшие параметры для {symbol}: {best_params}, Лучшее значение: {study.best_value:.2f}")

    # Финальная валидация на валидационном наборе
    try:
        strategy_data_val = moving_average_strategy(
            val_data.copy(),
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
            adx_period=best_params["adx_period"],
            use_adx_filter=best_params["use_adx_filter"],
            adx_threshold=best_params["adx_threshold"],
            atr_threshold=best_params["atr_threshold"],
            debug=True,  # Включен дебаг для анализа
            logger=logger
        )
        backtest_data, orders, metrics, num_orders = run_backtest(
            strategy_data_val,
            initial_capital,
            commission,
            best_params["stop_loss_multiplier"],
            best_params["take_profit_multiplier"]
        )
        if logger:
            logger.info(f"Результаты на валидационном наборе: Sharpe Ratio = {metrics['sharpe_ratio']:.2f}, "
                        f"Итоговый капитал = {metrics['final_value']:.2f}, Количество ордеров = {num_orders}")

        # Сохранение параметров даже при нулевом Sharpe Ratio для анализа
        if num_orders >= 5:
            params_str = json.dumps(best_params, sort_keys=True)
            hash_object = hashlib.sha256(params_str.encode())
            hash_hex = hash_object.hexdigest()[:16]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            best_model_filename = f"library/best_models_params/{hash_hex}_{timestamp}.json"
            best_params_with_meta = best_params.copy()
            best_params_with_meta["symbol"] = symbol
            best_params_with_meta["timeframe"] = timeframe
            best_params_with_meta["sharpe_ratio"] = metrics["sharpe_ratio"]
            best_params_with_meta["num_orders"] = num_orders
            with open(best_model_filename, 'w') as f:
                json.dump(best_params_with_meta, f, indent=4)
            if logger:
                logger.info(f"Лучшие параметры сохранены в {best_model_filename}")
        else:
            if logger:
                logger.warning(f"Параметры не сохранены: Количество ордеров ({num_orders}) < 5")

        return backtest_data, orders, metrics, num_orders

    except Exception as e:
        if logger:
            logger.error(f"Ошибка при валидации для {symbol}: {e}")
        raise