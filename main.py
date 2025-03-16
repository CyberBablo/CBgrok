from exchange_adapter import ExchangeAdapter
from backtest import optimize_backtest
import pandas as pd

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
        # Добавляем результаты с помощью pd.concat
        new_row = pd.DataFrame([{
            "symbol": symbol,
            "final_value": metrics["final_value"],
            "total_return_percent": metrics["total_return_percent"],
            "max_drawdown_percent": metrics["max_drawdown_percent"],
            "sharpe_ratio": metrics["sharpe_ratio"]
        }])
        results_df = pd.concat([results_df, new_row], ignore_index=True)

    # Сохранение результатов в CSV
    results_df.to_csv("backtest_results.csv", index=False)
    print("\nОбщие результаты:")
    print(results_df)

if __name__ == "__main__":
    main()