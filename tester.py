import pandas as pd

from strategies.Fractal.Fractal_strategy import FractalStrategy
from utils import symbol, basecoin, timeframe

if __name__ == '__main__':
    price_data = pd.read_csv(f'./binance\\{symbol}_{basecoin}--{timeframe}.csv')
    s = FractalStrategy(price_data, True)

    best = {'ema_n': 69, 'fractal_n': 3, 'order_risk_limiter': 0.4995118173549132, 'profit_multiplier': 2.7894229678355105, 'stop_multiplier': 1.8689680623597325}
    s.set_strategy_hyperparameters(best)
    s.compute_indicators()

    total_orders, win_ratio, trading_time, growth = s.test_strategy()
    print(f'Total orders: {total_orders}')
    print(f'Win ratio: %.2f' % (win_ratio) + '%')
    print(f'Time:  %.3f days' % (trading_time))
    print(f'Total growth: {growth}%')
