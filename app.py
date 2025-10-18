import os, json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import numpy as np
from data import get_data, get_recommendations

# === конфиг ===
load_dotenv()

# Используем API ключ из переменных окружения
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("DEEPSEEK_API_KEY not found in environment variables")

df = get_data()

app = Flask(__name__, template_folder="templates", static_folder="static")


def call_deepseek_api(prompt: str):
    """
    Вызов официального DeepSeek API
    """
    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": """Ты помощник по подбору блюд. Ты должен выбрать ОДНО блюдо из предоставленного списка и вернуть ответ в формате JSON. 
Формат ответа: {"choice": "название блюда", "reason": "обоснование выбора", "target_macros": {"calories": число или null, "proteins": число или null, "fats": число или null, "carbs": число или null}}
Если пользователь указывает предпочтения по КБЖУ, учти их в target_macros."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при вызове DeepSeek API: {e}")
        print(f"Ответ API: {response.text if 'response' in locals() else 'Нет ответа'}")
        return None
@app.route("/recommend", methods=["POST", "OPTIONS"])
def recommend():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    
    try:
        payload = request.get_json(force=True)
        query = (payload.get("query") or "").strip()
        if not query:
            return jsonify(error="empty query"), 400

        llm = llm_pick_dish(query)
        chosen_name = llm.get("choice")
        target = llm.get("target_macros") or {}

        # Находим блюдо в каталоге
        if chosen_name in set(df["name"]):
            candidate = df[df["name"] == chosen_name].iloc[0].to_dict()
        else:
            candidate = df.iloc[0].to_dict()

        # Уточняем по КБЖУ если нужно
        if any(v not in (None, "") for v in target.values()):
            scored = [(score_by_macros(row, target), row.to_dict()) for _, row in df.iterrows()]
            scored.sort(key=lambda x: x[0])
            candidate = scored[0][1]

        # Получаем рекомендации
        recommendations = get_recommendations(candidate["name"], df)
        
        return jsonify({
            "dish": candidate,
            "llm_choice": llm.get("choice"),
            "reason": llm.get("reason"),
            "used_target_macros": target,
            "recommendations": recommendations  # Добавляем рекомендации
        })
    
    except Exception as e:
        print(f"❌ Error in recommend: {e}")
        return jsonify(error="Internal server error"), 500


def llm_pick_dish(free_text: str):
    """
    Просим модель выбрать РОВНО ОДНО блюдо из имеющихся
    """
    dish_names = df["name"].tolist()
    dishes_str = "\n".join([f"- {name}" for name in dish_names])

    prompt = f"""
Пользователь сказал: "{free_text}"

Доступные блюда:
{dishes_str}

Выбери ОДНО самое подходящее блюдо из списка выше. 
Учти диетические предпочтения пользователя.

Верни ответ ТОЛЬКО в формате JSON:
{{
    "choice": "название выбранного блюда",
    "reason": "обоснование выбора на русском",
    "target_macros": {{
        "calories": число или null,
        "proteins": число или null, 
        "fats": число или null,
        "carbs": число или null
    }}
}}
"""

    try:
        api_response = call_deepseek_api(prompt)
        if api_response and 'choices' in api_response:
            content = api_response['choices'][0]['message']['content']
            print(f"Ответ от DeepSeek: {content}")  # Для отладки
            result = json.loads(content)

            # Валидация результата
            if 'choice' not in result:
                result['choice'] = dish_names[0]
            if 'reason' not in result:
                result['reason'] = "Автоматический выбор"
            if 'target_macros' not in result:
                result['target_macros'] = {}

            return result
        else:
            print("Неверный ответ от API")
            raise Exception("Неверный ответ от API")

    except Exception as e:
        print(f"Ошибка при обработке ответа DeepSeek: {e}")
        return {
            "choice": dish_names[0],
            "reason": "Автоматический выбор из-за ошибки",
            "target_macros": {"calories": None, "proteins": None, "fats": None, "carbs": None}
        }


def score_by_macros(row, target):
    """Штраф за превышение целевых КБЖУ (если заданы). Меньше — лучше."""
    score = 0.0
    for k in ("calories", "proteins", "fats", "carbs"):
        t = target.get(k)
        if t is None:
            continue
        try:
            diff = max(0.0, float(row[k]) - float(t))  # штраф только за превышение
            score += diff / (float(t) if float(t) > 0 else 1.0)
        except (ValueError, TypeError):
            continue
    return score


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    payload = request.get_json(force=True)
    query = (payload.get("query") or "").strip()
    if not query:
        return jsonify(error="empty query"), 400

    # Deep Seek выбирает блюдо
    llm = llm_pick_dish(query)
    chosen_name = llm.get("choice")
    target = llm.get("target_macros") or {}

    # Находим в каталоге
    candidate = None
    if chosen_name in set(df["name"]):
        candidate = df[df["name"] == chosen_name].iloc[0].to_dict()
    else:
        candidate = df.iloc[0].to_dict()

    # Если заданы КБЖУ — выбираем ближайшее
    if any(v not in (None, "") for v in
           (target.get("calories"), target.get("proteins"), target.get("fats"), target.get("carbs"))):
        scored = []
        for _, row in df.iterrows():
            s = score_by_macros(row, target)
            scored.append((s, row.to_dict()))
        scored.sort(key=lambda x: x[0])
        candidate = scored[0][1]

    return jsonify({
        "dish": candidate,
        "llm_choice": llm.get("choice"),
        "reason": llm.get("reason"),
        "used_target_macros": target
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
