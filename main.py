import apikeys
import mysql.connector
from mysql.connector import Error
import pandas as pd
from binance import Client
import plotly.graph_objects as go
from PIL import Image
from plotly.subplots import make_subplots
from datetime import date, timedelta, datetime

# mysql credentials
PWD = apikeys.PWD
HOST = apikeys.HOST
USER = apikeys.USER
DB = apikeys.DB

api_key = apikeys.api_key
api_secret = apikeys.api_secret
client = Client(api_key, api_secret, testnet=False)

ticker = "BTC-USD"
ticker_printed = ticker.replace("-", "/")
fonts = {"family": "Arial",
        "size": 15
         }

DAYS = 30
SYMBOL = "BTCUSDT"
PERIOD = f"{DAYS} day ago CET"
today = date.today()
back_then = today - timedelta(days=DAYS)

query_string = f"SELECT * FROM signals WHERE date_open >= (DATE(NOW()) - INTERVAL {DAYS} DAY) ORDER BY id DESC"


def read_data_from_binance():
    klines = client.get_historical_klines(SYMBOL, Client.KLINE_INTERVAL_1HOUR, PERIOD)
    df = pd.DataFrame(klines)
    df = df.drop(df.columns[[5, 6, 7, 8, 9, 10, 11]], axis=1)
    df[0] = pd.to_datetime(df[0], unit='ms')
    df.columns = ['date', 'open', 'high', 'low', 'close']
    data = df.copy()
    return data


def read_entries_from_mysql(query):
    try:
        connection = mysql.connector.connect(
            host=HOST,
            database=DB,
            user=USER,
            password=PWD
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("You're connected to database: ", record)

    except Error as e:
        print("Error while connecting to MySQL", e)

    finally:
        if connection.is_connected():
            cursor.execute(query)
            record = cursor.fetchall()
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
            return record


def plot(data, shorts, longs):
    start_date = data['date'].iat[0]
    end_date = data['date'].iat[-1]

    figure = make_subplots(rows=1, cols=1, shared_xaxes=True)
    figure.add_trace(go.Candlestick(x=data["date"],
                                    open=data["open"],
                                    high=data["high"],
                                    low=data["low"],
                                    close=data["close"],
                                    name="BTC price"),
                     row=1, col=1)
    figure.update_layout(autotypenumbers='convert types')

    try:
        datalabs_img = Image.open("dls.png")
    except FileNotFoundError:
        pass
    else:
        figure.add_layout_image(
            dict(
                source=datalabs_img,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.3,
                sizex=0.8,
                sizey=0.8,
                sizing="contain",
                opacity=0.04,
                xanchor='center',
                yanchor='bottom',
                layer="above")
        )
    figure.update_yaxes(title_font=dict(size=10))
    figure.update_annotations(font_size=8, align='left', xanchor="left", xref='paper', x=0, yref='paper', yanchor="top")
    figure.update_layout(height=700, width=1000,
                         title=f"ALL OPENED POSITIONS • {ticker_printed} • 1D • DATALABS.ME • {start_date} - {end_date} GMT",
                         title_x=0.5,
                         xaxis_rangeslider_visible=False,
                         plot_bgcolor="#fff",
                         showlegend=True,
                         title_font=fonts,
                         margin=dict(l=12, r=12, t=65, b=10),
                         yaxis=dict(side="left", tickfont=dict(size=10, color='lightgrey')),
                         yaxis2=dict(side="right", tickfont=dict(size=8, color='lightgrey')),
                         yaxis3=dict(side="right", tickfont=dict(size=8, color='lightgrey')),
                         yaxis4=dict(side="right", tickfont=dict(size=8, color='lightgrey')),
                         xaxis4=dict(tickfont=dict(size=10, color='lightgrey'))
                         )

    if shorts:
        df_s = pd.DataFrame(shorts)
        df_s = df_s.drop(df_s.columns[[1, 3, 5, 6, 7, 8, 9, 10, 11]], axis=1)
        df_s.columns = ['no', 'date', 'price_open']
        df_s['date'] = df_s['date'] - timedelta(hours=1)
        figure.add_trace(go.Scatter(x=df_s['date'],
                                    y=df_s['price_open'],
                                    mode="markers",
                                    name='SELL signal',
                                    marker={'color': 'red', 'size': 12, 'opacity': 0.9, 'symbol': 'triangle-down'}),
                         row=1,
                         col=1)

    if longs:
        df_l = pd.DataFrame(longs)
        df_l = df_l.drop(df_l.columns[[1, 3, 5, 6, 7, 8, 9, 10, 11]], axis=1)
        df_l.columns = ['no', 'date', 'price_open']
        df_l['date'] = df_l['date'] - timedelta(hours=1)
        figure.add_trace(go.Scatter(x=df_l['date'],
                                    y=df_l['price_open'],
                                    mode="markers",
                                    name='BUY signal',
                                    marker={'color': 'green', 'size': 12, 'opacity': 0.9, 'symbol': 'triangle-up'}),
                         row=1, col=1)

    # figure.write_html("pos.html")
    # return figure.to_html()
    figure.show()


def stack_it_all():
    records = read_entries_from_mysql(query_string)
    binance_data = read_data_from_binance()
    short = [r for r in records if r[6].lower() == 'short']
    long = [r for r in records if r[6].lower() == 'long']
    plot(binance_data, short, long)


if __name__ == '__main__':
    stack_it_all()

