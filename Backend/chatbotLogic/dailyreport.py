import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import pymysql
import asset_management
import os
from dotenv import load_dotenv
import chatbotLogic.composition as composition
from flask import jsonify


load_dotenv()

NAVER_DEV_API_KEY = os.getenv("NAVER_DEV_API_KEY")
NAVER_DEV_SECRET_KEY = os.getenv("NAVER_DEV_SECRET_KEY")

def calculate_technical_analysis(ticker, asset_type):
    print(f"[dailyreport] calculate_technical_analysis: ticker={ticker}, asset_type={asset_type}")
    if asset_type not in ["국내주식", "해외주식", "가상자산"]:
        print(f"[dailyreport] Non-technical asset type: {asset_type}, returning default values")
        return {"assetId": ticker, "macd_signal": "N/A", "rsi": 0, "rsi_signal": "N/A"}
    try:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        print(f"[dailyreport] Fetching prices for {ticker} from {start_date}")
        prices = fdr.DataReader(ticker + ("/KRW" if asset_type in ["가상자산"] else ""), start_date)["Close"]
        print(f"[dailyreport] Prices type: {prices.dtype}")
        
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_signal = "매수 시그널" if macd.iloc[-1] > signal_line.iloc[-1] else "매도 시그널" if macd.iloc[-1] < signal_line.iloc[-1] else "중립"

        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        rsi_signal = "과매수" if rsi > 70 else "과매도" if rsi < 30 else "중립"

        result = {"assetId": ticker, "macd_signal": macd_signal, "rsi": rsi, "rsi_signal": rsi_signal}
        print(f"[dailyreport] Technical analysis result: {result}")
        return result
    except Exception as e:
        print(f"[dailyreport] Error in technical analysis for {ticker}: {e}")
        return {"assetId": ticker, "macd_signal": "N/A", "rsi": 0, "rsi_signal": "N/A"}

def get_news_summary(ticker, asset_type, num_news=3):
    print(f"[dailyreport] get_news_summary: ticker={ticker}, asset_type={asset_type}, num_news={num_news}")
    if asset_type == "예적금":
        print(f"[dailyreport] Skipping news for 예적금 asset type")
        return []
    
    headers = {
        "X-Naver-Client-Id": NAVER_DEV_API_KEY,
        "X-Naver-Client-Secret": NAVER_DEV_SECRET_KEY
    }
    url = "https://openapi.naver.com/v1/search/news.json"
    params = {"query": ticker, "sort": "date", "display": num_news}
    
    try:
        print(f"[dailyreport] Fetching news from Naver API for {ticker}")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            print(f"[dailyreport] No news found for {ticker}")
            return [{"title": "뉴스 없음", "summary": "해당 종목 관련 최신 뉴스가 없습니다."}]
        
        news_list = []
        for item in items[:num_news]:
            news_url = item["link"]
            print(f"[dailyreport] Fetching article content from {news_url}")
            try:
                news_response = requests.get(news_url, timeout=5)
                soup = BeautifulSoup(news_response.text, "html.parser")
                article = soup.select_one("article") or soup.select_one(".article")
                content = article.get_text(strip=True) if article else item["description"]
                content = re.sub(r"\s+", " ", content)[:500]
            except Exception as e:
                print(f"[dailyreport] Error fetching article content for {news_url}: {e}")
                content = item["description"]
            
            summary = content[:50] + "..." if len(content) > 50 else content
            news_list.append({"title": item["title"], "summary": summary})
        
        print(f"[dailyreport] News summary result: {news_list}")
        return news_list
    except Exception as e:
        print(f"[dailyreport] Error fetching news for {ticker}: {e}")
        return [{"title": "뉴스 조회 실패", "summary": "API 호출 중 오류 발생"}]

def get_industry_trends(sector, num_trends=2):
    print(f"[dailyreport] get_industry_trends: sector={sector}, num_trends={num_trends}")
    # DB에서 섹터별 티커 정보 조회
    db = asset_management.connect_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT sector, ticker FROM ASSET_INFO_TB")
    rows = cursor.fetchall()
    db.close()
    sector_tickers = {}
    for sector_name, ticker in rows:
        sector_tickers.setdefault(sector_name, []).append(ticker)
    print(f"[dailyreport] sector_tickers: {sector_tickers}")
    
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    trends = {}
    for s, tickers in sector_tickers.items():
        returns = []
        for ticker in tickers:
            if s in ["예적금", "현금"]:
                returns.append(0.0)
            else:
                try:
                    print(f"[dailyreport] Fetching prices for {ticker} in sector {s} from {start_date}")
                    prices = fdr.DataReader(ticker + ("/KRW" if s in ["Crypto", "Currency", "가상자산"] else ""), start_date)["Close"].astype(float)
                    returns.append(prices.pct_change().fillna(0).mean())
                    print(f"[dailyreport] Return for {ticker}: {returns[-1]}")
                except Exception as e:
                    print(f"[dailyreport] Error fetching prices for {ticker}: {e}")
                    returns.append(0.0)
        trends[s] = np.mean(returns) if returns else 0.0
        print(f"[dailyreport] Sector {s} average return: {trends[s]}")
    
    top_sectors = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:num_trends]
    related_trends = [s for s, _ in top_sectors if s == sector] + [s for s, _ in top_sectors if s != sector][:1]
    result = {s: f"수익률 {trends[s]*100:.1f}%" for s in related_trends}
    print(f"[dailyreport] Industry trends result: {result}")
    return result

