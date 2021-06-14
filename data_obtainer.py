import math
from datetime import datetime

import pandas as pd
from binance.client import Client
from dotenv import load_dotenv

from utils import *

load_dotenv()

binance_client = Client(api_key=api_key, api_secret=secret_key)


def minutes_of_new_data(symbol, kline_size, start_date):
    old = datetime.strptime(start_date, '%d %b %Y')
    new = pd.to_datetime(binance_client.get_klines(symbol=symbol, interval=kline_size)[-1][0], unit='ms')
    return old, new


def get_all_binance(symbol, kline_size, start_date, basecoin='BTC'):
    data_df = pd.DataFrame()

    oldest_point, newest_point = minutes_of_new_data(symbol, kline_size, start_date=start_date)
    delta_min = (newest_point - oldest_point).total_seconds() / 60
    available_data = math.ceil(delta_min / binsizes[kline_size])

    print('Downloading all available %s data for %s. Be patient..!' % (kline_size, symbol))

    klines = binance_client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"),
                                                  newest_point.strftime("%d %b %Y %H:%M:%S"))

    parsedSymbol = symbol[0:-len(basecoin)] + "_" + symbol[-len(basecoin):]
    filename = './binance/%s-%s.json' % (parsedSymbol, kline_size)

    with open(filename, 'w') as f:
        f.write("[")

        print("Total number of candles: {}".format(len(klines)))

        for i, item in enumerate(klines):
            item = item[0:6]
            item[1] = float(item[1])
            item[2] = float(item[2])
            item[3] = float(item[3])
            item[4] = float(item[4])
            item[5] = float(item[5])

            if i != len(klines) - 1:
                f.write("%s," % item)
            else:
                f.write("%s" % item)

        f.write("]")


get_all_binance(symbol + basecoin, timeframe, basecoin=basecoin, start_date=start_date)
