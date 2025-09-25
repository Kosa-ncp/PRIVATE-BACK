from flask import jsonify
from urllib import request as urllib_request
from bs4 import BeautifulSoup
from coingecko_sdk import Coingecko, APIConnectionError, APIStatusError, RateLimitError
from dotenv import load_dotenv
import re, pymysql, os

import asset_management


load_dotenv()

# 환경변수
GECKO_API_KEY = os.getenv("GECKO_API_KEY")

# 이름으로 여러건 있는 경우 ticker 짧은 순서로 정렬해 하나만 반환
SELECT_ASSET_INFO_SINGLE_SQL = """
    SELECT
            ticker      AS ticker,
            asset_name  AS assetName,
            asset_type  AS assetType,
            sector      AS sector,
            register_at AS createdAt,
            update_at   AS updatedAt
      FROM ASSET_INFO_TB
     WHERE asset_name = %s
     ORDER BY ticker
     LIMIT 1
"""

# 이름이 포함된 여러건 반환
SELECT_ASSET_INFO_LIST_SQL = """
    SELECT
            ticker      AS ticker,
            asset_name  AS assetName,
            asset_type  AS assetType,
            sector      AS sector,
            register_at AS createdAt,
            update_at   AS updatedAt
      FROM ASSET_INFO_TB
     WHERE asset_name LIKE %s
     ORDER BY ticker
     LIMIT 1
"""

