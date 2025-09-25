# dailyreport.py
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import sqlite3

def calculate_technical_analysis(ticker, asset_type):
    if asset_type not in ["국내주식", "해외주식", "가상자산"]:
        return {"assetId": ticker, "macd_signal": "N/A", "rsi": 0, "rsi_signal": "N/A"}
    try:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        prices = fdr.DataReader(ticker + ("/KRW" if asset_type in ["가상자산"] else ""), start_date)["Close"]
        
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_signal = "Buy" if macd.iloc[-1] > signal_line.iloc[-1] else "Sell" if macd.iloc[-1] < signal_line.iloc[-1] else "Neutral"

        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"

        return {"assetId": ticker, "macd_signal": macd_signal, "rsi": rsi, "rsi_signal": rsi_signal}
    except Exception as e:
        print(f"Error in technical analysis for {ticker}: {e}")
        return {"assetId": ticker, "macd_signal": "N/A", "rsi": 0, "rsi_signal": "N/A"}

def get_news_summary(ticker, asset_type, num_news=3):
    if asset_type == "예적금":
        return []
    
    headers = {
        "X-Naver-Client-Id": "YOUR_CLIENT_ID_HERE",  # 실제 Naver Client ID 입력
        "X-Naver-Client-Secret": "YOUR_CLIENT_SECRET_HERE"  # 실제 Naver Client Secret 입력
    }
    url = "https://openapi.naver.com/v1/search/news.json"
    params = {"query": ticker, "sort": "date", "display": num_news}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return [{"title": "뉴스 없음", "summary": "해당 종목 관련 최신 뉴스가 없습니다."}]
        
        news_list = []
        for item in items[:num_news]:
            news_url = item["link"]
            try:
                news_response = requests.get(news_url, timeout=5)
                soup = BeautifulSoup(news_response.text, "html.parser")
                article = soup.select_one("article") or soup.select_one(".article")
                content = article.get_text(strip=True) if article else item["description"]
                content = re.sub(r"\s+", " ", content)[:500]
            except Exception:
                content = item["description"]
            
            summary = content[:50] + "..." if len(content) > 50 else content
            news_list.append({"title": item["title"], "summary": summary})
        
        return news_list
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return [{"title": "뉴스 조회 실패", "summary": "API 호출 중 오류 발생"}]

def get_industry_trends(sector, num_trends=2):
    sectors = {
        "IT": ["AAPL", "MSFT"],
        "Financial": ["JPM", "GS"],
        "Fixed Income": ["SAVING1"],
        "Crypto": ["BTC", "ETH"],
        "Currency": ["USD"]
    }
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    trends = {}
    for s, tickers in sectors.items():
        returns = []
        for ticker in tickers:
            if s == "Fixed Income":
                returns.append(0.0)
            else:
                try:
                    prices = fdr.DataReader(ticker + ("/KRW" if s in ["Crypto", "Currency"] else ""), start_date)["Close"]
                    returns.append(prices.pct_change().mean())
                except Exception:
                    returns.append(0.0)
        trends[s] = np.mean(returns) if returns else 0.0
    
    top_sectors = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:num_trends]
    related_trends = [s for s, _ in top_sectors if s == sector] + [s for s, _ in top_sectors if s != sector][:1]
    return {s: f"수익률 {trends[s]*100:.1f}%" for s in related_trends}

def daily_report(user_id):
    # DB 조회
    conn = sqlite3.connect("portfolio.db")
    portfolio = pd.read_sql_query(
        "SELECT ticker, quantity, purchase_price FROM ASSET_INFO_TB WHERE user_id = ?",
        conn, params=(user_id,)
    )
    stock_info = pd.read_sql_query(
        "SELECT ticker, sector, asset_type FROM stock_info", conn
    )
    conn.close()

    if portfolio.empty:
        return {"status": "error", "message": "보유 종목 없음"}

    # portfolio와 stock_info 병합
    portfolio = portfolio.merge(stock_info, on="ticker")

    # 현재 가격 계산
    portfolio["current_price"] = portfolio.apply(
        lambda x: fdr.DataReader(
            x["ticker"] + ("/KRW" if x["asset_type"] in ["가상자산"] else ""),
            datetime.now().strftime("%Y-%m-%d")
        )["Close"].iloc[-1]
        if x["asset_type"] in ["국내주식", "해외주식", "가상자산"]
        else x["purchase_price"],
        axis=1
    )
    portfolio["return"] = (portfolio["current_price"] - portfolio["purchase_price"]) / portfolio["purchase_price"]

    reports = []
    for _, row in portfolio.iterrows():
        ticker = row["ticker"]
        asset_type = row["asset_type"]
        sector = row["sector"]

        # 1. 기술적 지표 (Diagnosis)
        technicals = calculate_technical_analysis(ticker, asset_type)

        # 2. 성과 및 설명
        weight = row["quantity"] * row["current_price"] / (portfolio["quantity"] * portfolio["current_price"]).sum()
        item_return = row["return"] * 100
        explanation = f"수익률: {item_return:.1f}%, 비중: {weight*100:.1f}%. {'매수 추천' if technicals['macd_signal'] == 'Buy' else '매도 고려'} (RSI: {technicals['rsi_signal']})."

        # 3. 뉴스 2~3개 (Feedback)
        news = get_news_summary(ticker, asset_type, num_news=3)

        # 4. 산업 동향 1~2개 (Feedback)
        trends = get_industry_trends(sector, num_trends=2)

        reports.append({
            "assetId": ticker,
            "technicals": technicals,  # Diagnosis
            "performance": {"return": item_return, "weight": weight},
            "explanation": explanation,
            "news": news,  # Feedback
            "industryTrends": trends,  # Feedback
            "riskLevel": "High" if item_return > 20 else "Medium" if item_return > 10 else "Low"
        })

    return {
        "status": "success",
        "message": "일일 리포트 생성 성공",
        "data": {"reports": reports, "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")}
    }