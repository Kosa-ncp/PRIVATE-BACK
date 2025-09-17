"""
### asset_management.py
# usage: 사용자 포트폴리오 CRUD
"""

### 할일
# - XSS 공격 방지
# - CRUD 완성
#       - asset_id 유일하게 주기
#       - asset_id key로 조회 외 CRUD 완성
# - 예외처리 및 데이터 없는건?
# - 데이터 값 유효하지 않으면 기본값이라도 넣어야 될 듯

import os, pymysql, math
from dotenv import load_dotenv
from flask import jsonify
from datetime import datetime

load_dotenv()

# 환경변수
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

# 추가
def add_user_portfolio(data):
    print("받은 데이터: ", data)

    userId = data.get("userId", None)
    assetType = data.get("assetType", None)
    purchasePrice = data.get("purchasePrice", None)
    averagePrice = data.get("averagePrice", None)   # DB 저장 안함
    assetName = data.get("assetName", None)
    quantity = data.get("quantity", None)
    annualInterestRate = data.get("annualInterestRate", None)   # DB 저장 안함
    principalPrice = data.get("principalPrice", None)
    expectedEarnings = data.get("expectedEarnings", None)   # DB 저장 안함
    openDate = data.get("openDate", None) # 안쓰는 데이터
    maturityDate = data.get("maturityDate", None) # 안쓰는 데이터

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    sql = f"""
        INSERT INTO USER_ASSET_LIST_TB
        (
            user_id,
            asset_name,
            asset_type,
            quantity,
            principal,
            register_date,
            expire_date
        )
        VALUES
        (
            '{userId}',
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

    #TODO DB 조회해서 값 가져오기
    user_portfolio_add = {
        "status": "success",
        "message": "포트폴리오 추가 완료",
        "data": {
            "assetId": userId,
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
# 자산 테이블
def get_user_portfolio_list(id):
    # 데이터 가공
    user_portfolio_list = {
        "status": "fail",
        "data": []
    }

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    # 자산
    sql = f"""
        SELECT * 
          FROM USER_ASSET_LIST_TB 
         WHERE user_id = {id}
    """
    print("실행 SQL: ", sql)

    cursor.execute(sql)
    rows = cursor.fetchall()

    # 자산 매칭
    for row in rows:
        asset_id = row[0] #
        asset_name = row[2]
        asset_type = row[3]
        quantity = row[4]
        principal = math.floor(row[5]) # 원금
        averagePrice = math.floor(row[6]) # 평단가
        currentPrice = 100000    #TODO 현재가, API 통해 받기
        valuation = currentPrice * quantity # 평가금액
        profit = valuation - (averagePrice * quantity)
        profitRate = math.floor(profit / (averagePrice * quantity) * 10000) / 100 #TODO 소수 둘째자리 처리

        if asset_type.find("가상자산") < 0:
            quantity = math.floor(quantity)

        user_portfolio_list["data"].append({
            "assetId": asset_id,  #TODO 확인필요
            "assetName": asset_name,
            "assetType": asset_type,
            "quantity": quantity,
            "currentPrice": currentPrice,
            "valuation": math.floor(valuation),
            "averagePrice": averagePrice,  # 사용자 입력
            "principal": math.floor(averagePrice * quantity), 
            "profit": math.floor(profit),    # 평가금액 - 원금
            "profitRate": profitRate # (평가금액 - 원금) / 원금 * 100
        })
        
        
    db.close()
    print("DB 연결 종료")

    user_portfolio_list["status"] = "success"

    return jsonify(user_portfolio_list)

# 단건 수정
def patch_user_portfolio(data):
    user_id = data.get("assetId", None)
    # 추가할 값들 (assetId, purchasePrice, quantity)
    purchasePrice = data.get("purchasePrice", None)
    quantity = data.get("quantity", None)

    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor()

    check_sql = f"""
        SELECT COUNT(1)
          FROM USER_ASSET_LIST_TB
         WHERE user_id = {user_id}
    """
    cursor.execute(check_sql)
    exists = cursor.fetchone()[0]
    if not exists:
        db.close()
        return jsonify(error="Not Found", message=f"Portfolio(userId={user_id}) not found"), 404

    sql = f"""
        UPDATE USER_ASSET_LIST_TB
           SET purchasePrice = {purchasePrice}
             , quantity = {quantity}
         WHERE user_id = {user_id}
    """

    print("실행 SQL:", sql)

    cursor.execute(sql)
    db.commit()

    # 5) 갱신된 레코드 조회해서 응답(프론트 편의)
    select_sql = f"""
        SELECT
            user_id       AS userId,
            asset_name    AS assetName,
            asset_type    AS assetType,
            quantity      AS quantity,
            principal     AS principalPrice,
            register_date AS openDate,
            expire_date   AS maturityDate
        FROM USER_ASSET_LIST_TB
        WHERE user_id = {user_id}
    """
    cursor.execute(select_sql)
    row = cursor.fetchone()
    db.close()
    print("DB 연결 종료")

    return jsonify({
        "status": "success",
        "message": "포트폴리오 업데이트 완료",
        "data": row  # dict cursor가 아니라면 컬럼 매핑이 필요할 수 있음
    }), 200

# 삭제
def del_user_portfolio(id):
    user_id = id

    deleted_at = now_iso()

    # 1) DB 연결
    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor()

    try:
        # 2) 삭제 대상 존재/이름 확인
        select_sql = f"""
            SELECT asset_name
              FROM USER_ASSET_LIST_TB
             WHERE user_id = {user_id}
            LIMIT 1
        """
        cursor.execute(select_sql)
        row = cursor.fetchone()

        if not row:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Portfolio(userId={user_id}) not found",
                "data": None
            }), 404

        # default cursor면 tuple로 나옵니다.
        asset_name = row[0]

        # 3) 실제 삭제 실행 (하드 삭제)
        delete_sql = f"""
            DELETE FROM USER_ASSET_LIST_TB
             WHERE user_id = {user_id}
        """
        print("실행 SQL(DELETE):", delete_sql, "| params:", (user_id))
        cursor.execute(delete_sql)
        db.commit()

    except Exception as e:
        db.rollback()
        db.close()
        # 필요시 상세 로그 출력
        print("삭제 중 예외:", e)
        return jsonify({
            "status": "error",
            "message": "삭제 처리 중 오류가 발생했습니다.",
            "data": None
        }), 500

    db.close()
    print("DB 연결 종료")

    # 4) 요구한 응답 포맷으로 반환
    return jsonify({
        "status": "success",
        "message": "포트폴리오 삭제 완료",
        "data": {
            "assetId": str(user_id),      # NOTE: 별도 asset_id가 있으면 그 값으로 교체
            "assetName": asset_name,
            "deletedAt": deleted_at
        }
    }), 200



def connect_mysql():
    return pymysql.connect(
        host=DATABASE_URL, 
        user=DATABASE_USERNAME,
        password=DATABASE_PASSWORD,
        port=3306,
        db='asset', charset='utf8'
    )

def now_iso():
    # 서버 시간(UTC) ISO8601
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


###
# 대시보드 (내용 길어지면 파일 분리하기)
def get_user_dashboard(data):
    # 데이터 가공
    totalAssets = 0
    investmentPrincipal = 0
    profitAndLoss = 0
    assetsCount = 0
    assetType = []

    user_dashboard_list = {
        "totalAssets": 1,   # 총 자산
        "investmentPrincipal": 2,   # 투자 원금
        "profitAndLoss": 3,     # 손익
        "assetsCount": 5,   # 자산 종류 수
        "assetType": [      # 자산 종류별 수익률
            {
                "name": "국내주식",
                "rateOfReturn": 0.9,
            },
            {
                "name": "해외주식",
                "rateOfReturn": 0.8,
            },
            {
                "name": "가상자산",
                "rateOfReturn": 0.7,
            },
            {
                "name": "예적금",
                "rateOfReturn": 0.6,
            },
            {
                "name": "현금",
                "rateOfReturn": 0.5,
            },
        ],    
        "report": '추가중'     # 금일 투자 리포트
    }

    # db = connect_mysql()    
    # print("DB 연결 성공")

    # cursor = db.cursor()

    # # 자산
    # sql = f"""
    #     SELECT * 
    #       FROM USER_ASSET_LIST_TB 
    #      WHERE user_id = {id}
    # """
    # print("실행 SQL: ", sql)

    # cursor.execute(sql)
    # rows = cursor.fetchall()

    # # 자산 매칭
    # for row in rows:
    #     asset_id = row[0] #
    #     asset_name = row[2]
    #     asset_type = row[3]
    #     quantity = row[4]
    #     principal = math.floor(row[5]) # 원금
    #     averagePrice = math.floor(row[6]) # 평단가
    #     currentPrice = 100000    #TODO 현재가, API 통해 받기
    #     valuation = currentPrice * quantity # 평가금액
    #     profit = valuation - (averagePrice * quantity)
    #     profitRate = math.floor(profit / (averagePrice * quantity) * 10000) / 100 #TODO 소수 둘째자리 처리

        
    # db.close()
    # print("DB 연결 종료")

    return jsonify(user_dashboard_list)