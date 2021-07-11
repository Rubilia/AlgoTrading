import json
import os

import pandas as pd
import mplfinance as mpf
import numpy as np
from utils import *

data = json.load(open(os.path.join('binance', f'{symbol}_{basecoin}-{timeframe}.json')))
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
df['EMA50'] = pd.Series.ewm(df['Close'], span=50).mean()


def compute_Avg_True_Range(n, price_data, name='ATR', use_n=True):
    high_low = price_data['High'] - price_data['Low']
    high_close = np.abs(price_data['High'] - price_data['Close'].shift())
    low_close = np.abs(price_data['Low'] - price_data['Close'].shift())

    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)

    if use_n:
        price_data[f'{name}{n}'] = true_range.rolling(n).sum() / n
    else:
        price_data[f'{name}'] = true_range.rolling(n).sum() / n


compute_Avg_True_Range(14, df, use_n=False)

df = df.tail(1000)

apds = [mpf.make_addplot(df['EMA200']),
        mpf.make_addplot(df['EMA50']),
        mpf.make_addplot((df['ATR']), panel=1, color='b')
        ]

mpf.plot(df, type='candle', style='binance', addplot=apds)
input()
