from flask import Flask, request, Response, jsonify
import pymysql
import FinanceDataReader as fdr
import asset_management

def update_asset_info():
    """
    KRX, KOSPI, KOSDAQ, KONEX, NASDAQ, NYSE, SP500 순서로 동기화 실행.
    중간에 하나라도 실패하면 해당 실패 응답을 즉시 반환.
    전부 성공하면 시장별 결과를 합쳐서 성공 반환.
    """
    markets = ["KRX", "KOSPI", "KOSDAQ", "KONEX", "NASDAQ", "NYSE", "SP500"]    # SP500은 거부됨
    results = []

    for m in markets:
        try:
            print(f"[UPDATE] start sync: market={m}")
            res = sync_asset_info(m)  # 기존에 쓰던 함수: sync_asset_info("KOSPI") 형식
            data, code = _normalize_sync_result(res)

            # 에러 판정: HTTP 코드가 400+ 이거나 data.status == 'error'
            is_error = (code and code >= 400) or (isinstance(data, dict) and data.get("status") == "error")

            # 로그
            print(f"[UPDATE] market={m} status_code={code} body={data}")

            if is_error:
                # 요청하신 대로: 오류가 나면 해당 return 값을 그대로 반환
                # data가 dict가 아니면 안전하게 포장
                if isinstance(res, Response):
                    return res
                elif isinstance(res, tuple) and len(res) == 2:
                    return res
                elif isinstance(data, dict):
                    return jsonify(data), code
                else:
                    return jsonify({"status": "error", "message": str(data) or "unknown error"}), code or 500

            # 성공 케이스: 결과 축적
            results.append({
                "market": m,
                "status_code": code,
                "body": data
            })

        except Exception as e:
            # 예외 발생 시에도 즉시 실패 반환
            print(f"[UPDATE-ERROR] market={m} error={repr(e)}")
            return jsonify({"status": "error", "message": str(e), "market": m}), 500

    # 전부 성공
    return jsonify({
        "status": "success",
        "message": "All markets synced successfully",
        "results": results
    }), 200
    

    update_asset_info_list = []
    update_asset_info = {
            "ticker": "",
            "assetName": "",
            "assetType": "",
            "sector": "",
            "registerAt": "",
            "updateAt": ""
        }
    updateAt = asset_management.now_iso()

    db = asset_management.connect_mysql()
    print("DB 연결 성공")
    cursor = db.cursor(pymysql.cursors.DictCursor)


    # 종목 목록 가져오기
    # KRX : KRX 종목 전체
    # KOSPI : KOSPI 종목
    # KOSDAQ : KOSDAQ 종목
    # KONEX : KONEX 종목
    # NASDAQ : 나스닥 종목
    # NYSE : 뉴욕증권거래소 종목
    # SP500 : S&P500 종목
    df_krx = fdr.StockListing("KRX")
    # df_kospi = fdr.StockListing("KOSPI")
    # df_kosdaq = fdr.StockListing("KOSDAQ")
    # df_konex = fdr.StockListing("KONEX")
    # df_nasdaq = fdr.StockListing("NASDAQ")
    # df_nyse = fdr.StockListing("NYSE")
    #df_sp500 = fdr.StockListing("SP500")

    # 종목 코드와 이름을 딕셔너리로 저장
    for _, row in df_krx.iterrows():
        # 모든 항목 딕셔너리 추가
        keys = row.keys()
        for key in keys:
            print(f"{key}: {row[key]}")
            
        print("-----")

        update_asset_info["ticker"] = row['Symbol']
        update_asset_info["assetName"] = row['Name']
        update_asset_info["assetType"] = "국내주식"
        update_asset_info["sector"] = row['Sector']
        update_asset_info["registerAt"] = updateAt
        update_asset_info["updateAt"] = updateAt


        # 








    # asset_df = fdr.DataReader(asset_code)
    # if asset_df.empty:
    #     return None  # 자산 정보를 가져올 수 없는 경우 None 반환

    # latest_data = asset_df.iloc[-1]
    # current_price = latest_data['Close']
    # change_rate = ((latest_data['Close'] - latest_data['Open']) / latest_data['Open']) * 100

    # asset_info = {
    #     'current_price': current_price,
    #     'change_rate': change_rate
    # }

    
    db.close()
    print("DB 연결 종료")
    
    return '자산 정보 종료' #asset_info


