# ultimate_otc_signal_app_v2_final.py
import streamlit as st
import pandas as pd
import talib
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide")
st.title("Ultimate OTC Signal App v2 – Multi-Asset Live Simulation")

# Sidebar: Upload multiple CSVs
st.sidebar.header("Upload Candle Data for Assets")
uploaded_files = st.sidebar.file_uploader(
    "Upload CSV(s) (timestamp, open, high, low, close)", type=["csv"], accept_multiple_files=True
)

# Strategy Parameters
st.sidebar.header("Strategy Parameters")
ema_short = st.sidebar.number_input("EMA Short Period", value=20)
ema_long = st.sidebar.number_input("EMA Long Period", value=50)
rsi_period = st.sidebar.number_input("RSI Period", value=14)
bb_period = st.sidebar.number_input("Bollinger Band Period", value=20)
bb_std = st.sidebar.number_input("Bollinger Band Std Dev", value=2.0)
refresh_interval = st.sidebar.number_input("Simulation Refresh Interval (seconds)", value=2, min_value=1)

if uploaded_files:
    st.info("Starting Live Simulation...")
    
    # Load all assets
    assets_data = {}
    for file in uploaded_files:
        asset_name = file.name.split('.')[0]
        df = pd.read_csv(file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        assets_data[asset_name] = df

    signal_history = []

    # Live simulation loop
    max_len = max([len(df) for df in assets_data.values()])
    for i in range(1, max_len):
        st.write(f"--- Simulation Step {i} ---")
        for asset, df in assets_data.items():
            if i >= len(df):
                continue
            sub_df = df.iloc[:i+1].copy()
            
            # Indicators
            sub_df['EMA_short'] = talib.EMA(sub_df['close'], timeperiod=ema_short)
            sub_df['EMA_long'] = talib.EMA(sub_df['close'], timeperiod=ema_long)
            sub_df['RSI'] = talib.RSI(sub_df['close'], timeperiod=rsi_period)
            sub_df['upperBB'], sub_df['middleBB'], sub_df['lowerBB'] = talib.BBANDS(
                sub_df['close'], timeperiod=bb_period, nbdevup=bb_std, nbdevdn=bb_std
            )
            
            # Latest candle
            idx = len(sub_df) - 1
            trend_up = sub_df['EMA_short'][idx] > sub_df['EMA_long'][idx]
            trend_down = sub_df['EMA_short'][idx] < sub_df['EMA_long'][idx]
            
            call_conditions = 0
            put_conditions = 0
            if trend_up: call_conditions += 1
            if trend_down: put_conditions += 1
            if sub_df['RSI'][idx] > 50: call_conditions += 1
            if sub_df['RSI'][idx] < 50: put_conditions += 1
            if sub_df['close'][idx] < sub_df['lowerBB'][idx]: call_conditions += 1
            if sub_df['close'][idx] > sub_df['upperBB'][idx]: put_conditions += 1
            prev_close = sub_df['close'][idx-1]
            curr_open = sub_df['open'][idx]
            curr_close = sub_df['close'][idx]
            if trend_up and curr_close > curr_open and curr_close > prev_close: call_conditions += 1
            if trend_down and curr_close < curr_open and curr_close < prev_close: put_conditions += 1
            
            signal = None
            strength = None
            if call_conditions >= 4:
                strength = 'Strong' if call_conditions >= 5 else 'Medium'
                signal = 'CALL'
            elif put_conditions >= 4:
                strength = 'Strong' if put_conditions >= 5 else 'Medium'
                signal = 'PUT'
            
            if signal:
                signal_history.append({
                    'timestamp': sub_df['timestamp'][idx],
                    'asset': asset,
                    'price': sub_df['close'][idx],
                    'signal': signal,
                    'strength': strength
                })
            
            # Plot chart
            fig = go.Figure(data=[go.Candlestick(
                x=sub_df['timestamp'], open=sub_df['open'], high=sub_df['high'],
                low=sub_df['low'], close=sub_df['close'], name='Candles'
            )])
            fig.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df['EMA_short'], mode='lines', name=f'EMA {ema_short}', line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df['EMA_long'], mode='lines', name=f'EMA {ema_long}', line=dict(color='orange')))
            fig.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df['upperBB'], mode='lines', name='Upper BB', line=dict(color='grey', dash='dot')))
            fig.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df['lowerBB'], mode='lines', name='Lower BB', line=dict(color='grey', dash='dot')))
            
            # Signal markers
            for s in signal_history:
                if s['asset'] == asset:
                    color = 'green' if s['signal'] == 'CALL' else 'red'
                    fig.add_trace(go.Scatter(
                        x=[s['timestamp']], y=[s['price']],
                        mode='markers+text',
                        marker=dict(size=12, color=color),
                        text=[s['signal'] + " (" + s['strength'] + ")"],
                        textposition='top center',
                        name=s['signal']
                    ))
            
            fig.update_layout(title=f"{asset} Candle Chart with Signals", xaxis_title="Time", yaxis_title="Price")
            st.plotly_chart(fig, use_container_width=True)
        
        # Signal Table
        st.subheader("Signal History")
        if signal_history:
            signal_df = pd.DataFrame(signal_history)
            st.dataframe(signal_df)
        
        time.sleep(refresh_interval)
    
    # Download CSV
    st.download_button(
        label="Download Full Signals CSV",
        data=pd.DataFrame(signal_history).to_csv(index=False),
        file_name='ultimate_otc_signals_v2_final.csv',
        mime='text/csv'
    )
else:
    st.info("Upload one or more candle CSV files for live simulation.")
