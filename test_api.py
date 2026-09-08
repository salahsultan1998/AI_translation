import requests

API = "http://127.0.0.1:8000"
HEADERS = {
    "X-API-Key": "LOCATOOL_API_KEY",
    "Content-Type": "application/json",
}


source_list = ["开始游戏", "欢迎我们的指挥官", "金币不足", "主城装饰：1级"]

payload = {
    "game_id": "S06",
    "target_language": "English",
    "model":"google/gemini-3.7-flash",
    "texts": [{"id": str(i), "source_text": text} for i, text in enumerate(source_list)],
}

response = requests.post(
    f"{API}/v1/translate",
    headers=HEADERS,
    json=payload,
    timeout=120,
)

response.raise_for_status()
data = response.json()

# print(data)
for trans in data["translations"]:
    print(f"ID: {trans['id']}, Source: {trans['source_text']}, Translated: {trans['translated_text']}")