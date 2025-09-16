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
from datetime import datetime

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
    user_id = "1234"#data.get("userId")  # 예: 1234
    asset_order = 2#data.get("assetOrder")  # 예: 1


    # 4) DB 연결 및 실행
    db = connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor()

    # 존재 여부 확인(옵션) — 없으면 404
    check_sql = """
        SELECT COUNT(1)
        FROM USER_ASSET_LIST_TB
        WHERE user_id = %s AND asset_order = %s
    """
    cursor.execute(check_sql, (user_id, asset_order))
    exists = cursor.fetchone()[0]
    if not exists:
        db.close()
        return jsonify(error="NotFound", message=f"Portfolio(userId={user_id}, assetOrder={asset_order}) not found"), 404

    sql = f"""
        UPDATE USER_ASSET_LIST_TB
           SET quantity = 666
         WHERE user_id = {user_id}
           AND asset_order = {asset_order}
    """

    print("실행 SQL:", sql)

    cursor.execute(sql)
    db.commit()

    # 5) 갱신된 레코드 조회해서 응답(프론트 편의)
    select_sql = f"""
        SELECT
            user_id       AS userId,
            asset_order   AS assetOrder,
            asset_name    AS assetName,
            asset_type    AS assetType,
            quantity      AS quantity,
            principal     AS principalPrice,
            register_date AS openDate,
            expire_date   AS maturityDate
        FROM USER_ASSET_LIST_TB
        WHERE user_id = {user_id} AND asset_order = {asset_order}
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

def del_user_portfolio(id):
    user_id = "1234"
    asset_order = 2

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
               AND asset_order = {asset_order}
            LIMIT 1
        """
        cursor.execute(select_sql)
        row = cursor.fetchone()

        if not row:
            db.close()
            return jsonify({
                "status": "error",
                "message": f"Portfolio(userId={user_id}, assetOrder={asset_order}) not found",
                "data": None
            }), 404

        # default cursor면 tuple로 나옵니다.
        asset_name = row[0]

        # 3) 실제 삭제 실행 (하드 삭제)
        delete_sql = f"""
            DELETE FROM USER_ASSET_LIST_TB
             WHERE user_id = {user_id}
               AND asset_order = {asset_order}
        """
        print("실행 SQL(DELETE):", delete_sql, "| params:", (user_id, asset_order))
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
