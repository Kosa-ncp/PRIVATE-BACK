# feedback.py
import requests
import numpy as np
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr

def get_news_summary(ticker, asset_type):
    if asset_type == "예적금":
        return []
    if asset_type == "현금":
        return []
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": "YOUR_CLIENT_ID", "X-Naver-Client-Secret": "YOUR_SECRET"} #API 키 값 입력 여기다 하는건지 확인
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
    
    summary_url = "https://naver-api.example.com/summary"
    summary_headers = {"Authorization": "Bearer YOUR_CLOVA_TOKEN"} #수정 필요할지 확인 필요
    summary_payload = {
        "content": content,
        "max_length": 50,
        "language": "ko"
    }
    try:
        summary_response = requests.post(summary_url, headers=summary_headers, json=summary_payload)
        summary = summary_response.json().get("summary", content[:50])
    except Exception:
        summary = content[:50]
    
    return [{"title": items[0]["title"], "summary": summary}]

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
        other_sectors = ["IT", "Financial", "Fixed Income", "Crypto", "Currency"]
        per_sector = remaining_weight / len(other_sectors)
        for sector in other_sectors:
            adjusted_weights[sector] = adjusted_weights.get(sector, 0) + per_sector
            suggestions.append(f"{sector} 섹터를 {per_sector*100:.1f}% 추가를 제안 드립니다.")

    if mdd > 30:
        suggestions.append(f"MDD가 {mdd:.1f}%로 높습니다. 예적금(Fixed Income) 또는 금융주(Financial) 비중을 40%로 늘려보는 건 어떨까요?")
        adjusted_weights["Fixed Income"] = adjusted_weights.get("Fixed Income", 0) + 0.2
        adjusted_weights["Financial"] = adjusted_weights.get("Financial", 0) + 0.2
        remaining_weight = 1 - sum(adjusted_weights.values())
        other_sectors = [s for s in adjusted_weights if s not in ["Fixed Income", "Financial"]]
        for sector in other_sectors:
            adjusted_weights[sector] = remaining_weight / len(other_sectors) if other_sectors else 0

    # 섹터별 수익률 및 추천
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    sectors = {
        "IT": ["AAPL", "MSFT"],
        "Financial": ["JPM", "GS"],
        "Fixed Income": ["SAVING1"],
        "Crypto": ["BTC", "ETH"],
        "Currency": ["USD"]
    }
    market_trends = {}
    for sector, tickers in sectors.items():
        returns = []
        for ticker in tickers:
            if sector == "Fixed Income":
                returns.append(0.0)
            else:
                try:
                    prices = fdr.DataReader(ticker + ("/KRW" if sector in ["Crypto", "Currency"] else ""),
                                            start_date)["Close"]
                    returns.append(prices.pct_change().mean())
                except Exception:
                    returns.append(0.0)  # 데이터 없으면 0으로 처리
        market_trends[sector] = {"return": np.mean(returns), "tickers": tickers}
    
    top_sector = max(market_trends, key=lambda x: market_trends[x]["return"])
    top_tickers = market_trends[top_sector]["tickers"]
    if mdd > 30:
        safe_sectors = ["Fixed Income", "Financial"]
        top_sector = max(safe_sectors, key=lambda x: market_trends.get(x, {"return": 0})["return"])
        top_tickers = market_trends[top_sector]["tickers"]
        suggestions.append(f"안정적 섹터 {top_sector} 추천: {', '.join(top_tickers)}")
    else:
        suggestions.append(f"최고 수익률 섹터 {top_sector} (수익률 {market_trends[top_sector]['return']*100:.1f}%) 추천")

    # 뉴스 요약
    news = get_news_summary(top_tickers[0], top_sector)
    if news:
        suggestions.append(f"최신 뉴스: {news[0]['title']} (요약: {news[0]['summary']})")

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