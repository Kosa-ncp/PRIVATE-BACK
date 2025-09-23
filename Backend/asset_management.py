"""
### asset_management.py
# usage: 사용자 포트폴리오 CRUD
"""

### 할일
# - XSS 공격 방지
# - 입력값 받을때 유효성 검사하기
# - 컬럼 및 변수명 스네이크로 통일

# - 추가, 수정은 그냥 해당 데이터 조회해서 전체 돌려주는걸로 (따로 함수 만들어서 관리하는게 좋을듯)
# - 수정 때 매도,매수 구분해서 추가하고 별도 로직 추가
# - 추가 때 average 처리 어떻게 할지?
# - 일단은 티커랑 종목코드 가지고 있는 테이블 하나 새로 두고, 이름 없으면 입력단계에서 실패 하도록
#    - 종목 테이블 만들고

import decimal
import os, pymysql, math, uuid
from dotenv import load_dotenv
from flask import jsonify
from datetime import datetime

load_dotenv()

# 환경변수
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

SELECT_ASSET_SQL = """
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
        average_price AS averagePrice,
        create_at     AS createdAt,
        update_at     AS updatedAt
    FROM USER_ASSET_LIST_TB
    WHERE asset_id = %s
    LIMIT 1
"""

# 추가
def add_user_portfolio(data):
    print("추가 받은 데이터: ", data)

    token = str(uuid.uuid4())
    tokenArr = token.split('-')

    print("asfd")

    asset_id = str(tokenArr[2]) + str(tokenArr[1]) + str(tokenArr[0]) + str(tokenArr[3]) + str(tokenArr[4])   # asset_id 유일하게 주기
    userId = data.get("userId", None)
    assetType = data.get("assetType", None)
    assetName = data.get("assetName", None)
    quantity = data.get("quantity", 1)  # 수량
    annualInterestRate = data.get("annualInterestRate", None)   # DB 저장 안함
    principal = data.get("principal", None)
    averagePrice = data.get("averagePrice", None)
    expectedEarnings = data.get("expectedEarnings", None)   # DB 저장 안함
    openDate = data.get("openDate", None) # 안쓰는 데이터
    maturityDate = data.get("maturityDate", None) # 안쓰는 데이터
    updateAt = now_iso()

    # 자산 종류가 "예적금" 또는 "현금" 일때 수량 1로 고정
    if assetType == "예적금" or assetType == "현금":
        quantity = 1
        averagePrice = principal

    print(f"""asset_id: {asset_id}, userId: {userId}, assetType: {assetType},
           assetName: {assetName}, 
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
            expire_date,
            create_at,
            update_at
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s, 
            CURDATE(), 
            %s, %s, %s
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
        maturityDate,
        updateAt,  # createAt = updateAt
        updateAt
    )

    #DATE_FORMAT( SYSDATE(), '%y%m%d')
    
    print("실행 SQL: ", sql, values)

    cursor.execute(sql, values)
    #rows = cursor.fetchall()

    db.commit()
    db.close()
    print("DB 연결 종료")

    # DB 조회해서 값 가져오기
    user_portfolio_add = {
        "status": "success",
        "message": "포트폴리오 추가 완료",
        "data": {
            "assetId": asset_id,
            "assetName": assetName,
            "assetType": assetType,
            "purchasePrice": principal,
            "quantity": quantity,
            "createdAt": updateAt,
            "updatedAt": updateAt
        }
    }	
    
    return jsonify(user_portfolio_add)

# 조회
# 자산 테이블
def get_user_portfolio_list(user_id):
    # 데이터 가공
    user_portfolio_list = {
        "status": "fail",
        "data": []
    }

    db = connect_mysql()    
    print("DB 연결 성공")

    cursor = db.cursor()

    # 자산
    sql = """
        SELECT
            asset_id      AS assetId,
            user_id       AS userId,
            asset_name    AS assetName,
            asset_type    AS assetType,
            quantity      AS quantity,
            principal     AS principal,
            average_price AS averagePrice,
            register_date AS openDate,
            expire_date   AS maturityDate
          FROM USER_ASSET_LIST_TB 
         WHERE user_id = %s
    """
    print("실행 SQL: ", sql, user_id)

    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()

    # 자산 매칭
    for row in rows:
        asset_id = row[0] #
        asset_name = row[2]
        asset_type = row[3]
        quantity = row[4]
        principal = math.floor(row[5]) # 원금
        averagePrice = math.floor(row[6]) # 평단가

        # zero division 방지
        if quantity <= 0:
            quantity = 1
        if averagePrice <= 0:
            averagePrice = 1

        currentPrice = 100000    #TODO 현재가, API 통해 받기
        valuation = currentPrice * quantity # 평가금액
        profit = valuation - (averagePrice * quantity)
        profitRate = math.floor(profit / (averagePrice * quantity) * 10000) / 100 # 소수 둘째자리 처리

        user_portfolio_list["data"].append({
            "assetId": asset_id,
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
    print("수정 받은 데이터: ", data)
    
    assetId = data.get("assetId", None)
    requestUserId = data.get("userId", None)
    principal = data.get("principal", 0)    # 평단가
    quantity = data.get("quantity", 1)  # 수량
    orderType = data.get("orderType", None) # BUY 매수, SELL 매도
    updateAt = now_iso()
    
    principal = int(principal) if principal else 0    # 평단가
    quantity = decimal.Decimal(quantity) if quantity else decimal.Decimal(1) # 수량

    # 1) DB 연결
    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # 2) 수정 대상 존재 확인
    cursor.execute(SELECT_ASSET_SQL, (assetId,))
    print("실행 SQL:", SELECT_ASSET_SQL, (assetId,))
    row_check = cursor.fetchone()

    # 3) 없으면 404 응답
    if not row_check:
        db.close()
        return jsonify({
            "status": "error",
            "message": f"Portfolio(assetId={assetId}) not found",
            "data": None
        }), 404
    
    # 4) user 일치하는지 확인
    if row_check["userId"] != requestUserId:
        db.close()
        return jsonify({
            "status": "error",
            "message": f"Portfolio(user={requestUserId}) not authorized",
            "data": None
        }), 403
    
    # 5) 실제 수정 실행
    assetType = row_check["assetType"]
    tot_quantity = -1
    tot_principal = -1
    
    if orderType == "BUY":
        # 매수
        tot_quantity = row_check["quantity"] + quantity
        tot_principal = row_check["principal"] + principal
        print("BUY quantity", row_check["quantity"], quantity, tot_quantity)
        print("BUY principal", row_check["principal"], principal, tot_principal)
    elif orderType == "SELL":
        # 매도
        tot_quantity = row_check["quantity"] - quantity
        tot_principal = row_check["principal"] - principal
        print("SELL quantity", row_check["quantity"], quantity, tot_quantity)
        print("SELL principal", row_check["principal"], principal, tot_principal)

    if tot_quantity < 0:
        db.close()
        return jsonify({
            "status": "error",
            "message": f"Portfolio(assetId={assetId}) 수량이 부족합니다.",
            "data": None
        }), 400
    elif tot_quantity == 0:
        # 삭제
        del_user_portfolio(data)

    if tot_principal <= 0:
        db.close()
        return jsonify({
            "status": "error",
            "message": f"Portfolio(assetId={assetId}) 원금이 부족합니다.",
            "data": None
        }), 400
    
    # 자산 종류가 "예적금" 또는 "현금" 일때 수량 1로 고정
    if assetType == "예적금" or assetType == "현금":
        tot_quantity = 1
    
    tot_principal = int(tot_principal)

    # 평단가 재계산
    averagePrice = math.floor(tot_principal / tot_quantity) if tot_quantity > 0 else 0
    averagePrice = int(averagePrice)

    sql = """
        UPDATE USER_ASSET_LIST_TB
           SET principal = %s
             , quantity = %s
             , average_price = %s
             , update_at = %s
         WHERE asset_id = %s
    """
    print("실행 SQL:", sql, (tot_principal, tot_quantity, averagePrice, updateAt, assetId))
    cursor.execute(sql, (tot_principal, tot_quantity, averagePrice, updateAt, assetId))
    db.commit()

    # 5) 갱신된 레코드 조회해서 응답(프론트 편의)
    cursor.execute(SELECT_ASSET_SQL, (assetId,))
    row = cursor.fetchone()
    db.close()
    print("DB 연결 종료")

    return jsonify({
        "status": "success",
        "message": "포트폴리오 업데이트 완료",
        "data": row
    }), 200

# 삭제
def del_user_portfolio(data):
    assetId = data.get("assetId", None)
    requestUserId = data.get("userId", None)
    deleted_at = now_iso()
    asset_name = ""

    # 1) DB 연결
    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        # 2) 삭제 대상 존재/이름 확인
        cursor.execute(SELECT_ASSET_SQL, (assetId,))
        row_check = cursor.fetchone()

        if not row_check:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Portfolio(assetId={assetId}) not found",
                "data": None
            }), 404
        
        # user 일치하는지 확인
        if row_check["userId"] != requestUserId:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Portfolio(user={requestUserId}) not authorized",
                "data": None
            }), 403

        asset_name = row_check["assetName"]

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
        host = DATABASE_URL, 
        user = DATABASE_USERNAME,
        password = DATABASE_PASSWORD,
        port = 3306,
        db = 'asset', charset = 'utf8'
    )

def now_iso():
    # 서버 시간(UTC) ISO8601, 세계 서비스시 대비 (서버에 UTC로 저장 후 백엔드에서 시간대 수정)
    # return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    # 한국 시간(KST) ISO8601
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
    sql = """
        SELECT * 
          FROM USER_ASSET_LIST_TB 
         WHERE user_id = %s
    """
    print("실행 SQL: ", sql, user_id)

    cursor.execute(sql, (user_id,))
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
