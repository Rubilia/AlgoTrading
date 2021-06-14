import pandas as pd
import numpy as np
import abc

from utils import binsizes, timeframe
from typing import Tuple, Dict


class Data:
    @abc.abstractmethod
    def __init__(self):
        raise NotImplementedError


class Trade:
    def __init__(self, type, entry, close, take_profit, stop_loss, t_entry):
        self.type = type
        self.entry = entry
        self.close = close
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.t_entry = t_entry


class Hyperparameter(object):
    @abc.abstractmethod
    def __init__(self, min_value, max_value, value):
        self.min_value = min_value
        self.max_value = max_value
        self.value = value

    def get_min_value(self):
        return self.min_value

    def get_max_value(self):
        return self.max_value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def clone(self):
        return Hyperparameter(self.min_value, self.max_value, self.value)

    def __str__(self):
        return f'Value: {self.get_value()}'


class DiscreteHyperparameter:
    def __init__(self, values: list, value):
        self.values = values
        self.value = value

    def get_values(self):
        return self.values

    def clone(self):
        return DiscreteHyperparameter(self.values, self.get_value())

    def get_value(self):
        return self.value

    def set_value(self, value):
        if not value in self.values:
            return False
        self.value = value


class Strategy:
    def __init__(self, df_data):
        self.price_data = df_data
        self.indicators = ['MA', 'EMA', 'BearFractal', 'BullFractal', 'Open', 'Low', 'High', 'Close']
        self.fee = Hyperparameter(0, 0.05, 0.001)
        self.t_min = 0

    def set_data(self, df_data):
        self.price_data = df_data

    def compute_MA(self, n):
        self.price_data[f'MA{n}'] = self.price_data['Close'].rolling(window=n).mean()

    def compute_EMA(self, n):
        self.price_data[f'EMA{n}'] = pd.Series.ewm(self.price_data['Close'], span=n).mean()

    def compute_WilliamsFractal(self, n):
        periods = tuple(range(-n, 0)) + tuple(range(1, n + 1))

        bear_fractal = pd.Series(np.logical_and.reduce([
            self.price_data['High'] > self.price_data['High'].shift(period) for period in periods
        ]), index=self.price_data.index)

        bull_fractal = pd.Series(np.logical_and.reduce([
            self.price_data['Low'] < self.price_data['Low'].shift(period) for period in periods
        ]), index=self.price_data.index)

        self.price_data[f'BearFractal{n}'] = bear_fractal
        self.price_data[f'BullFractal{n}'] = bull_fractal

    @abc.abstractmethod
    def get_hyperparameter_space(self) -> Dict[str, float]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_strategy_hyperparameters(self, values):
        raise NotImplementedError

    @abc.abstractmethod
    def get_platform_hyperparameters(self):
        raise NotImplementedError

    @abc.abstractmethod
    def set_platform_hyperparameters(self, values):
        raise NotImplementedError

    @abc.abstractmethod
    def compute_indicators(self):
        raise NotImplementedError

    @abc.abstractmethod
    def compute_indicators(self):
        raise NotImplementedError

    @abc.abstractmethod
    def place_trade(self, t):
        return None, False

    @abc.abstractmethod
    def end_trade(self, t, data: Trade) -> Tuple[bool, float]:
        return False, 0

    def test_strategy(self):
        # 100% initial balance
        balance = 1000
        trade_balance = balance / 100

        # Define order info
        total_orders = 0
        successful_orders = 0

        t = self.t_min
        is_active = False
        data = None

        while t < len(self.price_data['Open']):
            if is_active:
                end, growth = self.end_trade(t, data)
                if end:
                    is_active = False
                    successful_orders += growth > 0
                    balance = (balance - trade_balance) + trade_balance * (growth + 1) * (1 - self.fee.get_value())
            # Place new orders
            if not is_active:
                trade_data, is_trade = self.place_trade(t)

            if is_trade:
                is_active = True
                is_trade = False
                total_orders += 1
                data = trade_data
            t += 1

        # return statistics
        if total_orders == 0:
            win_ratio = 0
        else:
            win_ratio = (successful_orders / total_orders * 100)
        trading_time = (len(self.price_data['Open']) / 60 / 24 * binsizes[timeframe])
        return total_orders, win_ratio, trading_time, balance - 1000
