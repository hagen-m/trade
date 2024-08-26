import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import time
import threading

# Initialize exchange
exchange = ccxt.bybit({
    'apiKey': 'GQl63zjnos1O9d1ql9',  # Hardcoded API Key
    'secret': 'qnrBhDs5FkiqfG2E5bLRDkEbI2xEa2DKOOyn'
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

# Load and save configurations
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f)

config = load_config()
current_config = config.get('current', {})

# Streamlit app
st.title('Bybit Trend Following Bot Interface')

# Sidebar for user input
st.sidebar.header('Bot Settings')

symbol = st.sidebar.selectbox('Select Trading Pair', ['ETH/BTC', 'BTC/USDT', 'ETH/USDT'], key='symbol')

# Entry settings
st.sidebar.subheader('Entry Settings')
entry_ma1 = st.sidebar.number_input('Entry MA 1', min_value=1, max_value=100, value=current_config.get('entry_ma1', 10), key='entry_ma1')
entry_ma2 = st.sidebar.number_input('Entry MA 2', min_value=1, max_value=100, value=current_config.get('entry_ma2', 20), key='entry_ma2')
entry_ma3 = st.sidebar.number_input('Entry MA 3', min_value=1, max_value=100, value=current_config.get('entry_ma3', 50), key='entry_ma3')
entry_timeframe = st.sidebar.selectbox('Entry Timeframe', ['1m', '5m', '15m', '30m', '1h', '4h', '1d'], key='entry_timeframe')

# Stop-Loss settings
st.sidebar.subheader('Stop-Loss Settings')
sl_ma1 = st.sidebar.number_input('Stop-Loss MA 1', min_value=1, max_value=100, value=current_config.get('sl_ma1', 5), key='sl_ma1')
sl_ma2 = st.sidebar.number_input('Stop-Loss MA 2', min_value=1, max_value=100, value=current_config.get('sl_ma2', 10), key='sl_ma2')
sl_ma3 = st.sidebar.number_input('Stop-Loss MA 3', min_value=1, max_value=100, value=current_config.get('sl_ma3', 20), key='sl_ma3')
sl_timeframe = st.sidebar.selectbox('Stop-Loss Timeframe', ['1m', '5m', '15m', '30m', '1h', '4h', '1d'], key='sl_timeframe')

# Take-Profit settings
st.sidebar.subheader('Take-Profit Settings')
tp_ma1 = st.sidebar.number_input('Take-Profit MA 1', min_value=1, max_value=100, value=current_config.get('tp_ma1', 10), key='tp_ma1')
tp_ma2 = st.sidebar.number_input('Take-Profit MA 2', min_value=1, max_value=100, value=current_config.get('tp_ma2', 20), key='tp_ma2')
tp_ma3 = st.sidebar.number_input('Take-Profit MA 3', min_value=1, max_value=100, value=current_config.get('tp_ma3', 30), key='tp_ma3')
tp_timeframe = st.sidebar.selectbox('Take-Profit Timeframe', ['1m', '5m', '15m', '30m', '1h', '4h', '1d'], key='tp_timeframe')

# MA crossing settings
ma_cross_type = st.sidebar.radio('MA Crossing Activation', ['Any Two', 'All Three'], key='ma_cross_type')

action = st.sidebar.radio('Select Action', ['Buy', 'Sell'], key='action')

# Order size settings
order_size_percent = st.sidebar.selectbox('Order Size', ['25%', '50%', '75%', '100%'], key='order_size_percent')

# Save configuration
save_config_name = st.sidebar.text_input('Configuration Name')
if st.sidebar.button('Save Configuration'):
    if save_config_name:
        config[save_config_name] = {
            'symbol': symbol,
            'entry_ma1': entry_ma1,
            'entry_ma2': entry_ma2,
            'entry_ma3': entry_ma3,
            'entry_timeframe': entry_timeframe,
            'sl_ma1': sl_ma1,
            'sl_ma2': sl_ma2,
            'sl_ma3': sl_ma3,
            'sl_timeframe': sl_timeframe,
            'tp_ma1': tp_ma1,
            'tp_ma2': tp_ma2,
            'tp_ma3': tp_ma3,
            'tp_timeframe': tp_timeframe,
            'action': action,
            'order_size_percent': order_size_percent,
            'ma_cross_type': ma_cross_type
        }
        save_config(config)
        st.sidebar.success(f'Configuration "{save_config_name}" saved successfully!')

# Fetch OHLCV data
@st.cache_data(ttl=60)
def fetch_ohlcv(symbol, timeframe, limit=1000):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

df_entry = fetch_ohlcv(symbol, entry_timeframe)
df_sl = fetch_ohlcv(symbol, sl_timeframe)
df_tp = fetch_ohlcv(symbol, tp_timeframe)

# Calculate indicators
def calculate_ma(df, periods):
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df

df_entry = calculate_ma(df_entry, [entry_ma1, entry_ma2, entry_ma3])
df_sl = calculate_ma(df_sl, [sl_ma1, sl_ma2, sl_ma3])
df_tp = calculate_ma(df_tp, [tp_ma1, tp_ma2, tp_ma3])

# Plotting
fig = go.Figure()

fig.add_trace(go.Candlestick(x=df_entry['timestamp'],
                             open=df_entry['open'],
                             high=df_entry['high'],
                             low=df_entry['low'],
                             close=df_entry['close'],
                             name='OHLC'))

for period in [entry_ma1, entry_ma2, entry_ma3]:
    fig.add_trace(go.Scatter(x=df_entry['timestamp'], y=df_entry[f'MA{period}'], name=f'Entry MA{period}'))

for period in [sl_ma1, sl_ma2, sl_ma3]:
    fig.add_trace(go.Scatter(x=df_sl['timestamp'], y=df_sl[f'MA{period}'], name=f'SL MA{period}', line=dict(dash='dash')))

for period in [tp_ma1, tp_ma2, tp_ma3]:
    fig.add_trace(go.Scatter(x=df_tp['timestamp'], y=df_tp[f'MA{period}'], name=f'TP MA{period}', line=dict(dash='dot')))

fig.update_layout(title=f'{symbol} Chart',
                  xaxis_title='Date',
                  yaxis_title='Price')

st.plotly_chart(fig)

# Check for MA crossings
def check_ma_crossing(df, ma1, ma2, ma3, cross_type):
    if cross_type == 'Any Two':
        cross_up = ((df[f'MA{ma1}'] > df[f'MA{ma2}']) & (df[f'MA{ma2}'] > df[f'MA{ma3}'])) | \
                   ((df[f'MA{ma1}'] > df[f'MA{ma3}']) & (df[f'MA{ma3}'] > df[f'MA{ma2}'])) | \
                   ((df[f'MA{ma2}'] > df[f'MA{ma1}']) & (df[f'MA{ma1}'] > df[f'MA{ma3}']))
        cross_down = ((df[f'MA{ma1}'] < df[f'MA{ma2}']) & (df[f'MA{ma2}'] < df[f'MA{ma3}'])) | \
                     ((df[f'MA{ma1}'] < df[f'MA{ma3}']) & (df[f'MA{ma3}'] < df[f'MA{ma2}'])) | \
                     ((df[f'MA{ma2}'] < df[f'MA{ma1}']) & (df[f'MA{ma1}'] < df[f'MA{ma3}']))
    else:  # All Three
        cross_up = (df[f'MA{ma1}'] > df[f'MA{ma2}']) & (df[f'MA{ma2}'] > df[f'MA{ma3}'])
        cross_down = (df[f'MA{ma1}'] < df[f'MA{ma2}']) & (df[f'MA{ma2}'] < df[f'MA{ma3}'])
    return cross_up, cross_down

entry_cross_up, entry_cross_down = check_ma_crossing(df_entry, entry_ma1, entry_ma2, entry_ma3, ma_cross_type)
sl_cross_up, sl_cross_down = check_ma_crossing(df_sl, sl_ma1, sl_ma2, sl_ma3, ma_cross_type)
tp_cross_up, tp_cross_down = check_ma_crossing(df_tp, tp_ma1, tp_ma2, tp_ma3, ma_cross_type)

# Bot control
bot_active = st.checkbox('Activate Bot')

# Trading interface
if st.button('Place Order'):
    # Implement order placement logic here
    st.success(f"Order placed: {action} {symbol}")

# PANIC button
if st.button('PANIC - Close All Positions'):
    # Implement logic to close all positions
    st.warning("Closing all positions!")

# Open Positions
st.header('Open Positions')
# Fetch and display open positions here

# Account Balance
st.header('Account Balance')
# Fetch and display account balance here

# Bot logs
st.header('Bot Logs')
log_container = st.empty()

# Calculate order amount
def calculate_order_amount(percent):
    balance = exchange.fetch_balance()
    asset = symbol.split('/')[0]
    asset_balance = balance[asset]['free']
    return asset_balance * float(percent.strip('%')) / 100

# Simulated bot logic
def bot_logic():
    while bot_active:
        current_price = df_entry['close'].iloc[-1]
        
        # Recalculate the order amount based on current balance
        amount = calculate_order_amount(order_size_percent)
        
        # Entry logic
        if action == 'Buy' and entry_cross_up.iloc[-1]:
            log_container.info(f"Buy signal detected at {current_price}. Order amount: {amount} {symbol.split('/')[0]}")
            # Implement order placement logic here
        elif action == 'Sell' and entry_cross_down.iloc[-1]:
            log_container.info(f"Sell signal detected at {current_price}. Order amount: {amount} {symbol.split('/')[0]}")
            # Implement order placement logic here
        
        # Stop-Loss logic
        if action == 'Buy' and sl_cross_down.iloc[-1]:
            log_container.warning(f"Stop-Loss triggered for long position at {current_price}")
            # Implement order closing logic here
        elif action == 'Sell' and sl_cross_up.iloc[-1]:
            log_container.warning(f"Stop-Loss triggered for short position at {current_price}")
            # Implement order closing logic here
        
        # Take-Profit logic
        if action == 'Buy' and tp_cross_up.iloc[-1]:
            log_container.success(f"Take-Profit triggered for long position at {current_price}")
            # Implement order closing logic here
        elif action == 'Sell' and tp_cross_down.iloc[-1]:
            log_container.success(f"Take-Profit triggered for short position at {current_price}")
            # Implement order closing logic here
        
        time.sleep(60)  # Check every minute

# Run bot logic in a separate thread
bot_thread = threading.Thread(target=bot_logic)
bot_thread.start()