def _normalize_sync_result(res):
    """
    sync_asset_info의 반환을 (data: dict|None, status_code: int)로 정규화.
    - dict만 오면 (dict, 200)
    - (body, status) 튜플이면 그대로
    - Flask Response면 .get_json(), .status_code 추출
    """
    # (body, status) 튜플
    if isinstance(res, tuple) and len(res) == 2:
        body, status = res
    else:
        body, status = res, 200

    # Flask Response 처리
    if isinstance(body, Response):
        data = body.get_json(silent=True)
        code = body.status_code
        return (data, code)

    # dict/None 처리
    return (body, status)

def market_to_asset_type(market: str) -> str:
    m = (market or "").upper()
    if m in ("KRX", "KOSPI", "KOSDAQ", "KONEX"):
        return "국내주식"
    if m in ("NASDAQ", "NYSE", "SP500", "S&P500", "AMEX"):
        return "해외주식"
    return "기타"

def pick_column(df, candidates):
    """
    candidates = ["Symbol", "Code"] 처럼 우선순위 리스트.
    df에 존재하는 첫 컬럼명을 리턴, 없으면 None.
    """
    for c in candidates:
        if c in df.columns:
            return c
    return None

UPSERT_SQL = """
INSERT INTO ASSET_INFO_TB
    (ticker, asset_name, asset_type, sector, register_at, update_at)
VALUES
    (%s, %s, %s, %s, NOW(), NOW())
ON DUPLICATE KEY UPDATE
    asset_name = VALUES(asset_name),
    asset_type = VALUES(asset_type),
    sector     = VALUES(sector),
    update_at  = NOW()
"""

