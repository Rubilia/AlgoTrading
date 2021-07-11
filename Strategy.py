import random

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
    def __init__(self, df_data, test_balance=1000, risk_per_trade=.1, futures_multiplier=1,
                 max_trade_time=24 * 60, show_trades=False):
        self.show_trades = show_trades
        self.price_data = df_data if isinstance(df_data, list) else [df_data]
        self.indicators = ['MA', 'EMA', 'BearFractal', 'BullFractal', 'Open', 'Low', 'High',
                           'Close', 'ATR', 'AR']
        self.fee = Hyperparameter(0, 0.05, 0.001)
        self.t_min = [0] * len(self.price_data)
        self.test_balance = test_balance
        self.risk_per_trade = risk_per_trade
        self.futures_multiplier = futures_multiplier
        self.max_trade_time = max_trade_time

    def set_data(self, df_data):
        self.price_data = df_data if isinstance(df_data, list) else [df_data]

    def compute_MA(self, n, price_data, name='MA', use_n=True):
        if use_n:
            price_data[f'{name}{n}'] = price_data['Close'].rolling(window=n).mean()
        else:
            price_data[f'{name}'] = price_data['Close'].rolling(window=n).mean()

    def compute_Avg_True_Range(self, n, price_data, name='ATR', use_n=True):
        high_low = price_data['High'] - price_data['Low']
        high_close = np.abs(price_data['High'] - price_data['Close'].shift())
        low_close = np.abs(price_data['Low'] - price_data['Close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)

        if use_n:
            price_data[f'{name}{n}'] = true_range.rolling(n).sum() / n
        else:
            price_data[f'{name}'] = true_range.rolling(n).sum() / n

    def compute_Avg_Range(self, n, price_data, name='AR', use_n=True):
        high_low = price_data['High'] - price_data['Low']
        if use_n:
            price_data[f'{name}{n}'] = high_low.rolling(n).sum() / n
        else:
            price_data[f'{name}'] = high_low.rolling(n).sum() / n

    def compute_EMA(self, n, price_data, name='EMA', use_n=True):
        if use_n:
            price_data[f'{name}{n}'] = pd.Series.ewm(price_data['Close'], span=n).mean()
        else:
            price_data[f'{name}'] = pd.Series.ewm(price_data['Close'], span=n).mean()

    def compute_WilliamsFractal(self, n, price_data, names=['BearFractal', 'BearFractal'], use_n=True):
        periods = tuple(range(-n, 0)) + tuple(range(1, n + 1))

        bear_fractal = pd.Series(np.logical_and.reduce([
            price_data['High'] > price_data['High'].shift(period) for period in periods
        ]), index=price_data.index)

        bull_fractal = pd.Series(np.logical_and.reduce([
            price_data['Low'] < price_data['Low'].shift(period) for period in periods
        ]), index=price_data.index)

        if use_n:
            price_data[f'{names[0]}{n}'] = bear_fractal
            price_data[f'{names[1]}{n}'] = bull_fractal
        else:
            price_data[f'{names[0]}'] = bear_fractal
            price_data[f'{names[1]}'] = bull_fractal

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
    def place_trade(self, t, t_min, price_data):
        return None, False

    @abc.abstractmethod
    def end_trade(self, t, data: Trade, price_data) -> Tuple[bool, float]:
        return False, 0

    def partial_test(self, trials, min_len=60 * 6, max_len=24 * 60):
        total_time = 0
        num_of_trades = 0
        successful_orders = 0
        total_balance_change = 0
        for t in range(trials):
            l = random.randint(int(min_len / binsizes[timeframe]), int(max_len / binsizes[timeframe]))
            data_id = random.randint(0, len(self.price_data) - 1)
            t_0 = random.randint(self.t_min[data_id], self.price_data[data_id].shape[0] - l - 1)
            data = self.price_data[data_id]

            total_orders, positive_trades, trading_time, change_of_balance = self.test_strategy(data, t_0, t_0 + l, self.t_min[data_id])
            total_time += trading_time
            num_of_trades += total_orders
            successful_orders += positive_trades
            total_balance_change += change_of_balance
        return total_time, num_of_trades, successful_orders, total_balance_change / (self.test_balance * self.risk_per_trade)

    def test_strategy(self, price_data, t_min, t_max, real_t_min):
        # 100% initial balance
        balance = self.test_balance
        trade_balance = balance * self.risk_per_trade

        # Define order info
        total_orders = 0
        successful_orders = 0

        t = t_min
        is_active = False
        is_trade = False
        data = None
        order_counter = 0

        while t < min(price_data['Open'].shape[0], t_max):
            if is_active:
                order_counter += 1
                if order_counter > self.max_trade_time and data is not None:
                    end = True
                    growth = price_data['Close'][t] / data.entry - 1
                    order_counter = 0
                else:
                    end, growth = self.end_trade(t, data, price_data)
                if end:
                    is_active = False
                    successful_orders += growth > 0
                    balance = (balance - trade_balance) + trade_balance * (growth * self.futures_multiplier + 1) * (1 - self.fee.get_value())
                    order_counter = 0
            # Place new orders
            if not is_active:
                trade_data, is_trade = self.place_trade(t, real_t_min, price_data)

            if is_trade:
                is_active = True
                is_trade = False
                total_orders += 1
                data = trade_data
                order_counter = 0
            t += 1

        if is_active:
            growth = price_data['Close'][t] / data.entry - 1
            successful_orders += growth > 0
            balance = (balance - trade_balance) + trade_balance * (growth * self.futures_multiplier + 1) * (
                        1 - self.fee.get_value())

        # return statistics
        trading_time = ((t - t_min) * binsizes[timeframe]) # time in minutes
        return total_orders, successful_orders, trading_time, balance - self.test_balance
