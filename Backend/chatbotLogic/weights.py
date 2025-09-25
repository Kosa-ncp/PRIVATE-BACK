# weights.py
import FinanceDataReader as fdr
import pandas as pd
import sqlite3
import asset_management
import pymysql
import chatbotLogic.composition as composition

def weights(user_id):
    print(f"[weights] user_id: {user_id}")

    # DB 조회
    portfolio_result = composition.composition(user_id)
    print(f"[weights] composition 반환 결과: {portfolio_result}")

    portfolio_df = pd.DataFrame(portfolio_result["data"])
    print(f"[weights] portfolio DataFrame:\n{portfolio_df}")

    # 비중 계산
    portfolio_df["value"] = portfolio_df["quantity"].astype(float) * portfolio_df["currentPrice"].astype(float)*100 
    print(f"[weights] value 컬럼 추가:\n{portfolio_df[['assetName', 'value']]}")

    total_value = portfolio_df["value"].sum()
    print(f"[weights] 전체 포트폴리오 가치: {total_value}")

    portfolio_df["weight"] = portfolio_df["value"] / total_value*100
    print(f"[weights] weight 컬럼 추가:\n{portfolio_df[['assetName', 'weight']]}")

    sector_weights = portfolio_df.groupby("sector")["weight"].sum().to_dict()
    print(f"[weights] sectorWeights: {sector_weights}")

    result = {
        "status": "success",
        "message": "비중 계산 성공",
        "data": {
            "stockWeights": portfolio_df[["assetName", "weight"]].to_dict(orient="records"),
            "sectorWeights": sector_weights
        }
    }
    print(f"[weights] 반환 결과: {result}")

    return result