
import streamlit as st
import pandas as pd
import yfinance as yf
import time

st.set_page_config(page_title="StockSavant", page_icon="📈", layout="wide")

st.title("📈 StockSavant")
st.markdown("**Beat the Market with Predictive Precision**")

tab1, tab2 = st.tabs(["🔍 Auto Scan (S&P 500)", "📂 Custom Scan (Upload or Manual)"])

def load_sp500_tickers():
    import requests
    from bs4 import BeautifulSoup
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    tickers = [row.find_all('td')[0].text.strip() for row in table.find_all('tr')[1:]]
    return tickers

def score_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="6mo")

        pe = info.get('trailingPE', None)
        roe = info.get('returnOnEquity', None)
        eps_growth = info.get('earningsQuarterlyGrowth', None)
        debt_to_equity = info.get('debtToEquity', None)
        fcf_yield = info.get('freeCashflow', None) / info.get('marketCap', 1) * 100 if info.get('freeCashflow') else None

        score = 0
        if pe is not None:
            score += 10 if pe < 15 else 5 if pe <= 25 else 0
        if roe is not None:
            roe *= 100
            score += 10 if roe > 20 else 5 if roe >= 10 else 0
        if eps_growth is not None:
            eps_growth *= 100
            score += 10 if eps_growth > 20 else 5 if eps_growth >= 5 else 0
        if debt_to_equity is not None:
            score += 10 if debt_to_equity < 0.5 else 5 if debt_to_equity <= 1 else 0
        if fcf_yield is not None:
            score += 10 if fcf_yield > 5 else 5 if fcf_yield >= 2 else 0

        price = hist['Close'].iloc[-1]
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        score += 10 if price > ma50 and price > ma200 else 5 if price > ma50 or price > ma200 else 0

        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean().iloc[-1]
        avg_loss = loss.rolling(14).mean().iloc[-1]
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        score += 10 if 40 <= rsi <= 60 else 5 if 30 <= rsi < 70 else 0

        avg_vol = hist['Volume'].rolling(20).mean().iloc[-2]
        today_vol = hist['Volume'].iloc[-1]
        score += 10 if today_vol > avg_vol * 1.1 else 5 if today_vol >= avg_vol else 0

        return {
            'Ticker': ticker,
            'Score': score,
            'P/E': pe,
            'ROE (%)': roe,
            'EPS Growth (%)': eps_growth,
            'Debt/Equity': debt_to_equity,
            'FCF Yield (%)': fcf_yield,
            'RSI': rsi,
        }
    except Exception as e:
        return {'Ticker': ticker, 'Error': str(e)}

def run_scoring(tickers):
    results = []
    for i, t in enumerate(tickers):
        with st.spinner(f"Processing {t} ({i+1}/{len(tickers)})..."):
            results.append(score_stock(t))
    df = pd.DataFrame(results)
    df = df[df['Score'].notna()].sort_values(by='Score', ascending=False)
    return df

with tab1:
    if st.button("Run Auto Scan"):
        sp500 = load_sp500_tickers()
        df = run_scoring(sp500[:50])
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False), "stocksavant_top_scores.csv")

with tab2:
    upload = st.file_uploader("Upload a CSV of tickers (1 column, no header)", type="csv")
    manual_input = st.text_area("Or enter tickers separated by commas (e.g., AAPL,MSFT,NVDA)")
    tickers = []

    if upload:
        tickers = pd.read_csv(upload, header=None)[0].tolist()
    elif manual_input:
        tickers = [x.strip().upper() for x in manual_input.split(',') if x.strip()]

    if tickers:
        df = run_scoring(tickers)
        st.dataframe(df)
        st.download_button("Download Results", df.to_csv(index=False), "stocksavant_custom_scores.csv")
