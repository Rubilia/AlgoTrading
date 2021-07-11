import json
import pandas as pd
import mplfinance as mpf
import numpy as np
from utils import *


def wilFractal(df, f_range):
    periods = tuple(range(-f_range, 0)) + tuple(range(1, f_range + 1))

    bear_fractal = pd.Series(np.logical_and.reduce([
        df['High'] > df['High'].shift(period) for period in periods
    ]), index=df.index)

    bull_fractal = pd.Series(np.logical_and.reduce([
        df['Low'] < df['Low'].shift(period) for period in periods
    ]), index=df.index)

    return bear_fractal, bull_fractal


data = json.load(open(f'binance\\{symbol}_{basecoin}-{timeframe}.json'))
date = [item[0] for item in data]
open = [item[1] for item in data]
high = [item[2] for item in data]
low = [item[3] for item in data]
close = [item[4] for item in data]


df = pd.DataFrame({'Date': date, 'Open': open, 'High': high, 'Low': low, 'Close': close})
df['Date'] = pd.to_datetime(df['Date'], unit='ms')
df.set_index('Date', inplace=True)

df.to_csv(f'binance\\{symbol}_{basecoin}--{timeframe}.csv')

df['EMA200'] = pd.Series.ewm(df['Close'], span=200).mean()
# df: pd.DataFrame = df.iloc[195]


def configure_fractal(percentB,price):
    signal = []
    previous = False
    for date,value in percentB.iteritems():
        if value and not previous:
            signal.append(price[date])
        else:
            signal.append(np.nan)
        previous = value
    return signal



bear_fractal, bull_fractal = wilFractal(df, 4)

low_signal = configure_fractal(bull_fractal, df['Low'])
high_signal = configure_fractal(bear_fractal, df['High'])


apds = [mpf.make_addplot(df['EMA200']),
         mpf.make_addplot(low_signal, type='scatter', markersize=100, marker='^'),
         mpf.make_addplot(high_signal, type='scatter', markersize=100, marker='v'),
       ]

mpf.plot(df, type='candle', style='binance', addplot=apds)
input()
