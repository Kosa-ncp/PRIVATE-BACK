# feedback.py
import requests
import numpy as np
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr
import os
from dotenv import load_dotenv

load_dotenv()

NAVER_DEV_API_KEY = os.getenv("NAVER_DEV_API_KEY")
NAVER_DEV_SECRET_KEY = os.getenv("NAVER_DEV_SECRET_KEY")

def get_news_summary(ticker, asset_type):
    print(f"[feedback] 뉴스 요약 요청: ticker={ticker}, asset_type={asset_type}")
    if asset_type in ["예적금", "현금"]:
        return []
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_DEV_API_KEY,
        "X-Naver-Client-Secret": NAVER_DEV_SECRET_KEY
    }
    params = {"query": ticker, "sort": "date", "display": 1}
    response = requests.get(url, headers=headers, params=params)
    items = response.json().get("items", [])
    if not items:
        return []
    
    news_url = items[0]["link"]
    try:
        news_response = requests.get(news_url, timeout=5)
        soup = BeautifulSoup(news_response.text, "html.parser")
        article = soup.select_one("article") or soup.select_one(".article")
        content = article.get_text(strip=True) if article else items[0]["description"]
        content = re.sub(r"\s+", " ", content)[:500]
    except Exception:
        content = items[0]["description"]
   
    return [{"title": items[0]["title"], "content": content}]

def feedback(user_id, diagnosis_data):
    # 비중 조절
    sector_weights = diagnosis_data["sectorWeights"]
    diversity_score = diagnosis_data["diversityScore"]
    mdd = diagnosis_data["risk"]["mdd"]
    adjusted_weights = sector_weights.copy()
    suggestions = []

    if diversity_score < 50:
        for sector, weight in sector_weights.items():
            if weight > 0.4:
                adjusted_weights[sector] = 0.3
                suggestions.append(f"{sector} 비중을 {weight*100:.1f}%에서 30%로 줄여보는 건 어떨까요?")
        remaining_weight = 1 - sum(adjusted_weights.values())
        other_sectors = ["IT", "금융주", "예적금", "가상산"]
        per_sector = remaining_weight / len(other_sectors)
        for sector in other_sectors:
            adjusted_weights[sector] = adjusted_weights.get(sector, 0) + per_sector
            suggestions.append(f"{sector} 섹터를 {per_sector*100:.1f}% 추가를 제안 드립니다.")

    if mdd > 30:
        suggestions.append(f"MDD가 {mdd:.1f}%로 높습니다. 예적금 또는 금융주 비중을 40%로 늘려보는 건 어떨까요?")
        adjusted_weights["예적금"] = adjusted_weights.get("예적금", 0) + 0.2
        adjusted_weights["금융주"] = adjusted_weights.get("금융주", 0) + 0.2
        remaining_weight = 1 - sum(adjusted_weights.values())
        other_sectors = [s for s in adjusted_weights if s not in ["예적금", "금융주"]]
        for sector in other_sectors:
            adjusted_weights[sector] = remaining_weight / len(other_sectors) if other_sectors else 0

    # 섹터별 티커 정보 동적 추출
    # diagnosis_data["sectorTickers"]가 있다고 가정 (없으면 DB에서 조회 필요)
    sector_tickers = diagnosis_data.get("sectorTickers")
    if not sector_tickers:
        # DB에서 섹터별 티커 정보 조회 예시
        import asset_management
        db = asset_management.connect_mysql()
        cursor = db.cursor()
        cursor.execute("SELECT sector, ticker FROM ASSET_INFO_TB")
        rows = cursor.fetchall()
        db.close()
        sector_tickers = {}
        for sector, ticker in rows:
            sector_tickers.setdefault(sector, []).append(ticker)
    print(f"[feedback] sector_tickers: {sector_tickers}")

    # 섹터별 수익률 및 추천
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    market_trends = {}
    for sector, tickers in sector_tickers.items():
        returns = []
        for ticker in tickers:
            if sector in ["예적금", "현금"]:
                returns.append(0.0)
            else:
                try:
                    prices = fdr.DataReader(ticker + ("/KRW" if sector in ["Crypto", "Currency", "가상자산", "외화"] else ""),
                                            start_date)["Close"]
                    returns.append(prices.pct_change().mean())
                except Exception:
                    returns.append(0.0)
        market_trends[sector] = {"return": np.mean(returns), "tickers": tickers}
    
    top_sector = max(market_trends, key=lambda x: market_trends[x]["return"])
    top_tickers = market_trends[top_sector]["tickers"]
    if mdd > 30:
        safe_sectors = [s for s in sector_tickers if s in ["금융주", "예적금", "현금"]]
        if safe_sectors:
            top_sector = max(safe_sectors, key=lambda x: market_trends.get(x, {"return": 0})["return"])
            top_tickers = market_trends[top_sector]["tickers"]
            suggestions.append(f"안정적 섹터 {top_sector} 추천: {', '.join(top_tickers)}")
    else:
        suggestions.append(f"최고 수익률 섹터 {top_sector} (수익률 {market_trends[top_sector]['return']*100:.1f}%) 추천")

    # 뉴스 요약
    news = get_news_summary(top_tickers[0], top_sector)
    if news and "summary" in news[0]:
        suggestions.append(f"최신 뉴스: {news[0]['title']} (요약: {news[0]['summary']})")
    elif news:
        suggestions.append(f"최신 뉴스: {news[0]['title']} (내용: {news[0]['content']})")

    return {
        "status": "success",
        "message": "포트폴리오 피드백 성공",
        "data": {
            "adjustedWeights": adjusted_weights,
            "weightSuggestions": suggestions,
            "recommendedStocks": top_tickers,
            "marketSuggestions": [f"{s} (수익률 {market_trends[s]['return']*100:.1f}%)" for s in market_trends],
            "chatbotSummary": "\n".join(suggestions)
        }
    }