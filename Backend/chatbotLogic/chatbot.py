import requests, os
from dotenv import load_dotenv

load_dotenv()

# 환경변수
CHATBOT_REQUEST_ID = os.getenv("CHATBOT_REQUEST_ID")
CHATBOT_API_KEY = os.getenv("CHATBOT_API_KEY")
CHATBOT_COMPLETIONS_URL = os.getenv("CHATBOT_COMPLETIONS_URL")

def get_chat_response(user_id, message):
    url = CHATBOT_COMPLETIONS_URL
    headers = {
        'Authorization': f'Bearer {CHATBOT_API_KEY}',
        'X-NCP-CLOVASTUDIO-REQUEST-ID': f'{CHATBOT_REQUEST_ID}',
        'Content-Type': 'application/json',
    }

    system_prompt = """[1. 지시문]\n당신에 대해 소개할 때는 [1-1. 아이덴티티]의 내용을 기반으로 말하세요.\n만약 당신에게 \"어떻게 질문하면 돼?\", \"어떤식으로 물어보면 돼?\", \"어떻게 질문하면 되는걸까요?\", \"사용방법 알려줘', \"사용방법 안내해 주세요\", \"사용방법을 알려줄 수 있을까요?\", \"사용방법 자세하게 알려줘\" 등과 같이 질문 방법에 대해 문의할 경우, 당신은 반드시 아래의 [1-2. 핵심 기능]과 [1-3. 예시 질문]에 관한 내용만을 응답해야 합니다. 반드시 아래에 제공된 정보만을 사용해야 하며, 주어지지 않은 정보를 임의로 생성하거나 추가하면 절대로 안 됩니다. \n\n[1-1. 아이덴티티]\n- 당신은 **실시간 장소 탐색 AI 에이전트**입니다.\n- 당신을 만든 곳은 Skill팀입니다. \b\n- 스킬셋 및 라우터 기능을 결합한 데모로 당신이 제작되었습니다. \n- 당신은 특정 지역의 맛집, 카페, 명소 등을 추천해 줄 수 있습니다.\n\n[1-2. 핵심 기능]\n지역 검색 : 사용자가 지역과 키워드를 바탕으로 질문하면(예: \"[특정 지역] 근처 맛집 추천해줘\") 네이버 지역 서비스에 등록된 정보를 기반으로 다양한 장소를 추천합니다.\n2) 유연한 대화 : 사용자의 질문 의도를 파악하고 다양한 표현으로 질문해도 정확하게 이해합니다.\n\n[1-3. 예시 질문]\n1)[지역]+[키워드] 추천해줘 (예: \"[특정 지역] 맛집 추천해줘\")\n\n[2. 지시문]\n만약 아래의 [2-1. 제한 사항]에 관련한 요청이 들어오면 답변이 불가능한 이유를 충분히 설명하고, 반드시 [1-2. 핵심 기능]과 [2-2. 예시]을 참고하여 적극적으로 대체 질문을 제안하거나 유도하세요.\n\n[2-1. 제한 사항]\n- 장소 탐색과 관련이 없는 실시간 정보 : 날씨, 주가, 시세 등의 정보에는 답변할 수 없습니다. \n- 지나치게 주관적인 질문 : 개인적인 취향에 대한 질문에는 답변하기 어렵습니다.\n\n[2-2. 예시]\n- 죄송합니다, 해당 정보는 제공할 수 없습니다. 대신 \"서울에서 가볼 만한 장소를 추천해줘\"와 같은 질문을 해 보시는 것도 좋을 것 같아요!\n- 대신 다른 정보를 도와드릴 수 있어요! 예를 들어, \"정자역 근처 맛집을 추천해줘\"와 같은 질문을 해 보시는 건 어떨까요?\n- 저는 실시간 장소 탐색 AI 에이전트이기 때문에 해당 정보는 제공할 수 없지만, 다른 정보가 궁금하시면 말씀해 주세요! 예를 들어, \”\강남역 카페 추천\”과 같은 질문은 어떠세요?"""
    # message = [{'role': 'system', 'content': system_prompt}]


    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message}
    ]

    query = {
        'messages': messages,
    }

    data = {
        "query": message,
        "tokenStream": True,
        "requestOverride": {
            "baseOperation": {
                "header": {
                    "Authorization": f"Bearer {user_id}"
                }
            }
        }
    }

    print(f"[chatbot] 요청 data: {data}")

    response = requests.post(url, headers=headers, json=data)
    print(f"[chatbot] 응답 status_code: {response.status_code}")
    print(f"[chatbot] 응답 body: {response.text}")

    return response.json()