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
# - 컬럼 및 변수명 스네이크로 통일

import os, pymysql, math, uuid
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

    token = str(uuid.uuid4())
    tokens = token.split('-')

    asset_id = str(tokens[2]) + str(tokens[1]) + str(tokens[0]) + str(tokens[3]) + str(tokens[4])   # asset_id 유일하게 주기
    userId = data.get("userId", None)
    assetType = data.get("assetType", None)
    purchasePrice = data.get("purchasePrice", None)
    averagePrice = data.get("averagePrice", None)   # DB 저장 안함
    assetName = data.get("assetName", None)
    quantity = data.get("quantity", None)
    annualInterestRate = data.get("annualInterestRate", None)   # DB 저장 안함
    principal = data.get("principal", None)
    expectedEarnings = data.get("expectedEarnings", None)   # DB 저장 안함
    openDate = data.get("openDate", None) # 안쓰는 데이터
    maturityDate = data.get("maturityDate", None) # 안쓰는 데이터

    print(f"""asset_id: {asset_id}, userId: {userId}, assetType: {assetType},
           purchasePrice: {purchasePrice}, assetName: {assetName}, 
           quantity: {quantity}, principal: {principal}, 
           openDate: {openDate}, maturityDate: {maturityDate}"""
    )

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    sql = """
        INSERT INTO USER_ASSET_LIST_TB
        (
            asset_id,
            user_id,
            asset_name,
            asset_type,
            quantity,
            principal,
            average_price,
            register_date,
            expire_date
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    values = (
        asset_id,
        userId,
        assetName,
        assetType,
        quantity,
        principal,
        averagePrice,
        openDate,
        maturityDate
    )

    #DATE_FORMAT( SYSDATE(), '%y%m%d')
    
    print("실행 SQL: ", sql, values)

    cursor.execute(sql, values)
    #rows = cursor.fetchall()

    db.commit()
    db.close()
    print("DB 연결 종료")

    #TODO DB 조회해서 값 가져오기
    user_portfolio_add = {
        "status": "success",
        "message": "포트폴리오 추가 완료",
        "data": {
            "assetId": asset_id,
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

        user_portfolio_list["data"].append({
            "assetId": asset_id,  #TODO 확인필요
            "assetName": asset_name,
            "assetType": asset_type,
            "quantity": quantity if asset_type.find("가상자산") > -1 else math.floor(quantity),
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
    assetId = data.get("assetId", None)
    # 추가할 값들 (assetId, purchasePrice, quantity)
    purchasePrice = data.get("purchasePrice", None)
    quantity = data.get("quantity", None)

    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor()

    check_sql = """
        SELECT COUNT(1)
          FROM USER_ASSET_LIST_TB
         WHERE asset_id = %s
    """
    cursor.execute(check_sql, (assetId,))
    exists = cursor.fetchone()[0]
    if not exists:
        db.close()
        return jsonify(error="Not Found", message=f"Portfolio(assetId={assetId}) not found"), 404

    sql = """
        UPDATE USER_ASSET_LIST_TB
           SET principal = %s
             , quantity = %s
         WHERE asset_id = %s
    """
    print("실행 SQL:", sql, (purchasePrice, quantity, assetId))
    cursor.execute(sql, (purchasePrice, quantity, assetId))
    db.commit()

    # 5) 갱신된 레코드 조회해서 응답(프론트 편의)
    select_sql = """
        SELECT
            asset_id      AS assetId,
            user_id       AS userId,
            asset_name    AS assetName,
            asset_type    AS assetType,
            CASE
                WHEN asset_type <> '가상자산' THEN TRUNCATE(quantity, 0)
                ELSE quantity
            END     AS quantity,
            principal     AS principal,
            register_date AS openDate,
            expire_date   AS maturityDate
        FROM USER_ASSET_LIST_TB
        WHERE asset_id = %s
    """
    cursor.execute(select_sql, (assetId,))
    row = cursor.fetchone()
    db.close()
    print("DB 연결 종료")

    return jsonify({
        "status": "success",
        "message": "포트폴리오 업데이트 완료",
        "data": row  # dict cursor가 아니라면 컬럼 매핑이 필요할 수 있음
    }), 200

# 삭제
def del_user_portfolio(data):
    assetId = data.get("assetId", None)

    deleted_at = now_iso()

    # 1) DB 연결
    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor()

    try:
        # 2) 삭제 대상 존재/이름 확인
        select_sql = """
            SELECT asset_name
              FROM USER_ASSET_LIST_TB
             WHERE asset_id = %s
            LIMIT 1
        """
        cursor.execute(select_sql, (assetId,))
        row = cursor.fetchone()

        if not row:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Portfolio(assetId={assetId}) not found",
                "data": None
            }), 404

        # default cursor면 tuple로 나옵니다.
        asset_name = row[0]

        # 3) 실제 삭제 실행 (하드 삭제)
        delete_sql = """
            DELETE FROM USER_ASSET_LIST_TB
             WHERE asset_id = %s
        """
        print("실행 SQL(DELETE):", delete_sql, "| params:", (assetId,))
        cursor.execute(delete_sql, (assetId,))
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
            "assetId": str(assetId),
            "assetName": asset_name,
            "deletedAt": deleted_at
        }
    }), 200


# DB 연결
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
def get_user_dashboard(user_id):
    # 데이터 가공
    totalAssets = 0     # sum (currentPrice * quantity) -> valuation
    investmentPrincipal = 0 # sum(averagePrice * quantity)
    profitAndLoss = 0   # sum(profit = valuation - (averagePrice * quantity))
    assetsCount = 0 # assetType 에서 뽑기

    total_principal_kor = 0.00
    total_principal_for = 0.00
    total_principal_virtual = 0.00
    total_principal_deposit = 0.00
    total_principal_cash = 0.00

    total_valuation_kor = 0.00
    total_valuation_for = 0.00
    total_valuation_virtual = 0.00
    total_valuation_deposit = 0.00
    total_valuation_cash = 0.00

    user_dashboard_list = {}
    user_dashboard_list["status"] = "fail"
    user_dashboard_list["data"] = {
        "totalAssets": 0,   # 총 자산
        "investmentPrincipal": 0,   # 투자 원금
        "profitAndLoss": 0,     # 손익
        "assetsCount": 0,   # 자산 종류 수
        "assetType": [      # 자산 종류별 수익률
            {
                "name": "국내주식",
                "rateOfReturn": 0.00,
            },
            {
                "name": "해외주식",
                "rateOfReturn": 0.00,
            },
            {
                "name": "가상자산",
                "rateOfReturn": 0.00,
            },
            {
                "name": "예적금",
                "rateOfReturn": 0.00,
            },
            {
                "name": "현금",
                "rateOfReturn": 0.00,
            },
        ],    
        "report": '추가중'     # 금일 투자 리포트
    }

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    # 자산
    sql = f"""
        SELECT * 
          FROM USER_ASSET_LIST_TB 
         WHERE user_id = {user_id}
    """
    print("실행 SQL: ", sql)

    cursor.execute(sql)
    rows_user_asset = cursor.fetchall()

    # 자산 매칭
    for row in rows_user_asset:
        asset_id = row[0] #
        asset_name = row[2]
        asset_type = row[3]
        quantity = row[4]
        averagePrice = math.floor(row[6]) # 평단가
        principal = averagePrice * quantity # 원금
        currentPrice = 100000    #TODO 현재가, API 통해 받기
        valuation = currentPrice * quantity # 평가금액
        profit = valuation - (averagePrice * quantity)
        profitRate = math.floor(profit / (averagePrice * quantity) * 10000) / 100

        totalAssets += valuation
        investmentPrincipal += principal
        profitAndLoss += profit
        
        # (전체 평가금액 - 전체 원금) / 전체 원금 * 100
        if asset_type == "국내주식":
            total_valuation_kor += math.floor(valuation)
            total_principal_kor += math.floor(principal)
        elif asset_type == "해외주식":
            total_valuation_for += math.floor(valuation)
            total_principal_for += math.floor(principal)
        elif asset_type == "가상자산":
            total_valuation_virtual += math.floor(valuation)
            total_principal_virtual += math.floor(principal)
        elif asset_type == "예적금":
            total_valuation_deposit += math.floor(valuation)
            total_principal_deposit += math.floor(principal)
        elif asset_type == "현금":
            total_valuation_cash += math.floor(valuation)
            total_principal_cash += math.floor(principal)

    # 자산 종류별 수익률 계산
    if total_principal_kor > 0:
        user_dashboard_list["data"]["assetType"][0]["rateOfReturn"] = math.floor((total_valuation_kor - total_principal_kor) / total_principal_kor * 10000) / 100
    if total_principal_for > 0:
        user_dashboard_list["data"]["assetType"][1]["rateOfReturn"] = math.floor((total_valuation_for - total_principal_for) / total_principal_for * 10000) / 100
    if total_principal_virtual > 0:
        user_dashboard_list["data"]["assetType"][2]["rateOfReturn"] = math.floor((total_valuation_virtual - total_principal_virtual) / total_principal_virtual * 10000) / 100
    if total_principal_deposit > 0:
        user_dashboard_list["data"]["assetType"][3]["rateOfReturn"] = math.floor((total_valuation_deposit - total_principal_deposit) / total_principal_deposit * 10000) / 100
    if total_principal_cash > 0:
        user_dashboard_list["data"]["assetType"][4]["rateOfReturn"] = math.floor((total_valuation_cash - total_principal_cash) / total_principal_cash * 10000) / 100

    # 자산 종류 수
    sql = f"""
        SELECT COUNT(DISTINCT asset_name)
          FROM USER_ASSET_LIST_TB
         WHERE user_id = {user_id}
    """
    print("실행 SQL: ", sql)

    cursor.execute(sql)
    row_asset_count = cursor.fetchone()

    user_dashboard_list["data"]["assetsCount"] = row_asset_count[0]
    user_dashboard_list["data"]["totalAssets"] = math.floor(totalAssets)
    user_dashboard_list["data"]["investmentPrincipal"] = math.floor(investmentPrincipal)
    user_dashboard_list["data"]["profitAndLoss"] = math.floor(profitAndLoss)

    db.close()
    print("DB 연결 종료")

    user_dashboard_list["status"] = "success"

    return jsonify(user_dashboard_list)