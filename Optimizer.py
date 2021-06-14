import pandas as pd
from strategies.Fractal_strategy_1 import FractalStrategy
from utils import symbol, basecoin, timeframe
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials

if __name__ == '__main__':
    price_data = pd.read_csv(f'./binance\\{symbol}_{basecoin}--{timeframe}.csv')
    s = FractalStrategy(price_data)
    fspace = s.get_hyperparameter_space()


    def f(params):
        strategy = FractalStrategy(price_data)
        strategy.set_strategy_hyperparameters(params)
        strategy.compute_indicators()

        total_orders, win_ratio, trading_time, growth = strategy.test_strategy()

        if total_orders == 0 or (total_orders == 1 and win_ratio == 0.):
            loss = -10
        else:
            loss = growth / total_orders

        return {'loss': -loss, 'status': STATUS_OK, 'total_orders': total_orders, 'win_ratio': win_ratio, 'growth': growth}


    trials = Trials()
    best = fmin(fn=f, space=fspace, algo=tpe.suggest, max_evals=50, trials=trials)
    print('best: ' + str(best))

    # print('trials:')
    # for trial in trials.trials[len(trials.trials) - 4:]:
    #     print(trial)
    s.set_strategy_hyperparameters(best)
    s.compute_indicators()

    total_orders, win_ratio, trading_time, growth = s.test_strategy()
    print(f'Total orders: {total_orders}')
    print(f'Win ratio: %.2f' % (win_ratio) + '%')
    print(f'Time:  %.3f days' % (trading_time))
    print(f'Total growth: {growth}%')
    print(f'Time:  %.3f days' % (trading_time))

