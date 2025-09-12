from flask import Flask, request, jsonify
from chatbot import test

app = Flask(__name__)

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