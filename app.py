import os, json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import numpy as np
from data import get_data
from flask_cors import CORS

# === конфиг ===
load_dotenv()

# Получаем API ключ безопасно
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("⚠️ DEEPSEEK_API_KEY not found - using local logic")

df = get_data()
app = Flask(__name__)
CORS(app)  # Важно для Vercel!

def call_deepseek_api(prompt: str):
    """Вызов DeepSeek API"""
    if not api_key:
        return None
        
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
                "content": "Ты помощник по подбору блюд. Верни JSON: {choice: 'название', reason: 'текст', target_macros: {calories: число или null, proteins: число или null, fats: число или null, carbs: число или null}}"
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return None

def llm_pick_dish(free_text: str):
    """Выбор блюда через DeepSeek или локальную логику"""
    dish_names = df["name"].tolist()
    
    # Пытаемся использовать DeepSeek API
    if api_key:
        dishes_str = "\n".join([f"- {name}" for name in dish_names])
        prompt = f"""
Пользователь: "{free_text}"

Доступные блюда:
{dishes_str}

Выбери ОДНО блюдо и верни JSON:
{{
    "choice": "название блюда",
    "reason": "обоснование на русском",
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
                result = json.loads(content)
                
                if 'choice' in result and result['choice'] in dish_names:
                    print("✅ DeepSeek API успешно сработал!")
                    return result
        except Exception as e:
            print(f"❌ DeepSeek failed: {e}")
    
    # Локальная логика как запасной вариант
    print("🔄 Используем локальную логику")
    query_lower = free_text.lower()
    target_macros = {"calories": None, "proteins": None, "fats": None, "carbs": None}
    
    if any(word in query_lower for word in ["диетич", "легк", "мало калорий", "низкокалорий"]):
        target_macros["calories"] = 250
        return {"choice": "Рыба на пару", "reason": "Диетическое блюдо с низкой калорийностью", "target_macros": target_macros}
    elif any(word in query_lower for word in ["белк", "протеин", "много белка"]):
        target_macros["proteins"] = 30
        return {"choice": "Курица с овощами", "reason": "Богатое белком блюдо", "target_macros": target_macros}
    elif any(word in query_lower for word in ["углев", "карб", "энерги"]):
        target_macros["carbs"] = 50
        return {"choice": "Гречка с мясом", "reason": "Богатое углеводами для энергии", "target_macros": target_macros}
    elif any(word in query_lower for word in ["вегетариан", "без мяса"]):
        return {"choice": "Паста с томатами", "reason": "Вегетарианское блюдо", "target_macros": target_macros}
    elif any(word in query_lower for word in ["завтрак", "омлет"]):
        return {"choice": "Омлет с овощами", "reason": "Идеально для завтрака", "target_macros": target_macros}
    elif any(word in query_lower for word in ["салат", "свеж"]):
        return {"choice": "Салат Цезарь", "reason": "Свежий и легкий салат", "target_macros": target_macros}
    else:
        return {"choice": "Курица с овощами", "reason": "Сбалансированное блюдо", "target_macros": target_macros}

def score_by_macros(row, target):
    """Штраф за превышение целевых КБЖУ"""
    score = 0.0
    for k in ("calories", "proteins", "fats", "carbs"):
        t = target.get(k)
        if t is None: continue
        try:
            diff = max(0.0, float(row[k]) - float(t))
            score += diff / (float(t) if float(t) > 0 else 1.0)
        except (ValueError, TypeError): continue
    return score

@app.route("/")
def home():
    return render_template("index.html")

# ТОЛЬКО ОДИН endpoint /recommend!
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

        # Получаем рекомендации (простая версия без ML)
        recommendations = []
        if candidate["name"] == "Курица с овощами":
            recommendations = ["Салат Цезарь", "Омлет с овощами"]
        elif candidate["name"] == "Рыба на пару":
            recommendations = ["Гречка с мясом", "Салат Цезарь"]
        elif candidate["name"] == "Гречка с мясом":
            recommendations = ["Рыба на пару", "Омлет с овощами"]
        elif candidate["name"] == "Омлет с овощами":
            recommendations = ["Курица с овощами", "Салат Цезарь"]
        elif candidate["name"] == "Салат Цезарь":
            recommendations = ["Курица с овощами", "Паста с томатами"]
        elif candidate["name"] == "Паста с томатами":
            recommendations = ["Салат Цезарь", "Рыба на пару"]
        
        return jsonify({
            "dish": candidate,
            "llm_choice": llm.get("choice"),
            "reason": llm.get("reason"),
            "used_target_macros": target,
            "recommendations": recommendations
        })
    
    except Exception as e:
        print(f"❌ Error in recommend: {e}")
        return jsonify(error="Internal server error"), 500

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
