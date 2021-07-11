import pandas as pd
from strategies.Fractal.Fractal_strategy import FractalStrategy
from utils import symbol, basecoin, timeframe

if __name__ == '__main__':
    price_data = pd.read_csv(f'./binance\\{symbol}_{basecoin}--{timeframe}.csv')
    strategy = FractalStrategy(price_data)
    strategy.compute_indicators()
    total_orders, win_ratio, trading_time, growth = strategy.test_strategy()
    print(f'Total orders: {total_orders}')
    print(f'Win ratio: %.2f' % (win_ratio) + '%')
    print(f'Time:  %.3f days' % (trading_time))
    print(f'Total growth: {growth}%')