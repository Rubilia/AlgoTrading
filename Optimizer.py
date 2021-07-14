import os
from pprint import pprint

import pandas as pd

from strategies.DoubleEMA.Double_EMA_strategy import DoubleEMAStrategy
from utils import symbol, basecoin, timeframe, binsizes
from hyperopt import fmin, tpe, STATUS_OK, Trials

if __name__ == '__main__':
    price_data = pd.read_csv(os.path.join('./binance', f'{symbol}_{basecoin}--{timeframe}.csv'))
    price_data = price_data
    s = DoubleEMAStrategy(price_data)
    fspace = s.get_hyperparameter_space()
    s.compute_indicators()


    def f(params):
        global Growths
        strategy = DoubleEMAStrategy(price_data)
        strategy.set_strategy_hyperparameters(params)
        strategy.compute_indicators()

        total_time, num_of_trades, successful_orders, growth = strategy.partial_test(25, min_len=60*4, max_len=60 * 24)

        # order_freq = num_of_trades / total_time
        # if order_freq < 1 / (24 * 60):
        #     loss = -100 - 1 / (order_freq + 1e-5)
        # elif num_of_trades == 0 or successful_orders / num_of_trades < .2:
        #     loss = - 49.5 * num_of_trades / successful_orders - 10
        # elif growth / total_time * 100 * 24 * 60 < 5:
        #     loss = 10 / (growth / total_time - .5 / (24 * 60) - 1)
        # else:
        loss = growth / total_time * 100 * 24 * 60
        Growths += [loss]
        # loss - growth per day % (relative to staked amount)

        return {'loss': -loss, 'status': STATUS_OK, 'total_orders': num_of_trades, 'win_ratio': successful_orders / (num_of_trades + 1e-5) * 100, 'growth': growth}

    Growths = []
    trials = Trials()
    best = fmin(fn=f, space=fspace, algo=tpe.suggest, max_evals=200, trials=trials)
    print('best params: ' + str(best))
    pprint(Growths)

    # Baseline
    print('=' * 25 + 'BASELINE MODEL' + '=' * 25)
    total_time, num_of_trades, successful_orders, growth = s.partial_test(1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1)
    print(f'Total orders: {num_of_trades}')
    print(f'Win ratio: %.2f' % (successful_orders / (num_of_trades + 1e-5) * 100) + '%')
    print(f'Time:  %.3f days' % (total_time / 24 / 60))
    print(f'Growth per day: {growth * 100 / (total_time / 24 / 60)}%')
    print(f'Total growth: {growth * 100}%')
    # Learned model
    s = DoubleEMAStrategy(price_data)
    s.set_strategy_hyperparameters(best)
    s.compute_indicators()
    print('='*25 + 'OPTIMIZED MODEL' + '=' * 25)

    total_time, num_of_trades, successful_orders, growth = s.partial_test(1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1, s.price_data[0].shape[0] * binsizes[timeframe] - s.t_min[0] - 1)
    print(f'Total orders: {num_of_trades}')
    print(f'Win ratio: %.2f' % (successful_orders / (num_of_trades + 1e-5) * 100) + '%')
    print(f'Time:  %.3f days' % (total_time / 24 / 60))
    print(f'Growth per day: {growth * 100 / (total_time / 24 / 60)}%')
    print(f'Total growth: {growth * 100}%')

