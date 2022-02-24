from boto3 import resource
from dataclasses import dataclass
from decimal import Decimal
from dotenv import load_dotenv
from os import getenv
from s3_helper import CSVStream
from typing import Any

from datetime import datetime
from statsmodels.tsa.arima.model import ARIMA

load_dotenv()

BUY = "buy"
SELL = "sell"

BUCKET = getenv("BUCKET_NAME")

XBT_2018_KEY = "xbt.usd.2018"
XBT_2020_KEY = "xbt.usd.2020"

ETH_2018_KEY = "eth.usd.2018"
ETH_2020_KEY = "eth.usd.2020"

S3 = resource("s3")
SELECT_ALL_QUERY = 'SELECT * FROM S3Object'

# Example s3 SELECT Query to Filter Data Stream
#
# The where clause fields refer to the timestamp column in the csv row.
# To filter the month of February, for example, (start: 1517443200, end: 1519862400) 2018
#                                               (Feb-01 00:00:00  , Mar-01 00:00:00) 2018
#
# QUERY = '''\
#     SELECT *
#     FROM S3Object s
#     WHERE CAST(s._4 AS DECIMAL) >= 1514764800
#       AND CAST(s._4 AS DECIMAL) < 1514764802
# '''

STREAM = CSVStream(
    'select',
    S3.meta.client,
    key=XBT_2018_KEY,
    bucket=BUCKET,
    expression=SELECT_ALL_QUERY,
)

@dataclass
class Trade:
    trade_type: str # BUY | SELL
    base: str
    volume: Decimal

def train(data, current):
    model = ARIMA(data, order=(1, 1, 2))
    model_fit = model.fit()
    predict = model_fit.predict(len(data), len(data))
    return predict

def algorithm(csv_row: str, context: dict[str, Any],):
    """ Trading Algorithm

    Add your logic to this function. This function will simulate a streaming
    interface with exchange trade data. This function will be called for each
    data row received from the stream.

    The context object will persist between iterations of your algorithm.

    Args:
        csv_row (str): one exchange trade (format: "exchange pair", "price", "volume", "timestamp")
        context (dict[str, Any]): a context that will survive each iteration of the algorithm

    Generator:
        response (dict): "Fill"-type object with information for the current and unfilled trades
    
    Yield (None | Trade | [Trade]): a trade order/s; None indicates no trade action
    """
    # algorithm logic...
    
    row = csv_row.split(',')
    if len(row) != 4:
        pass
    exc = row[0].split("-")[2]
    if context[exc]:
        val = context[exc]
        val.append(row[1])
        context[exc] = val
    else:
        context[exc] = []
    mode = "NEUTRAL"
    currency = exc
    x = context[exc]
    if len(x) < 100:
        mode = "NEUTRAL"
    else:
        result = train(np.array(context[exc]),row[1])
        if result[0] < float(row(1)):
            mode = "BUY"
        else:
            mode = "SELL"
    response = yield Trade(BUY, 'xbt', Decimal(1))

    # algorithm clean-up/error handling...

if __name__ == '__main__':
    # example to stream data
    context = {'xbt': [], 'eth': []}
    for row in STREAM.iter_records():
        algorithm(row,context)
    
# Example Interaction
#
# Given the following incoming trades, each line represents one csv row:
#   (1) okfq-xbt-usd,14682.26,2,1514765115
#   (2) okf1-xbt-usd,13793.65,2,1514765115
#   (3) stmp-xbt-usd,13789.01,0.00152381,1514765115
#
# When you receive trade 1 through to your algorithm, if you decide to make
# a BUY trade for 3 xbt, the order will start to fill in the following steps
#   [1] 1 unit xbt from trade 1 (%50 available volume from the trade data)
#   [2] 1 unit xbt from trade 2
#   [3] receiving trade 3, you decide to put in another BUY trade:
#       i. Trade will be rejected, because we have not finished filling your 
#          previous trade
#       ii. The fill object will contain additional fields with error data
#           a. "error_code", which will be "rejected"; and
#           b. "error_msg", description why the trade was rejected.
#
# Responses during these iterations:
#   [1] success resulting in:
#       {
#           "price": 14682.26,
#           "volume": 1,
#           "unfilled": {"xbt": 2, "eth": 0 }
#       }
#   [2]
#       {
#           "price": 13793.65,
#           "volume": 1,
#           "unfilled": {"xbt": 1, "eth": 0 }
#       }
#   [3]
#       {
#           "price": 13789.01,
#           "volume": 0.000761905,
#           "error_code": "rejected",
#           "error_msg": "filling trade in progress",
#           "unfilled": {"xbt": 0.999238095, "eth": 0 }
#       }
#
# In step 3, the new trade order that you submitted is rejected; however,
# we will continue to fill that order that was already in progress, so
# the price and volume are CONFIRMED in that payload.
