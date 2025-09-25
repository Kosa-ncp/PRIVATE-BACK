# composition.py
import FinanceDataReader as fdr
import pandas as pd
import asset_management
import pymysql

portfolio_sql = "SELECT asset_id, asset_name, quantity, average_price, create_at, update_at FROM USER_ASSET_LIST_TB WHERE user_id = %s"
stock_info_sql = "SELECT ticker, asset_name, asset_type, sector FROM ASSET_INFO_TB"

def composition(user_id):
    print(f"[composition] user_id: {user_id}")

    # DB 조회
    db = asset_management.connect_mysql()
    print("[composition] DB 연결 성공")
    conn = db.cursor(pymysql.cursors.DictCursor)
    
    conn.execute(stock_info_sql)
    stock_info_rows = conn.fetchall()
    print(f"[composition] stock_info_rows: {stock_info_rows}")

    stock_info = pd.DataFrame(stock_info_rows, columns=["ticker", "asset_name", "asset_type", "sector"])
    print(f"[composition] stock_info DataFrame:\n{stock_info}")

    conn.execute(portfolio_sql, (user_id,))
    portfolio_rows = conn.fetchall()
    print(f"[composition] portfolio_rows: {portfolio_rows}")

    portfolio = pd.DataFrame(portfolio_rows, columns=["asset_id", "asset_name", "quantity", "average_price", "create_at", "update_at"])
    print(f"[composition] portfolio DataFrame:\n{portfolio}")

    conn.close()
    print("[composition] DB 연결 종료")

    # 데이터 형식 조정
    portfolio = portfolio.merge(stock_info, on="asset_name")
    print(f"[composition] 병합된 portfolio DataFrame:\n{portfolio}")

    portfolio["current_price"] = portfolio.apply(  #실시간 연동으로 수정 예정 (현재는 2025-09-22 고정) -- 재윤재윤
        lambda x: fdr.DataReader(x["ticker"] + ("/KRW" if x["asset_type"] in ["가상자산", "외화"] else ""),
                                 "2025-09-22")["Close"].iloc[-1]
        if x["asset_type"] in ["국내주식", "해외주식", "가상자산", "외화"] else x["average_price"],
        axis=1
    )
    print(f"[composition] current_price 컬럼 추가:\n{portfolio[['ticker', 'current_price']]}")

    portfolio["current_value"] = portfolio["quantity"].astype(float) * portfolio["current_price"]
    portfolio["current_value"] = portfolio["current_value"].round(2)
    print(f"[composition] current_value 컬럼 추가:\n{portfolio[['ticker', 'current_value']]}")

    portfolio = portfolio.rename(columns={
        "asset_id": "assetId",
        "asset_name": "assetName",
        "asset_type": "assetType",
        "create_at": "createdAt",
        "update_at": "updatedAt",
        "average_price": "purchasePrice"
    })

    portfolio["quantity"] = portfolio["quantity"].astype(str)
    portfolio["purchasePrice"] = portfolio["purchasePrice"].astype(str)
    portfolio["currentPrice"] = portfolio["current_price"].astype(str)
    portfolio["currentValue"] = portfolio["current_value"].astype(str)

    print(f"[composition] 최종 portfolio DataFrame:\n{portfolio}")

    result = {
        "status": "success",
        "message": "포트폴리오 조회 성공",
        "data": portfolio[["assetId", "ticker", "assetName", "assetType", "quantity", "purchasePrice",
                           "currentPrice", "currentValue", "createdAt", "updatedAt", "sector"]].to_dict(orient="records")
    }
    print(f"[composition] 반환 결과: {result}")

    return result