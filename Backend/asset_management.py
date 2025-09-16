"""
### asset_management.py
# usage: 사용자 포트폴리오 CRUD
"""

### 할일
# - XSS 공격 방지
# - 예적금 통장 기준으로 데이터 통신 짜놓았으니까 화면 정의 다시해서 API 명세서 재정의 필요
# - CRUD 완성
# - 예외처리 및 데이터 없는건?
# - 데이터 값 유효하지 않으면 기본값이라도 넣어야 될 듯

import os, pymysql
from dotenv import load_dotenv
from flask import jsonify

load_dotenv()

# 환경변수
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

# 추가
def add_user_portfolio(data):
    print("받은 데이터: ", data)

    id = "1234"
    assetType = data.get("assetType", None)
    purchasePrice = data.get("purchasePrice", None)
    averagePrice = data.get("averagePrice", None)
    assetName = data.get("assetName", None)
    quantity = data.get("quantity", None)
    annualInterestRate = data.get("annualInterestRate", None)
    principalPrice = data.get("principalPrice", None)
    expectedEarnings = data.get("expectedEarnings", None)
    openDate = data.get("openDate", None)
    maturityDate = data.get("maturityDate", None)

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    sql = f"""
        SELECT COALESCE(MAX(asset_order), 0)
        FROM USER_ASSET_LIST_TB
        WHERE user_id = {id}
    """
    cursor.execute(sql)
    asset_order =cursor.fetchone()[0]+ 1

    print("최대 자산 순서: ", asset_order)

    sql = f"""
        INSERT INTO USER_ASSET_LIST_TB
        (
            user_id,
            asset_order,
            asset_name,
            asset_type,
            quantity,
            principal,
            register_date,
            expire_date
        )
        VALUES
        (
            '{id}',
            {asset_order},
            '{assetName}',
            '{assetType}',
            {quantity},
            {principalPrice},
            {openDate},
            {maturityDate}
        )
    """
    #DATE_FORMAT( SYSDATE(), '%y%m%d')
    
    print("실행 SQL: ", sql)

    cursor.execute(sql)
    #rows = cursor.fetchall()

    db.commit()
    db.close()
    print("DB 연결 종료")

    user_portfolio_add = {
        "status": "success",
        "message": "포트폴리오 추가 완료",
        "data": {
            "assetId": id,
            "assetName": assetName,
            "assetType": assetType,
            "purchasePrice": purchasePrice,
            "quantity": quantity,
            "createdAt": openDate,
            "updatedAt": maturityDate
        }
    }	
    
    return jsonify(user_portfolio_add)

# 조회
def get_user_portfolio_list(id):
    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()
    sql = f"""
        SELECT * 
          FROM USER_DEPOSIT_LIST_TB 
         WHERE user_id = {id}
    """
    print("실행 SQL: ", sql)

    cursor.execute(sql)
    rows = cursor.fetchall()
    
    db.close()
    print("DB 연결 종료")

    # 데이터 가공
    user_portfolio_list = {
        "status": "success",
        "data": []
    }

    for row in rows:
        user_portfolio_list["data"].append({
            "assetId": row[0],
            "assetName": row[1],
            "assetType": row[2],
            "quantity": row[3],
            "marketValue": row[4],
            "averagePrice": row[5],
            "principal": row[6],
            "profit": row[7],
            "profitRate": row[8]
        })
    
    return jsonify(user_portfolio_list)

def patch_user_portfolio():
    return "포트폴리오 수정"

def del_user_portfolio(id):
    return "포트폴리오 삭제: " + id



def connect_mysql():
    return pymysql.connect(
        host=DATABASE_URL, 
        user=DATABASE_USERNAME,
        password=DATABASE_PASSWORD,
        port=3306,
        db='asset', charset='utf8'
    )

