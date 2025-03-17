from cb_grok.adapters.exchange_adapter import ExchangeAdapter
from cb_grok.optimization.optimization import optimize_backtest
import pandas as pd
import os
import logging
from datetime import datetime

def main():
    """Запускает оптимизацию и бэктест для списка символов."""
    symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'DOGE/USDT', 'TRX/USDT']
    timeframe = '1h'
    initial_capital = 10000
    commission = 0.00075  # 0.075%
    n_trials = 100

    # Настройка логирования
    log_folder = "log"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{log_folder}/main_{timestamp}.log"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    adapter = ExchangeAdapter()
    results_df = pd.DataFrame(columns=["symbol", "final_value", "total_return_percent",
                                       "max_drawdown_percent", "sharpe_ratio", "num_orders"])

    for symbol in symbols:
        logger.info(f"Начинаем оптимизацию для {symbol}")
        _, _, metrics, num_orders = optimize_backtest(adapter, symbol, timeframe, initial_capital,
                                                      commission, n_trials, logger)
        new_row = pd.DataFrame([{
            "symbol": symbol,
            "final_value": metrics["final_value"],
            "total_return_percent": metrics["total_return_percent"],
            "max_drawdown_percent": metrics["max_drawdown_percent"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "num_orders": num_orders
        }])
        results_df = pd.concat([results_df, new_row], ignore_index=True)
        logger.info(f"Завершена оптимизация для {symbol}: Sharpe Ratio = {metrics['sharpe_ratio']:.2f}, "
                    f"Количество ордеров = {num_orders}")

    results_df.to_csv("backtest_results.csv", index=False)
    logger.info("Общие результаты бэктеста:")
    logger.info(results_df.to_string())

if __name__ == "__main__":
    main()