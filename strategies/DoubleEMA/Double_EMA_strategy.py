from typing import List, Tuple, Dict

from hyperopt import hp

from Strategy import Strategy, Hyperparameter, DiscreteHyperparameter, Trade


class DoubleEMAStrategy(Strategy):
    def __init__(self, df_data, show_trades=False):
        super().__init__(df_data, show_trades=show_trades)
        self.profit_multiplier = Hyperparameter(0.8, 2.5, 1.5)
        self.stop_multiplier = Hyperparameter(.5, 3., 2)
        self.order_risk_limiter = Hyperparameter(0.3, 1., 0.4)
        self.ema_trend_n = DiscreteHyperparameter(list(range(60, 400 + 1)), 200)
        self.ema_signal_n = DiscreteHyperparameter(list(range(10, 90 + 1)), 50)
        self.atr_period = DiscreteHyperparameter(list(range(8, 25 + 1)), 14)
        self.true_range = DiscreteHyperparameter([0, 1], 1)
        self.n_out_of_trend = DiscreteHyperparameter([2, 3, 4, 5], 3)

    def set_strategy_hyperparameters(self, values: Dict):
        self.profit_multiplier.set_value(values['profit_multiplier'])
        self.stop_multiplier.set_value(values['stop_multiplier'])
        self.order_risk_limiter.set_value(values['order_risk_limiter'])
        self.ema_trend_n.set_value(values['ema_trend'])
        self.ema_signal_n.set_value(values['ema_signal'])
        self.atr_period.set_value(values['atr'])
        self.true_range.set_value(values['true_range'])
        self.n_out_of_trend.set_value(values['out_of_trend'])

    def get_hyperparameter_space(self) -> Dict[str, float]:
        space = dict()
        space['profit_multiplier'] = hp.uniform('profit_multiplier', self.profit_multiplier.get_min_value(),
                                                self.profit_multiplier.get_max_value())
        space['stop_multiplier'] = hp.uniform('stop_multiplier', self.stop_multiplier.get_min_value(),
                                              self.stop_multiplier.get_max_value())
        space['order_risk_limiter'] = hp.uniform('order_risk_limiter', self.order_risk_limiter.get_min_value(),
                                                 self.order_risk_limiter.get_max_value())
        space['ema_trend'] = hp.choice('ema_trend', self.ema_trend_n.values)
        space['ema_signal'] = hp.choice('ema_signal', self.ema_signal_n.values)
        space['atr'] = hp.choice('atr', self.atr_period.values)
        space['true_range'] = hp.choice('true_range', self.true_range.values)
        space['out_of_trend'] = hp.choice('out_of_trend', self.n_out_of_trend.values)
        return space

    def get_platform_hyperparameters(self):
        return [self.fee]

    def set_platform_hyperparameters(self, values: List[float]):
        self.fee.set_value(values[0])

    def compute_indicators(self):
        for i, data in enumerate(self.price_data):
            self.compute_EMA(self.ema_trend_n.get_value(), data, name='ema_trend', use_n=False)
            self.compute_EMA(self.ema_signal_n.get_value(), data, name='ema_signal', use_n=False)
            if self.true_range.get_value():
                self.compute_Avg_True_Range(self.atr_period.get_value(), data, use_n=False)
            else:
                self.compute_Avg_Range(self.atr_period.get_value(), data, name='ATR', use_n=False)

            self.t_min[i] = max(self.ema_trend_n.get_value(), self.ema_signal_n.get_value(),
                                self.atr_period.get_value())

    def find_cross(self, t, t_min, price_data):
        for p in range(t, t_min, -1):
            if ((price_data['ema_signal'][p - 1] - price_data['ema_trend'][p - 1]) <= 0 and
                    (price_data['ema_signal'][p] - price_data['ema_trend'][p]) > 0) or \
                ((price_data['ema_signal'][p - 1] - price_data['ema_trend'][p - 1]) < 0 and
                 (price_data['ema_signal'][p] - price_data['ema_trend'][p]) >= 0):
                # Long trade
                return p - 1, 'Long'
            elif ((price_data['ema_signal'][p - 1] - price_data['ema_trend'][p - 1]) >= 0 and
                    (price_data['ema_signal'][p] - price_data['ema_trend'][p]) < 0) or \
                ((price_data['ema_signal'][p - 1] - price_data['ema_trend'][p - 1]) > 0 and
                 (price_data['ema_signal'][p] - price_data['ema_trend'][p]) <= 0):
                # Long trade
                return p - 1, 'Short'
        return None, None

    def is_touch(self, t, price_data):
        return (price_data['High'][t] - price_data['ema_signal'][t]) * \
               (price_data['Low'][t] - price_data['ema_signal'][t]) < 0

    def find_touch(self, t_cross, t, price_data):
        for p in range(t, t_cross - 1, -1):
            if self.is_touch(p, price_data):
                return p
        return -1

    def place_trade(self, t, t_min, price_data):
        cross, order_type = self.find_cross(t, t_min, price_data)
        if cross is None:
            return None, False

        out_of_trend = 0
        if order_type == 'Long':
            # Place long order
            touch = self.find_touch(cross, t, price_data)
            if touch == -1:
                return None, False
            for p in range(cross + 1, t + 1):
                # Keep track of candles below trend EMA
                if price_data['Close'][p] < price_data['ema_trend'][t]:
                    out_of_trend += 1

                # Too many candles below trend ema
                if out_of_trend == self.n_out_of_trend.get_value():
                    return None, False

            # By this point we wait for price to close above signal EMA
            # Exit if cross is not found
            if price_data['Close'][t] <= price_data['ema_signal'][t]:
                return None, False

            # Cross found, place a trade
            entry = price_data['Close'].get(t)
            risk = self.stop_multiplier.get_value() * price_data['ATR'][t]
            stop_loss = price_data['Open'].get(t) - risk
            take_profit = price_data['Close'].get(t) + self.profit_multiplier.get_value() * risk
            return Trade('Long', entry, 0, take_profit, stop_loss, t), True
        elif order_type == 'Short':
            # Place short order
            touch = self.find_touch(cross, t, price_data)
            if touch == -1:
                return None, False
            for p in range(cross + 1, t + 1):
                # Keep track of candles above trend EMA
                if price_data['Close'][p] > price_data['ema_trend'][t]:
                    out_of_trend += 1

                # Too many candles below trend ema
                if out_of_trend >= self.n_out_of_trend.get_value():
                    return None, False

            # By this point we wait for price to close below signal EMA
            # Exit if cross is not found
            if price_data['Close'][t] >= price_data['ema_signal'][t]:
                return None, False

            # Cross found, place a trade
            entry = price_data['Close'].get(t)
            risk = self.stop_multiplier.get_value() * price_data['ATR'][t]
            stop_loss = price_data['Open'].get(t) + risk
            take_profit = price_data['Close'].get(t) - self.profit_multiplier.get_value() * risk
            return Trade('Short', entry, 0, take_profit, stop_loss, t), True

        return None, False
