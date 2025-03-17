import sys
import pandas as pd
import os
import logging
from datetime import datetime
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
from cb_grok.optimization.optimization import optimize_backtest
from cb_grok.backtest.backtest import run_backtest
from cb_grok.live_trading import live_trading
import asyncio


def main(mode, exchange_name='binance', api_key=None, api_secret=None, symbols=None, timeframe='1h',
         initial_capital=10000, commission=0.00075, n_trials=100, model_file=None, telegram_token=None,
         telegram_chat_id=None, category='linear'):
    """Запускает программу в указанном режиме."""
    if symbols is None:
        symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'DOGE/USDT', 'TRX/USDT']

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

    adapter = ExchangeAdapter(exchange_name, api_key, api_secret)

    if mode == 'optimizer':
        results_df = pd.DataFrame(columns=["symbol", "final_value", "total_return_percent",
                                           "max_drawdown_percent", "sharpe_ratio", "num_orders"])
        for symbol in symbols:
            logger.info(f"Начинаем оптимизацию для {symbol}")
            backtest_data, orders, metrics, num_orders = optimize_backtest(
                adapter, symbol, timeframe, initial_capital, commission, n_trials, logger)
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
        logger.info("Общие результаты оптимизации:")
        logger.info(results_df.to_string())

    elif mode == 'backtest':
        if not model_file:
            raise ValueError("Для режима backtest требуется указать файл модели (--model_file)")
        from cb_grok.run_model import run_model
        run_model(model_file, initial_capital, commission)
        logger.info(f"Бэктест завершен для модели {model_file}")

    elif mode == 'live_trading':
        if not (model_file and telegram_token and telegram_chat_id):
            raise ValueError("Для live_trading требуется model_file, telegram_token и telegram_chat_id")
        asyncio.run(live_trading(model_file, telegram_token, telegram_chat_id, mode="production",
                                 initial_capital=initial_capital, exchange_name=exchange_name,
                                 api_key=api_key, api_secret=api_secret, category=category, timeframe=timeframe))
        logger.info("Запущена торговля в реальном времени")

    else:
        raise ValueError(f"Неверный режим: {mode}. Используйте 'optimizer', 'backtest' или 'live_trading'")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <mode> [--exchange_name] [--api_key] [--api_secret] [--symbols] "
              "[--timeframe] [--initial_capital] [--commission] [--n_trials] [--model_file] "
              "[--telegram_token] [--telegram_chat_id] [--category]")
        sys.exit(1)

    mode = sys.argv[1]
    args = {arg.split('=')[0].strip('--'): arg.split('=')[1] for arg in sys.argv[2:] if '=' in arg}

    exchange_name = args.get('exchange_name', 'binance')
    api_key = args.get('api_key')
    api_secret = args.get('api_secret')
    symbols = args.get('symbols', None)
    if symbols:
        symbols = symbols.split(',')
    timeframe = args.get('timeframe', '1h')
    initial_capital = float(args.get('initial_capital', 10000))
    commission = float(args.get('commission', 0.00075))
    n_trials = int(args.get('n_trials', 100))
    model_file = args.get('model_file')
    telegram_token = args.get('telegram_token')
    telegram_chat_id = args.get('telegram_chat_id')
    category = args.get('category', 'linear')

    main(mode, exchange_name, api_key, api_secret, symbols, timeframe, initial_capital, commission,
         n_trials, model_file, telegram_token, telegram_chat_id, category)