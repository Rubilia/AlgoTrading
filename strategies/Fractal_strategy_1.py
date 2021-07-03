from Strategy import Strategy, Data, Hyperparameter, DiscreteHyperparameter, Trade
from typing import List, Tuple, Dict
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials


class FractalStrategy(Strategy):
    def __init__(self, df_data, show_trades=False):
        super().__init__(df_data)
        self.show_trades = show_trades
        self.profit_multiplier = Hyperparameter(0.8, 2.5, 1.2)
        self.stop_multiplier = Hyperparameter(1., 2., 1)
        self.order_risk_limiter = Hyperparameter(0.3, 1., 0.4)
        self.ema_n = DiscreteHyperparameter(list(range(100, 500)), 200)
        self.fractal_n = DiscreteHyperparameter(list(range(3, 7)), 5)

    def set_strategy_hyperparameters(self, values: Dict):
        self.profit_multiplier.set_value(values['profit_multiplier'])
        self.stop_multiplier.set_value(values['stop_multiplier'])
        self.order_risk_limiter.set_value(values['order_risk_limiter'])
        self.ema_n.set_value(values['ema_n'])
        self.fractal_n.set_value(values['fractal_n'])

    def get_hyperparameter_space(self) -> Dict[str, float]:
        space = dict()
        space['profit_multiplier'] = hp.uniform('profit_multiplier', self.profit_multiplier.get_min_value(), self.profit_multiplier.get_max_value())
        space['stop_multiplier'] = hp.uniform('stop_multiplier', self.stop_multiplier.get_min_value(), self.stop_multiplier.get_max_value())
        space['order_risk_limiter'] = hp.uniform('order_risk_limiter', self.order_risk_limiter.get_min_value(), self.order_risk_limiter.get_max_value())
        space['ema_n'] = hp.choice('ema_n', self.ema_n.values)
        space['fractal_n'] = hp.choice('fractal_n', self.fractal_n.values)
        return space

    def get_platform_hyperparameters(self):
        return [self.fee]

    def set_platform_hyperparameters(self, values: List[float]):
        self.fee.set_value(values[0])

    def compute_indicators(self):
        for i, data in enumerate(self.price_data):
            self.compute_EMA(self.ema_n.get_value(), data)
            self.compute_WilliamsFractal(self.fractal_n.get_value(), data)
            self.t_min[i] = max(self.ema_n.get_value(), self.fractal_n.get_value() + 1)

    def find_latest_top_fractal(self, fractals, t, Close_data, Open_data, EMA):
        p = t - 2
        while p > 0 and Close_data.get(p) >= EMA.get(p) and Open_data.get(p) >= EMA.get(p):
            if fractals.get(p):
                return p
            p -= 1
        return -1

    def find_latest_bottom_fractal(self, fractals, t, Close_data, Open_data, EMA):
        p = t - 2
        while p > 0 and Close_data.get(p) <= EMA.get(p) and Open_data.get(p) <= EMA.get(p):
            if fractals.get(p):
                return p
            p -= 1
        return -1

    def place_trade(self, t, t_min, price_data):
        if price_data['Open'].get(t) >= price_data[f'EMA{self.ema_n.get_value()}'].get(t) and price_data['Close'].get(t)\
                >= price_data[f'EMA{self.ema_n.get_value()}'].get(t):
            # Place long
            top_fractal = self.find_latest_top_fractal(price_data[f'BearFractal{self.fractal_n.get_value()}'], t,
                                                       price_data['Close'],
                                                       price_data['Open'],
                                                       price_data[f'EMA{self.ema_n.get_value()}'])
            if top_fractal < t_min or price_data['Close'].get(t) < price_data['High'].get(top_fractal):
                return None, False

            # Don`t place a trade if it is too volatile
            if 1 - (price_data['Low'].get(t) / self.stop_multiplier.get_value()) / price_data['Close'].get(
                    t) >= self.order_risk_limiter.get_value():
                return None, False

            entry = price_data['Close'].get(t)
            stop_loss = price_data['Low'].get(t) + (price_data['Low'].get(t) - entry) * self.stop_multiplier.get_value()
            take_profit = price_data['Close'].get(t) + self.profit_multiplier.get_value() * (
                    price_data['Close'].get(t) - price_data['Low'].get(t))

            return Trade('Long', entry, 0, take_profit, stop_loss, t), True

        elif price_data['Open'].get(t) <= price_data[f'EMA{self.ema_n.get_value()}'].get(t) and \
                price_data['Close'].get(t) <= price_data[
            f'EMA{self.ema_n.get_value()}'].get(t):
            # Place short
            bottom_fractal = self.find_latest_bottom_fractal(
                price_data[f'BullFractal{self.fractal_n.get_value()}'], t,
                price_data['Close'],
                price_data['Open'], price_data[f'EMA{self.ema_n.get_value()}'])
            if bottom_fractal < t_min or price_data['Close'].get(t) > price_data['Low'].get(bottom_fractal):
                return None, False

            # Don`t place a trade if it is too volatile
            if 1 - price_data['Close'].get(t) / (price_data['High'].get(
                    t) * self.stop_multiplier.get_value()) >= self.order_risk_limiter.get_value():
                return None, False

            entry = price_data['Close'].get(t)
            stop_loss = price_data['High'].get(t) + (price_data['High'].get(t) - entry) * self.stop_multiplier.get_value()
            take_profit = price_data['Close'].get(t) + self.profit_multiplier.get_value() * (
                    price_data['Close'].get(t) - price_data['High'].get(t))
            return Trade('Short', entry, 0, take_profit, stop_loss, t), True
        return None, False

    def end_trade(self, t, data: Trade, price_data) -> Tuple[bool, float]:
        order_type = data.type
        stop_loss = data.stop_loss
        entry = data.entry
        take_profit = data.take_profit
        t_entry = data.t_entry
        if order_type == 'Long' and price_data['Low'].get(t) <= stop_loss:
            # Long order failed
            growth = stop_loss / entry - 1
            if self.show_trades:
                print(
                    f'Failed Long trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {growth * 100}%')
            return True, growth
        elif order_type == 'Long' and price_data['High'].get(t) >= take_profit:
            # Long trade succeeded
            growth = take_profit / entry - 1
            if self.show_trades:
                print(
                    f'Successful Long trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {growth * 100}%')
            return True, growth
        elif order_type == 'Short' and price_data['Low'].get(t) <= take_profit:
            # Short trade succeeded
            growth = entry / take_profit - 1
            if self.show_trades:
                print(
                    f'Successful Short trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {growth * 100}%')
            return True, growth
        elif order_type == 'Short' and price_data['Low'].get(t) >= stop_loss:
            # Short trade failed
            growth = stop_loss / entry - 1
            if self.show_trades:
                print(
                    f'Failed Short trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {growth * 100}%')
            return True, growth
        return False, 0.