def get_asset_info_single(asset_name: str):
    """
    자산 정보 단건 조회
    """
    try:
        db = asset_management.connect_mysql()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        cursor.execute(SELECT_ASSET_INFO_SINGLE_SQL, (asset_name,))
        print("실행 SQL:", SELECT_ASSET_INFO_SINGLE_SQL, (asset_name,))
        asset_info = cursor.fetchone()

        return jsonify({
            "status": "success",
            "data": asset_info
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
def find_asset_info_list(asset_name: str):
    """
    자산 정보 목록 조회
    """
    try:
        db = asset_management.connect_mysql()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        cursor.execute(SELECT_ASSET_INFO_LIST_SQL, (f"%{asset_name}%",))
        print("실행 SQL:", SELECT_ASSET_INFO_LIST_SQL, (f"%{asset_name}%",))
        asset_info_list = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": asset_info_list
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

def get_asset_info_current(ticker: str):
    """
    자산 정보 현재 가격 조회 (ticker 기준)
    """
    try:
        url = "https://finance.naver.com/item/main.nhn?code=" + ticker  # 종목코드 또는 ticker로 조회
        html = urllib_request.urlopen(url).read().decode("utf-8")

        # dl class 뽑기
        pattern1 = r"(\<dl class=\"blind\"\>)([\s\S]+?)(\</dl\>)"
        # pattern1 비었을 때 예외 처리
        if not re.search(pattern1, html):
            raise ValueError("해당 티커에 대한 정보를 찾을 수 없습니다.")
        result = re.findall(pattern1, html)  # <dl class="blind"> </dl> 읽어오기 list type
        result = result[0][1].strip() # html 헤더정보는 제외하고 중간의 원하는 정보만 뽑아와서 str으로 변환

        # dd 정보들 뽑기
        pattern2 = r"(\<dd\>)([\s\S]+?)(\</dd\>)"
        detail_results = re.findall(pattern2, result)  # 변환된 list 중 필요 정보는 <dd>태그 내부 정보만 list로 추출

        current_price = extract_current_price(detail_results)
        if current_price is None:
            raise ValueError("현재가 정보를 추출하지 못했습니다.")

        return jsonify({
            "status": "success",
            "data": {
                "currentPrice": current_price
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def extract_current_price(items):
    """
    현재가 추출
    """
    for _, text, _ in items:
        if '현재가' in text:
            # '현재가 99,999 전일대비 …' 에서 99,999만 추출
            m = re.search(r'현재가\s*([0-9,]+)', text)

            if m:
                return int(m.group(1).replace(',', ''))
            
            # 형식이 달라도 첫 번째 숫자 블록을 잡는 폴백
            m = re.search(r'([0-9][0-9,]*)', text)

            if m:
                return int(m.group(1).replace(',', ''))
    return None



def get_current_stock_price_with_name(asset_name: str):
    """
    자산 이름으로 현재가 조회 (asset_info.py 활용)
    """

    asset_info_response = get_asset_info_single(asset_name)
    if asset_info_response[1] != 200:
        print(f"{asset_name} 정보 조회 실패: {asset_info_response[0].get_json()}")
        return 0

    asset_data = asset_info_response[0].get_json().get("data", None)
    if not asset_data or "ticker" not in asset_data:
        print(f"{asset_name} 자산 정보에 ticker가 없습니다.")
        return 0

    ticker = asset_data["ticker"]
    sector = asset_data["sector"]

    # sector 값이 없는 경우 크롤링 해서 추가해주기
    if not sector:
        search_sector = get_sector(ticker)
        if search_sector:
            try:
                db = asset_management.connect_mysql()
                cursor = db.cursor(pymysql.cursors.DictCursor)
                update_at = asset_management.now_iso()
                update_sql = """
                    UPDATE ASSET_INFO_TB
                    SET sector = %s,
                        update_at = %s
                    WHERE ticker = %s
                """
                cursor.execute(update_sql, (search_sector, update_at, ticker))
                db.commit()
                db.close()
                print(f"{asset_name} sector 정보 DB에 업데이트 완료: {search_sector}")
                sector = search_sector
            except Exception as e:
                print(f"{asset_name} sector DB 업데이트 실패: {e}")
    
    current_price_response = get_asset_info_current(ticker)
    if current_price_response[1] != 200:
        print(f"{asset_name} 현재가 조회 실패: {current_price_response[0].get_json()}")
        return 0

    current_price_data = current_price_response[0].get_json().get("data", None)
    if not current_price_data or "currentPrice" not in current_price_data:
        print(f"{asset_name} 현재가 정보가 없습니다.")
        return 0

    return current_price_data["currentPrice"]


# 가상자산 실시간 받아오기
def get_current_virtual_price_with_name(asset_name: str):
    cg = Coingecko(
        environment  = "demo", 
        demo_api_key = GECKO_API_KEY
    )

    # 1) 이름으로 (쉼표로 여러 개)
    price_by_names = cg.simple.price.get(
        names         = asset_name,           # 코인 '이름'
        vs_currencies = "usd,krw"
    )
    print("by names:", price_by_names)

    item = price_by_names.get(asset_name)
    krw = item["krw"] if isinstance(item, dict) else getattr(item, "krw", None)

    if krw is None:
        print("KRW price not found for ", asset_name)
        return 0
    return (int(krw))


#####################
# 섹터 (start)
#####################

def _try_yfinance_sector(symbol: str):
    """
    yfinance API로 섹터 조회 시도.
    - 성공: 섹터 문자열 반환
    - 실패: None
    """
    print(f"[sector] yfinance 시도 → symbol={symbol}")
    try:
        import yfinance as yf
    except ImportError:
        print("[sector] yfinance 미설치 → 건너뜀")
        return None

    try:
        t = yf.Ticker(symbol)
        info = t.get_info()  # yfinance>=2.x (구버전은 .info)
        sector = info.get("sector")
        if isinstance(sector, str) and sector.strip():
            sector = sector.strip()
            print(f"[sector] yfinance 성공 → sector='{sector}'")
            return sector
        print("[sector] yfinance 반환값에 sector 키 없음 또는 빈 문자열")
    except Exception as e:
        print(f"[sector] yfinance 예외 발생: {type(e).__name__} - {e}")
    return None


def _naver_sector_kr(ticker: str):
    """
    네이버 금융(국내 종목)에서 섹터 텍스트 추출 (HTML 파싱).
    - ticker: '005930' 같은 6자리 코드
    """
    url = f"https://finance.naver.com/item/main.nhn?code={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"[sector] 네이버 시도 → code={ticker}, url={url}")

    try:
        r = urllib_request.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[sector] 네이버 요청 실패: {type(e).__name__} - {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) 종목분류 블록의 링크 텍스트 후보 수집
    candidates = []
    for a in soup.select("table td a"):
        txt = a.get_text(strip=True)
        if txt and txt not in ("코스피", "코스닥", "KOSPI", "KOSDAQ"):
            candidates.append(txt)

    # 2) 백업: '업종' 라벨 근처 dd 텍스트
    if not candidates:
        for dt in soup.select("dt"):
            if "업종" in dt.get_text():
                dd = dt.find_next_sibling("dd")
                if dd:
                    candidates.append(dd.get_text(strip=True))

    print(f"[sector] 네이버 후보 개수: {len(candidates)}")

    # 휴리스틱: 한글/영문 포함 & 너무 짧지 않은 첫 번째 후보 반환
    for c in candidates:
        if re.search(r"[가-힣A-Za-z]", c) and len(c) >= 2:
            print(f"[sector] 네이버 성공 → sector='{c}'")
            return c

    print("[sector] 네이버에서 유효한 섹터 텍스트를 찾지 못함")
    return None


def get_sector(ticker_or_code: str):
    """
    해외 티커/국내 6자리 종목코드 모두 지원하는 통합 함수.
    우선순위: yfinance → (국내 코드일 때) 네이버 폴백
    """
    s = (ticker_or_code or "").strip()
    if not s:
        print("[sector] 입력이 비어있음")
        return None

    s_upper = s.upper()
    print(f"[sector] 요청 시작: raw='{s}', norm='{s_upper}'")

    # 1) 해외(영문 포함 & 6자리 숫자가 아님) → yfinance 우선
    if re.search(r"[A-Z]", s_upper) and not re.fullmatch(r"\d{6}", s_upper):
        print("[sector] 분기: 해외 티커로 판단 (yfinance만 시도)")
        return _try_yfinance_sector(s_upper)

    # 2) 국내 6자리 코드
    if re.fullmatch(r"\d{6}", s_upper):
        print("[sector] 분기: 국내 6자리 코드로 판단")
        # 먼저 yfinance 접미사(.KS/.KQ) 시도
        for suffix in (".KS", ".KQ"):
            symbol = s_upper + suffix
            sec = _try_yfinance_sector(symbol)
            if sec:
                print(f"[sector] 국내 yfinance 성공 ({symbol})")
                return sec
        # 실패 시 네이버 폴백
        print("[sector] 국내 yfinance 실패 → 네이버 폴백으로 전환")
        return _naver_sector_kr(s_upper)

    # 3) 그 밖의 형식: 일단 yfinance 한번 시도
    print("[sector] 분기: 기타 형식 → yfinance 단일 시도")
    return _try_yfinance_sector(s_upper)

#####################
# 섹터 (end)
#####################


