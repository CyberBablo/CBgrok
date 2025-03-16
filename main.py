from exchange_adapter import ExchangeAdapter
from backtest import optimize_backtest
import pandas as pd
import os
import logging
from datetime import datetime

# Настройка логирования
log_folder = "log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{log_folder}/main_{timestamp}.log"

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def main():
    symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'DOGE/USDT']
    timeframe = '1h'
    initial_capital = 10000
    commission = 0.00075  # 0.075%
    n_trials = 50  # Количество итераций оптимизации

    adapter = ExchangeAdapter()
    results_df = pd.DataFrame(columns=["symbol", "final_value", "total_return_percent", "max_drawdown_percent", "sharpe_ratio"])

    for symbol in symbols:
        _, _, metrics = optimize_backtest(adapter, symbol, timeframe, initial_capital, commission, n_trials)
        new_row = pd.DataFrame([{
            "symbol": symbol,
            "final_value": metrics["final_value"],
            "total_return_percent": metrics["total_return_percent"],
            "max_drawdown_percent": metrics["max_drawdown_percent"],
            "sharpe_ratio": metrics["sharpe_ratio"]
        }])
        results_df = pd.concat([results_df, new_row], ignore_index=True)

    results_df.to_csv("backtest_results.csv", index=False)
    logging.info("Общие результаты:")
    logging.info(results_df.to_string())

if __name__ == "__main__":
    main()