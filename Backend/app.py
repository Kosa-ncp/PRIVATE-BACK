from flask import Flask, request, jsonify
from flask_cors import CORS

from chatbot import test
from asset_management import *
from asset_info import *

app = Flask(__name__)

CORS(app)

"""
# 대시보드 CRUD (start)
# author: 이승원
"""

# 대시보드 조회
@app.get("/api/search")
def dashboard_get():
    user_id = request.headers.get('Authorization')
    user_id = user_id.split(" ", 1)[1]
    return get_user_dashboard(user_id)

"""
# 대시보드 CRUD (end)
"""


"""
# 포트폴리오 CRUD (start)
# author: 이승원
"""

# 포트폴리오 자산입력
@app.post("/api/portfolio")
def portfolio_add():
    data = request.get_json()
    data["userId"] = get_user_id()
    # 예외직접 컨트롤 할때
    # data = request.get_json(silent=True) 
    #if data is None and required:
    #    return None, (jsonify(error="MalformedJSON", message="Invalid JSON body"), 400)

    return add_user_portfolio(data)

# 포트폴리오 조회
@app.get("/api/portfolio")
def portfolio_get():
    return get_user_portfolio_list(get_user_id())

# 포트폴리오 자산수정
@app.patch("/api/portfolio")
def portfolio_patch():
    data = request.get_json()
    data["userId"] = get_user_id()

    return patch_user_portfolio(data)

# 포트폴리오 삭제
@app.delete("/api/portfolio")
def portfolio_del():
    data = request.get_json()
    data["userId"] = get_user_id()

    return del_user_portfolio(data)

"""
# 포트폴리오 CRUD (end)
"""

# user_id 추출, header에서 Authorization 값 추출
def get_user_id():
    user_id = request.headers.get('Authorization')
    user_id = user_id.split(" ", 1)[1]

    return user_id

"""
# API 연결 확인용 코드 (start)
"""
@app.route("/")
def hello_world():
    return test()
    
# POST 요청 예시, 포트폴리오 조회
@app.route("/api/portfolio_test", methods=["POST"])
def portfolio_data():
    # 받은 데이터
    data = request.get_json()
    
    # 보낼 데이터
    if not data:
        return jsonify({"error": "JSON 데이터 없음."}), 400

    assetType = data.get("assetType", "string")
    purchasePrice = data.get("purchasePrice", 12345)
    assetName = data.get("assetName", "")
    quantity = data.get("quantity", 123.456)
    
    sample_portfolio = {
        "status": "success",
        "message": "테스트",
        "data": {
            "assetId": "string",
            "assetName": assetName,
            "assetType": assetType,
            "purchasePrice": purchasePrice,
            "quantity": quantity,
            "createdAt": "20250101",
            "updatedAt": "20250912"
        }
    }
    
    return jsonify(sample_portfolio)

@app.route("/api/portfolio_test")
def portfolio_data1():
    sample_portfolio = {
        "status": "success",
        "message": "테스트",
        "data": {
            "assetId": "string",
            "assetName": "삼성전자",
            "assetType": "국내주식",
            "purchasePrice": "10000",
            "quantity": "10",
            "createdAt": "20250101",
            "updatedAt": "20250912"
        }
    }

    return jsonify(sample_portfolio)

@app.route("/api/portfolio_test2")
def portfolio_data2():
    sample_portfolio = {
        "portfolio": [
            {
                "data": {
                "assetId": "string",
                    "assetName": "삼성전자",
                    "assetType": "국내주식",
                    "createdAt": "20250101",
                    "purchasePrice": "10000",
                    "quantity": "10",
                    "updatedAt": "20250912"
                },
                "message": "테스트",
                "status": "success"
            }
            ,{
                "data": {
                    "assetId": "string",
                    "assetName": "테슬라",
                    "assetType": "해외주식",
                    "createdAt": "20250101",
                    "purchasePrice": "200000",
                    "quantity": "25",
                    "updatedAt": "20250916"
                },
                "message": "테스트",
                "status": "success"
            }
            ,{
                "data": {
                    "assetId": "string",
                    "assetName": "예금",
                    "assetType": "예적금",
                    "createdAt": "20250101",
                    "purchasePrice": "3000000",
                    "quantity": "1",
                    "updatedAt": "20250916"
                },
                "message": "테스트",
                "status": "success"
            }
        ]
    }

    return jsonify(sample_portfolio)


# 자산 정보 추가 테스트
@app.put("/api/inject_asset_info_test")
def inject_asset_info_test():
    return "update_asset_info 호출"
    # return update_asset_info()
"""
# API 연결 확인용 코드 (end)
"""