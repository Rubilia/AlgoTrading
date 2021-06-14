import pandas as pd
import numpy as np
from binance.client import Client

from utils import *

# client = Client(api_key, secret_key, testnet=True)

price_data = pd.read_csv(f'binance\\{symbol}_{basecoin}--{timeframe}.csv')


def wilFractal(df, f_range):
    periods = tuple(range(-f_range, 0)) + tuple(range(1, f_range + 1))

    bear_fractal = pd.Series(np.logical_and.reduce([
        df['High'] > df['High'].shift(period) for period in periods
    ]), index=df.index)

    bull_fractal = pd.Series(np.logical_and.reduce([
        df['Low'] < df['Low'].shift(period) for period in periods
    ]), index=df.index)

    return bear_fractal, bull_fractal


# price_data['MA200'] = price_data['Close'].rolling(window=200).mean()
# Calculate EMA
price_data['EMA200'] = pd.Series.ewm(price_data['Close'], span=200).mean()
# Calculate Williams fractal
bear_fractal, bull_fractal = wilFractal(price_data, 4)
price_data['Bear_fractal'] = bear_fractal
price_data['Bull_fractal'] = bull_fractal

# price_data: pd.DataFrame = price_data.iloc[200:]
# price_data.reset_index(drop=True)

# Backtesting strategy


def find_latest_top_fractal(fractals, t, Close_data, Open_data, EMA):
    p = t - 2
    while p > 0 and Close_data.get(p) >= EMA.get(p) and Open_data.get(p) >= EMA.get(p):
        if fractals.get(p):
            return p
        p -= 1
    return -1


def find_latest_bottom_fractal(fractals, t, Close_data, Open_data, EMA):
    p = t - 2
    while p > 0 and Close_data.get(p) <= EMA.get(p) and Open_data.get(p) <= EMA.get(p):
        if fractals.get(p):
            return p
        p -= 1
    return -1

# 100% initial balance
balance = 100

# Define order info
total_orders = 0
successful_orders = 0

t = 204
is_active = False
stop_loss = 0
take_profit = 0
entry = 0
t_entry = 0
order_type = 'long'

val = price_data['Open'].get(204)


while t < len(price_data['Open']):
    if is_active:
        # Check if order is completed
        if order_type == 'long' and price_data['Low'].get(t) <= stop_loss:
            # Long order failed
            is_active = False
            total_orders += 1
            new_balance = stop_loss / entry * balance * (1 - fee)
            print(f'Failed Long trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {(new_balance - balance) / balance * 100}%, Total growth: {new_balance - 100}%')
            balance = new_balance
        elif order_type == 'long' and price_data['High'].get(t) >= take_profit:
            # Long trade succeeded
            total_orders += 1
            successful_orders += 1
            is_active = False
            new_balance = take_profit / entry * balance * (1 - fee)
            print(
                f'Successful Long trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {(new_balance - balance) / balance * 100}%, Total growth: {new_balance - 100}%')
            balance = new_balance
        elif order_type == 'short' and price_data['Low'].get(t) <= take_profit:
            # Short trade succeeded
            total_orders += 1
            successful_orders += 1
            is_active = False
            new_balance = entry / take_profit * balance * (1 - fee)
            print(
                f'Successful Short trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {(new_balance - balance) / balance * 100}%, Total growth: {new_balance - 100}%')
            balance = new_balance
        elif order_type == 'short' and price_data['Low'].get(t) >= stop_loss:
            # Short trade failed
            total_orders += 1
            is_active = False
            new_balance = entry / stop_loss * balance * (1 - fee)
            print(
                f'Failed Short trade: Date: {price_data["Date"].get(t_entry)} Entry: {entry}, Stop: {stop_loss}, TakeProfit: {take_profit}, growth: {(new_balance - balance) / balance * 100}%, Total growth: {new_balance - 100}%')
            balance = new_balance

    # Place new orders
    if price_data['Open'].get(t) >= price_data['EMA200'].get(t) and price_data['Close'].get(t) >= price_data['EMA200'].get(t) and not is_active:
        # Place long
        top_fractal = find_latest_top_fractal(price_data['Bear_fractal'], t, price_data['Close'], price_data['Open'], price_data['EMA200'])
        if top_fractal == -1 or price_data['Close'].get(t) < price_data['High'].get(top_fractal):
            t += 1
            continue

        # Don`t place a trade if it is too volatile
        if 1 - (price_data['Low'].get(t) / stop_multiplier) / price_data['Close'].get(t) >= order_risk_limiter:
            t += 1
            continue


        is_active = True
        t_entry = t
        entry = price_data['Close'].get(t)
        stop_loss = price_data['Low'].get(t) / stop_multiplier
        take_profit = price_data['Close'].get(t) + profit_multiplier * (price_data['Close'].get(t) - price_data['Low'].get(t))
        order_type = 'long'
        t += 1
        continue
    elif price_data['Open'].get(t) <= price_data['EMA200'].get(t) and price_data['Close'].get(t) <= price_data['EMA200'].get(t) and not is_active:
        # Place short
        bottom_fractal = find_latest_bottom_fractal(price_data['Bull_fractal'], t, price_data['Close'], price_data['Open'], price_data['EMA200'])
        if bottom_fractal == -1 or price_data['Close'].get(t) > price_data['Low'].get(bottom_fractal):
            t += 1
            continue

        # Don`t place a trade if it is too volatile
        if 1 - price_data['Close'].get(t) / (price_data['High'].get(t) * stop_multiplier) >= order_risk_limiter:
            t += 1
            continue

        is_active = True
        t_entry = t
        entry = price_data['Close'].get(t)
        stop_loss = price_data['High'].get(t) * stop_multiplier
        take_profit = price_data['Close'].get(t) + profit_multiplier * (price_data['Close'].get(t) - price_data['High'].get(t))
        order_type = 'short'
        t += 1
        continue
    else:
        t += 1


# Print statistics
print(f'Total orders: {total_orders}')
print(f'Win ratio: %.2f' % (successful_orders / total_orders * 100) + '%')
print(f'Time:  %.3f days' % (len(price_data['Open']) / 60 / 24 * binsizes[timeframe]))
print(f'Total growth: {balance - 100}%')