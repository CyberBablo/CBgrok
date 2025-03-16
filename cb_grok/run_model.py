import json
import argparse
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
from cb_grok.strategies.moving_average_strategy import moving_average_strategy
from cb_grok.backtest.backtest import run_backtest
from cb_grok.utils.utils import save_model_results

def run_model(filename, initial_capital, commission):
    """
    Запускает бэктест для модели с параметрами из файла.

    :param filename: Имя файла с параметрами модели (например, 4a5b6c7d8e9f0a1b_20250316_183512.json).
    :param initial_capital: Начальный капитал.
    :param commission: Комиссия за сделку.
    """
    # Путь к файлу с параметрами
    best_models_folder = "library/best_models_params"
    filepath = f"{best_models_folder}/{filename}"

    # Считываем параметры модели
    with open(filepath, 'r') as f:
        model_params_with_meta = json.load(f)

    # Извлекаем symbol и timeframe
    symbol = model_params_with_meta["symbol"]
    timeframe = model_params_with_meta["timeframe"]

    # Параметры модели без symbol и timeframe
    model_params = {k: v for k, v in model_params_with_meta.items() if k not in ["symbol", "timeframe"]}

    # Загружаем данные
    adapter = ExchangeAdapter()
    data = adapter.fetch_ohlcv(symbol, timeframe, model_params["limit"])

    # Применяем стратегию
    strategy_data = moving_average_strategy(
        data.copy(),
        short_period=model_params["short_period"],
        long_period=model_params["long_period"],
        rsi_period=model_params["rsi_period"],
        atr_period=model_params["atr_period"],
        buy_rsi_threshold=model_params["buy_rsi_threshold"],
        sell_rsi_threshold=model_params["sell_rsi_threshold"],
        ema_short_period=model_params["ema_short_period"],
        ema_long_period=model_params["ema_long_period"],
        use_trend_filter=model_params["use_trend_filter"],
        use_rsi_filter=model_params["use_rsi_filter"],
        debug=False
    )

    # Запускаем бэктест
    backtest_data, orders, metrics, num_orders = run_backtest(
        strategy_data,
        initial_capital,
        commission,
        model_params["stop_loss_multiplier"],
        model_params["take_profit_multiplier"]
    )

    # Сохраняем результаты в order_bin с теми же параметрами
    save_model_results(model_params, metrics["final_value"], orders, symbol, initial_capital)

    print(f"Бэктест завершён для {symbol}. Итоговый капитал: {metrics['final_value']:.2f}, Количество ордеров: {num_orders}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск бэктеста для модели из best_models_params")
    parser.add_argument("filename", type=str, help="Имя файла с параметрами модели (например, 4a5b6c7d8e9f0a1b_20250316_183512.json)")
    parser.add_argument("initial_capital", type=float, help="Начальный капитал")
    parser.add_argument("commission", type=float, help="Комиссия за сделку")

    args = parser.parse_args()
    run_model(args.filename, args.initial_capital, args.commission)