# diagnosis.py
import numpy as np
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pymysql
import asset_management

def calculate_technical_analysis(ticker, asset_type):
    # 현금, 예적금은 기술적 분석 대상에서 제외
    if asset_type not in ["국내주식", "해외주식", "가상자산"]:
        return {"assetId": ticker, "macd_signal": "N/A", "rsi": 0, "rsi_signal": "N/A"}
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

def diagnosis(user_id):
    try:
        print(f"[diagnosis] user_id: {user_id}")

        # DB 조회
        db = asset_management.connect_mysql()
        print("[diagnosis] DB 연결 성공")
        cursor = db.cursor(pymysql.cursors.DictCursor)

        # 포트폴리오 조회
        portfolio_sql = "SELECT asset_id, asset_name, quantity, average_price FROM USER_ASSET_LIST_TB WHERE user_id = %s"
        stock_info_sql = "SELECT ticker, asset_name, asset_type, sector FROM ASSET_INFO_TB"

        cursor.execute(portfolio_sql, (user_id,))
        portfolio_rows = cursor.fetchall()
        print(f"[diagnosis] portfolio_rows: {portfolio_rows}")

        cursor.execute(stock_info_sql)
        stock_info_rows = cursor.fetchall()
        print(f"[diagnosis] stock_info_rows: {stock_info_rows}")

        cursor.close()
        db.close()
        print("[diagnosis] DB 연결 종료")

        portfolio = pd.DataFrame(portfolio_rows, columns=["asset_id", "asset_name", "quantity", "average_price"])
        stock_info = pd.DataFrame(stock_info_rows, columns=["ticker", "asset_name", "asset_type", "sector"])

        # 병합
        portfolio = portfolio.merge(stock_info, on="asset_name")
        print(f"[diagnosis] 병합된 portfolio DataFrame:\n{portfolio}")

        # 실시간 가격
        portfolio["current_price"] = portfolio.apply(
            lambda x: fdr.DataReader(x["ticker"] + ("/KRW" if x["asset_type"] == "가상자산" else ""),
                                    "2025-09-22")["Close"].iloc[-1]
            if x["asset_type"] in ["국내주식", "해외주식", "가상자산"] else x["average_price"],
            axis=1
        )
        print(f"[diagnosis] current_price 컬럼 추가:\n{portfolio[['ticker', 'current_price']]}")

        # 가치 및 비중
        portfolio["value"] = portfolio["quantity"].astype(float) * portfolio["current_price"].astype(float)
        portfolio["weight"] = portfolio["value"] / portfolio["value"].sum()
        portfolio = portfolio.rename(columns={"ticker": "assetId"})
        sector_weights = portfolio.groupby("sector")["weight"].sum().to_dict()
        print(f"[diagnosis] sectorWeights: {sector_weights}")

        # 성과 분석 (현금도 예적금과 동일하게 처리)
        portfolio["return"] = portfolio.apply(
            lambda x: 0 if x["asset_type"] in ["예적금", "현금"] else (float(x["current_price"]) - float(x["average_price"])) / float(x["average_price"]),
            axis=1
        )
        total_return = (portfolio["weight"].astype(float) * portfolio["return"].astype(float)).sum() * 100
        print(f"[diagnosis] total_return: {total_return}")

        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        portfolio_returns = []
        for _, row in portfolio.iterrows():
            if row["asset_type"] in ["예적금", "현금"]:
                portfolio_returns.append(pd.Series(0.0, index=pd.date_range(start_date, "2025-09-22")))
            else:
                prices = fdr.DataReader(row["assetId"] + ("/KRW" if row["asset_type"] == "가상자산" else ""),
                                        start_date)["Close"]
                returns = prices.pct_change().dropna()
                portfolio_returns.append(returns * row["weight"])
        portfolio_std = np.std(sum(portfolio_returns)) * 100 if portfolio_returns else 0
        risk_free_rate = 0.03
        sharpe_ratio = (total_return / 100 - risk_free_rate) / portfolio_std if portfolio_std else 0
        print(f"[diagnosis] sharpe_ratio: {sharpe_ratio}")

        # 기술적 분석 (현금, 예적금 제외)
        technicals = [calculate_technical_analysis(row["assetId"], row["asset_type"])
                    for _, row in portfolio.iterrows()
                    if row["asset_type"] not in ["예적금", "현금"]]
        print(f"[diagnosis] technicals: {technicals}")

        # 다양성 점수
        hhi = (portfolio["weight"] ** 2).sum()
        diversity_score = (1 - hhi) * 100
        if len(portfolio) < 5:
            diversity_score -= 10
        if len(portfolio["sector"].unique()) < 3:
            diversity_score -= 10
        diversity_score = max(0, diversity_score)
        print(f"[diagnosis] diversity_score: {diversity_score}")

        # 리스크 및 MDD (현금, 예적금 동일 처리)
        portfolio_values = pd.Series(0.0, index=pd.date_range(start_date, "2025-09-22"))
        for _, row in portfolio.iterrows():
            if row["asset_type"] in ["예적금", "현금"]:
                values = pd.Series(float(row["quantity"]) * float(row["average_price"]), index=pd.date_range(start_date, "2025-09-22"))
            else:
                values = float(fdr.DataReader(row["assetId"] + ("/KRW" if row["asset_type"] == "가상자산" else ""),
                                        start_date)["Close"]) * float(row["quantity"])
            portfolio_values += values
        rolling_max = portfolio_values.cummax()
        drawdown = (portfolio_values - rolling_max) / rolling_max
        mdd = drawdown.min() * -100
        risk_level = "Low" if portfolio_std < 10 else "Medium" if portfolio_std <= 20 else "High"
        print(f"[diagnosis] mdd: {mdd}, risk_level: {risk_level}")

        return {
            "status": "success",
            "message": "포트폴리오 진단 성공",
            "data": {
                "stockWeights": portfolio[["assetId", "weight"]].to_dict(orient="records"),
                "sectorWeights": sector_weights,
                "performance": {"totalReturn": total_return, "sharpeRatio": sharpe_ratio},
                "technicals": technicals,
                "diversityScore": diversity_score,
                "risk": {"risk": portfolio_std, "riskLevel": risk_level, "mdd": mdd}
            }
        }
    except Exception as e:
        return print(f"[diagnosis] 오류: {e}"), {"status": "error", "message": str(e)}