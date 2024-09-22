from config import GPT_TOKEN, FOLDER_ID
import requests

def ask_gpt(collection):
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Api-Key {GPT_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 500
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты тренер, который отвечает на вопросы про спорт"
            }
        ]
    }

    for row in collection:
        content = row['content']

        data["messages"].append({
            "role": row["role"],
            "text": content
        })

    try:
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(url, headers=headers, json=data) as response:

        response = requests.post(url, headers=headers, json=data)
        result = response.json()['result']['alternatives'][0]['message']['text']
        #         if response.status != 200:
        #             result = f"Ошибка, задайте вопрос еще раз"
        #             return result
        #
        #         result = json.loads(await response.text())['result']['alternatives'][0]['message']['text']
    except Exception as e:
        result = "Произошла непредвиденная ошибка"
        print(e)
    return result