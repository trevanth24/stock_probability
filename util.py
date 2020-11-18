import requests

import numpy as np
import pandas as pd


def get_option_data(ticker: str, expiration_date: str) -> (float, pd.DataFrame):
    """
    :param ticker: stock ticker
    :param expiration_date: option chain expiration date (YYYY-MM-DD)
    :return: tuple containing stock price and data frame with option chain
    """
    stock_price_response = requests.get(
        'https://sandbox.tradier.com/v1/markets/quotes',
        params={
            'symbols': ticker,
        },
        headers={
            'Authorization': 'Bearer RudqnB0bzRxQVucDkn3dKTx1Ka34',
            'Accept': 'application/json'
        }
    )
    try:
        stock_price = stock_price_response.json()['quotes']['quote']['last']
    except KeyError:
        raise ValueError(f"Ticker {ticker} is not valid")

    option_price_response = requests.get(
        'https://sandbox.tradier.com/v1/markets/options/chains',
        params={
            'symbol': ticker,
            'expiration': expiration_date,
        },
        headers={
            'Authorization': 'Bearer RudqnB0bzRxQVucDkn3dKTx1Ka34',
            'Accept': 'application/json'
        }
    )
    try:
        options = option_price_response.json()['options']['option']
    except TypeError:
        raise ValueError("Invalid expiration date")

    data = []
    for i in range(0, len(options), 2):
        strike_price = options[i]['strike']
        option_type = options[i]['option_type']
        if option_type == 'call':
            call_price = options[i]['last']
            put_price = options[i + 1]['last']
        else:
            call_price = options[i + 1]['last']
            put_price = options[i]['last']
        data.append([strike_price, call_price, put_price])
    df = pd.DataFrame(data, columns=['strike_price', 'call_price', 'put_price'])
    return stock_price, df


def preprocces_data(price: float, df: pd.DataFrame) -> pd.DataFrame:
    """
    :param price: spot price for ticker
    :param df: raw option chain
    :return: dataframe for use with model
    """
    distance_from_spot = 0.125
    lower_limit = price * (1 - distance_from_spot)
    upper_limit = price * (1 + distance_from_spot)
    df = df[df['strike_price'].between(lower_limit, upper_limit)]
    dif = df.iloc[1]['strike_price'] - df.iloc[0]['strike_price']
    df.loc[df['strike_price'] <= price - dif / 2, 'call_price'] = np.nan
    df.loc[df['strike_price'] > price + dif / 2, 'put_price'] = np.nan
    # If either the lower or upper dfs have an odd number of rows, remove the outermost
    # element so that the model can build spreads with every other row.
    if df[df['call_price'] > 0].shape[0] % 2 == 0:
        df = df[:-1]
    if df[df['put_price'] > 0].shape[0] % 2 == 0:
        df = df[1:]
    # Return every other row
    return df[::2]
