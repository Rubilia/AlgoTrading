import pandas as pd
from strategies.Fractal_strategy_1 import FractalStrategy
from utils import symbol, basecoin, timeframe, binsizes
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials

if __name__ == '__main__':
    price_data = pd.read_csv(f'./binance\\{symbol}_{basecoin}--{timeframe}.csv')
    s = FractalStrategy(price_data)
    fspace = s.get_hyperparameter_space()
    s.compute_indicators()


    def f(params):
        strategy = FractalStrategy(price_data)
        strategy.set_strategy_hyperparameters(params)
        strategy.compute_indicators()

        total_time, num_of_trades, successful_orders, growth = strategy.partial_test(40)

        order_freq = num_of_trades / total_time

        if order_freq < 1 / (24 * 60):
            loss = -100 - 1 / (order_freq + 1e-5)
        elif num_of_trades == 0 or successful_orders / num_of_trades < .2:
            loss = - 49.5 * num_of_trades / successful_orders - 10
        elif growth / total_time * 100 * 24 * 60 < 5:
            loss = 10 / (growth / total_time - .5 / (24 * 60) - 1)
        else:
            loss = growth / num_of_trades * 100

        return {'loss': -loss, 'status': STATUS_OK, 'total_orders': num_of_trades, 'win_ratio': successful_orders / (num_of_trades + 1e-5) * 100, 'growth': growth}


    trials = Trials()
    best = fmin(fn=f, space=fspace, algo=tpe.suggest, max_evals=1000, trials=trials)
    print('best params: ' + str(best))

    # Baseline
    print('=' * 25 + 'BASELINE MODEL' + '=' * 25)
    total_time, num_of_trades, successful_orders, growth = s.partial_test(1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1)
    print(f'Total orders: {num_of_trades}')
    print(f'Win ratio: %.2f' % (successful_orders / (num_of_trades + 1e-5) * 100) + '%')
    print(f'Time:  %.3f days' % (total_time / 24 / 60))
    print(f'Growth per day: {growth * 100 / (total_time / 24 / 60)}%')
    print(f'Total growth: {growth * 100}%')
    # Learned model
    s = FractalStrategy(price_data)
    s.set_strategy_hyperparameters(best)
    s.compute_indicators()
    print('='*25 + 'OPTIMIZED MODEL' + '=' * 25)

    total_time, num_of_trades, successful_orders, growth = s.partial_test(1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1)
    print(f'Total orders: {num_of_trades}')
    print(f'Win ratio: %.2f' % (successful_orders / (num_of_trades + 1e-5) * 100) + '%')
    print(f'Time:  %.3f days' % (total_time / 24 / 60))
    print(f'Growth per day: {growth * 100 / (total_time / 24 / 60)}%')
    print(f'Total growth: {growth * 100}%')

