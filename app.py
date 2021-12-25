from flask import Flask, render_template, request
from stocks import stocks
from patterns import patterns
from datetime import date
import json
import plotly
import plotly.express as px
import plotly.graph_objs as go
import yfinance as yf
import yahoo_fin.stock_info as si
import math
import os, csv
import pandas as pd
import talib
from plotly.subplots import make_subplots



app = Flask(__name__,static_url_path="/static")

@app.route('/dash/')
def dashboard():
    stock = request.args.get('stock',None)
    print(stock)
    if stock is not None:
        return render_template('dashboard.html',list_stocks=stocks,selected=stock)

    return render_template('dashboard.html',list_stocks=stocks,selected=None)

@app.route('/dash/callback/<endpoint>')
def cb(endpoint):   
    if endpoint == "getStock":
        return gm(request.args.get('data'),request.args.get('period'),request.args.get('interval'))
    elif endpoint == "getInfo":
        stock = request.args.get('data')
        st = yf.Ticker(stock)
        st = st.info
        if st['marketCap'] is not None:
            st['marketCap']= millify(st['marketCap'])
        for key in st:
            if st[key] is None:
                st[key]="-"

        return json.dumps(st)
    else:
        return "Bad endpoint", 400

def gm(stock,period, interval):
    st = yf.Ticker(stock)
  
    df = st.history(period=(period), interval=interval)
    df=df.reset_index()
    df.columns = ['Date-Time']+list(df.columns[1:])

    #tambah ma
    df['10MA'] = df['Close'].rolling(10).mean()
    df['50MA'] = df['Close'].rolling(50).mean()

    fig = make_subplots(rows = 2, cols = 1, shared_xaxes = True, subplot_titles = ('Price', 'Volume'), vertical_spacing = 0.1, row_width = [0.2, 0.7])

    #candlestick
    fig.add_trace(go.Candlestick(x=df['Date-Time'],open = df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name = 'market data',showlegend=False),row = 1, col = 1)

    #ma
    fig.add_trace(go.Scatter(x=df['Date-Time'], y=df['10MA'], mode='lines', name='10MA',line=dict(color='blue', width=1)),row=1,col=1)
    fig.add_trace(go.Scatter(x=df['Date-Time'], y=df['50MA'], mode='lines', name='50MA',line=dict(color='orange', width=1)),row=1,col=1)

    #volume
    fig.add_trace(go.Bar(x = df['Date-Time'], y = df['Volume'], name="Volume",showlegend=False), row = 2, col = 1)
    
    #update
    fig.update_layout(legend=dict(orientation="h",
                              yanchor="bottom",y=1.02,
                              xanchor="right",x=1))
    fig.update_layout(template='plotly_white')
    fig.update_xaxes(rangeslider_visible=False)


    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

millnames = ['',' Thousand',' Million',' Billion',' Trillion']
def millify(n):
    n = float(n)
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])



@app.route("/screener")
def screener():
    pattern = request.args.get('pattern',None)
    stocks ={}
    with open('dataset/company.csv') as f:
        csv_reader = csv.reader(f)
        header = next(csv_reader)
        if header != None:
            for row in csv_reader:
                stocks[row[2]]={'company':row[3]}

    if pattern:
        datafiles = os.listdir('dataset/daily')
        for filename in datafiles:
            df=pd.read_csv('dataset/daily/{}'.format(filename))
            pattern_function = getattr(talib, pattern)
            symbol = filename.split('.')[0]

            try:
                result = pattern_function(df['Open'], df['High'],df['Low'],df['Close'])
                #print(result)
                last = result.tail(1).values[0]
                #print(last)
                if last>0:
                    stocks[symbol][pattern]='bullish'
                elif last<0:
                    stocks[symbol][pattern]='bearish'
                else:
                    stocks[symbol][pattern]=None
                    
            except:
                pass
    newst={}
    for k,v in stocks.items():
        if len(stocks[k])==2 and v[pattern] is not None:
            newst.update({k:v})
    
    return render_template('screener.html',patterns=patterns,stocks=newst,current_pattern=pattern)

@app.route('/screener/snapshot')
def snapshot():
    today = date.today()
    today=today.strftime("%Y-%m-%d")

    with open('dataset/company.csv') as f:
        companies = f.read().splitlines()
        for company in companies[1:]:
            symbol =company.split(',')[2]
            df = yf.download(symbol+".JK", start="2021-01-01",end=today)
            df.to_csv('dataset/daily/{}.csv'.format(symbol))
    return{
        'code':'success'
    }


@app.route('/')
def static_file():
    return render_template('index.html')

@app.route('/pattern')
def pat():
    return render_template('pattern.html')

@app.route('/stockinfo')
def stockinfo():
    return render_template('stock.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')