# @bp_admin.route("/admin/asset-info/sync", methods=["GET","POST"])
def sync_asset_info(market: str = "KRX"):
    # market = request.args.get("market", "KRX").upper()
    print("="*80)
    print(f"[SYNC-START] market={market} at {asset_management.now_iso()}")
    try:
        # 1) FDR에서 목록 로드
        print("[FDR] FinanceDataReader.__version__ 가져오는 중...")
        try:
            print("FinanceDataReader version:", fdr.__version__)
        except Exception as ve:
            print("FDR 버전 출력 중 예외:", repr(ve))

        print(f"[FDR] StockListing('{market}') 호출")
        df = fdr.StockListing(market)
        print("[FDR] DataFrame 로드 완료")
        print(f"[FDR] df.shape={df.shape}")
        print(f"[FDR] df.columns={list(df.columns)}")
        print("[FDR] df.head(3):")
        try:
            print(df.head(3).to_string())
        except Exception as he:
            print("df.head 출력 중 예외:", repr(he))

        if df is None or df.empty:
            msg = f"{market} 목록이 비어 있습니다."
            print("[WARN]", msg)
            return jsonify({"status":"success","message":msg,"count":0})

        # 2) 컬럼 자동 매핑
        ticker_col = pick_column(df, ["Symbol", "Code", "Ticker", "종목코드"])
        name_col   = pick_column(df, ["Name", "회사명"])
        sector_col = pick_column(df, ["Sector", "섹터", "Industry", "산업"])

        print(f"[MAP] ticker_col={ticker_col}, name_col={name_col}, sector_col={sector_col}")

        if ticker_col is None or name_col is None:
            # 서버에서 바로 원인 파악 가능하도록 디버그 정보 동반
            err = "FinanceDataReader 반환 데이터에 Symbol/Code 또는 Name/회사명 컬럼이 없습니다."
            print("[ERROR]", err)
            print("[HINT] 현재 컬럼 목록:", list(df.columns))
            print("[HINT] 예시 DF.head:")
            try:
                print(df.head(5).to_string())
            except:
                pass
            return jsonify({"status":"error","message":err,"columns":list(df.columns)}), 500

        # 3) 전처리 (결측치/공백 제거)
        use_cols = [c for c in [ticker_col, name_col, sector_col] if c is not None]
        df2 = df.copy()
        for c in use_cols:
            try:
                df2[c] = df2[c].fillna("").astype(str).str.strip()
            except Exception as ce:
                print(f"[WARN] 컬럼 정규화 실패: {c}, err={repr(ce)}")

        # 한국 시장의 경우 코드가 숫자형으로 들어오는 버전 방지: zero-pad(6자리)
        if ticker_col == "Code":
            print("[INFO] KRX Code 감지 → 6자리 제로패딩 적용")
            try:
                df2[ticker_col] = df2[ticker_col].apply(lambda x: str(x).zfill(6) if x and x.isdigit() else x)
            except Exception as pe:
                print("[WARN] 제로패딩 중 예외:", repr(pe))

        # 4) 레코드 생성
        a_type = market_to_asset_type(market)
        records = []
        row_count = 0
        for _, row in df2.iterrows():
            ticker = row.get(ticker_col, "")
            name   = row.get(name_col, "")
            sector = row.get(sector_col, "") if sector_col else ""

            name   = clip(name, 255)    # asset_name
            sector = clip(sector, 100)  # sector

            if not ticker or not name:
                continue
            records.append((ticker, name, a_type, sector))
            row_count += 1

        print(f"[BUILD] records 생성 완료: {row_count} rows")

        if not records:
            msg = "유효한 (ticker, name) 레코드가 없습니다."
            print("[WARN]", msg)
            return jsonify({"status":"success","message":msg,"count":0})

        # 5) DB 업서트 (배치)
        conn = None
        try:
            print("[DB] MySQL 연결 시도")
            conn = asset_management.connect_mysql()
            print("[DB] 연결 성공")
            with conn.cursor() as cur:
                BATCH = 1000
                total = len(records)
                print(f"[DB] 업서트 시작: 총 {total} 건, 배치={BATCH}")
                for i in range(0, total, BATCH):
                    chunk = records[i:i+BATCH]
                    # executemany에 맞게 튜플 형식을 SQL 파라미터와 일치시킴
                    cur.executemany(UPSERT_SQL, [(t, n, a_type, s) for (t, n, a_type, s) in chunk])
                    print(f"[DB] upsert batch {i}..{i+len(chunk)-1} OK")
                conn.commit()
                print("[DB] 커밋 완료")
        except Exception as dbe:
            print("[DB-ERROR]", repr(dbe))
            try:
                if conn:
                    conn.rollback()
                    print("[DB] 롤백 완료")
            except Exception as rbe:
                print("[DB-ROLLBACK-ERROR]", repr(rbe))
            return jsonify({"status":"error","message":str(dbe)}), 500
        finally:
            try:
                if conn: 
                    conn.close()
                    print("[DB] 연결 종료")
            except Exception as ce:
                print("[DB-CLOSE-WARN]", repr(ce))

        ok_msg = f"{market} 종목 정보 업서트 완료"
        print("[DONE]", ok_msg, f"총 건수={len(records)}")
        return jsonify({"status":"success","message":ok_msg,"count":len(records)})

    except Exception as e:
        print("[FATAL]", repr(e))
        return jsonify({"status":"error","message":str(e)}), 500
    finally:
        print(f"[SYNC-END] market={market} at {asset_management.now_iso()}")
        print("="*80)

def clip(s: str, max_len: int):
    s = (s or "").strip()
    if len(s) > max_len:
        print(f"[WARN] asset_name too long ({len(s)}>{max_len}): {s[:80]}...")
        return s[:max_len]
    return s