def daily_report(user_id):
    print(f"[dailyreport] Starting daily_report for user_id: {user_id}")
    try:
        # DB 조회 (MySQL)
        # db = asset_management.connect_mysql()
        # cursor = db.cursor(pymysql.cursors.DictCursor)
        # print("[dailyreport] DB connection successful")
        # cursor.execute("SELECT asset_id, quantity, averagePrice FROM USER_ASSET_LIST_TB WHERE user_id = %s", (user_id,))
        # portfolio_rows = cursor.fetchall()
        # print(f"[dailyreport] portfolio_rows: {portfolio_rows}")
        # cursor.execute("SELECT ticker, sector, assetType FROM ASSET_INFO_TB") #asset_name로 수정?
        # stock_info_rows = cursor.fetchall()
        # print(f"[dailyreport] stock_info_rows: {stock_info_rows}")
        # cursor.close()
        # db.close()
        # print("[dailyreport] DB connection closed")

        # portfolio = pd.DataFrame(portfolio_rows, columns=["asset_id", "ticker", "quantity", "averagePrice"])
        # print(f"[dailyreport] portfolio DataFrame created:\n{portfolio}")
        # portfolio[["quantity", "averagePrice"]] = portfolio[["quantity", "averagePrice"]].astype(float)  # decimal.Decimal to float
        # stock_info = pd.DataFrame(stock_info_rows, columns=["ticker", "sector", "assetType"])
        # print(f"[dailyreport] stock_info DataFrame created:\n{stock_info}")

        # if portfolio.empty:
        #     print("[dailyreport] Portfolio is empty")
        #     return {"status": "error", "message": "보유 종목 없음"}

        # # portfolio와 stock_info 병합
        # portfolio = portfolio.merge(stock_info, on="ticker")
        # print(f"[dailyreport] Merged portfolio DataFrame:\n{portfolio}")

        # DB 조회
        portfolio_result = composition.composition(user_id)
        print(f"[dailyreport] composition 반환 결과: {portfolio_result}")

        portfolio = pd.DataFrame(portfolio_result["data"])
        print(f"[dailyreport] portfolio DataFrame:\n{portfolio}")

        # 현재 가격 계산
        portfolio["currentPrice"] = portfolio.apply(
            lambda x: float(fdr.DataReader(
                x["ticker"] + ("/KRW" if x["assetType"] in ["가상자산"] else ""),
                datetime.now().strftime("%Y-%m-%d")
            )["Close"].iloc[-1])
            if x["assetType"] in ["국내주식", "해외주식", "가상자산"]
            else float(x["averagePrice"]),
            axis=1
        )
        print(f"[dailyreport] currentPrice calculated:\n{portfolio[['ticker', 'currentPrice']]}")
        print(f"[dailyreport] Data types:\n{portfolio.dtypes}")

        # 수익률 계산
        portfolio["return"] = portfolio.apply(
            lambda x: 0 if x["assetType"] in ["예적금", "현금"] else (float(x["currentPrice"]) - float(x["averagePrice"])) / float(x["averagePrice"]),
            axis=1
        )
        print(f"[dailyreport] Return calculated:\n{portfolio[['ticker', 'return']]}")

        reports = []
        for _, row in portfolio.iterrows():
            ticker = row["ticker"]
            assetType = row["assetType"]
            sector = row["sector"]
            print(f"[dailyreport] Processing ticker: {ticker}, assetType: {assetType}, sector: {sector}")

            # 1. 기술적 지표 (Diagnosis)
            technicals = calculate_technical_analysis(ticker, assetType)

            # 2. 성과 및 설명
            weight = float(row["quantity"]) * float(row["currentPrice"]) / (portfolio["quantity"].astype(float) * portfolio["currentPrice"]).sum()
            item_return = row["return"] * 100
            explanation = f"수익률: {item_return:.1f}%, 비중: {weight*100:.1f}%. {'매수 추천' if technicals['macd_signal'] == '매수 시그널' else '매도 고려'} (RSI: {technicals['rsi_signal']})."
            print(f"[dailyreport] Performance for {ticker}: return={item_return:.1f}%, weight={weight*100:.1f}%")

            # 3. 뉴스 2~3개 (Feedback)
            news = get_news_summary(ticker, assetType, num_news=3)

            # 4. 산업 동향 1~2개 (Feedback)
            trends = get_industry_trends(sector, num_trends=2)

            reports.append({
                "assetId": ticker,
                "technicals": technicals,
                "performance": {"return": item_return, "weight": weight},
                "explanation": explanation,
                "news": news,
                "industryTrends": trends,
                "riskLevel": "High" if item_return > 20 else "Medium" if item_return > 10 else "Low"
            })
            print(f"[dailyreport] Report entry created for {ticker}: {reports[-1]}")

        result = {
            "status": "success",
            "message": "일일 리포트 생성 성공",
            "data": {"reports": reports, "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")}
        }
        print(f"[dailyreport] Final result: {result}")
        return result
    
    except Exception as e:
        print(f"[dailyreport] Error in daily_report: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

