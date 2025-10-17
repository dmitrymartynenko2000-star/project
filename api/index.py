import os, json
from flask import Flask, request, jsonify
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Ваши данные блюд
def get_data():
    dishes = [
        ("Курица с овощами", "горячее", "обычное", 450, 35, 14, 40, "курица,без свинины,без остро", "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop"),
        ("Рыба на пару", "горячее", "диетическое", 220, 28, 6, 2, "рыба,легкое,без глютена", "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400&h=300&fit=crop"),
        ("Гречка с мясом", "горячее", "сытное", 520, 25, 12, 70, "говядина,сытно", "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=400&h=300&fit=crop"),
        ("Омлет с овощами", "завтрак", "вегетарианское", 300, 18, 18, 8, "омлет,овощи", "https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop"),
        ("Салат Цезарь", "салат", "обычное", 380, 24, 22, 20, "курица,салат", "https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400&h=300&fit=crop"),
        ("Паста с томатами", "горячее", "вегетарианское", 430, 14, 12, 62, "паста,без свинины", "https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?w=400&h=300&fit=crop"),
    ]
    df = pd.DataFrame(dishes, columns=[
        "name", "category", "diet", "calories", "proteins", "fats", "carbs", "tags", "image_url"
    ])
    return df

df = get_data()

def call_deepseek_api(prompt: str):
    """Вызов DeepSeek API"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
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
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
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
                    print("DeepSeek API успешно сработал!")
                    return result
        except Exception as e:
            print(f"DeepSeek failed: {e}")
    
    # Локальная логика как запасной вариант
    print("Используем локальную логику")
    query_lower = free_text.lower()
    target_macros = {"calories": None, "proteins": None, "fats": None, "carbs": None}
    
    if any(word in query_lower for word in ["диетич", "легк", "мало калорий"]):
        target_macros["calories"] = 250
        return {"choice": "Рыба на пару", "reason": "Диетическое блюдо с низкой калорийностью", "target_macros": target_macros}
    elif any(word in query_lower for word in ["белк", "протеин"]):
        target_macros["proteins"] = 30
        return {"choice": "Курица с овощами", "reason": "Богатое белком блюдо", "target_macros": target_macros}
    elif any(word in query_lower for word in ["углев", "энерги"]):
        target_macros["carbs"] = 50
        return {"choice": "Гречка с мясом", "reason": "Богатое углеводами для энергии", "target_macros": target_macros}
    elif any(word in query_lower for word in ["вегетариан", "без мяса"]):
        return {"choice": "Паста с томатами", "reason": "Вегетарианское блюдо", "target_macros": target_macros}
    else:
        return {"choice": "Курина с овощами", "reason": "Сбалансированное блюдо", "target_macros": target_macros}

def score_by_macros(row, target):
    score = 0.0
    for k in ("calories", "proteins", "fats", "carbs"):
        t = target.get(k)
        if t is None: continue
        try:
            diff = max(0.0, float(row[k]) - float(t))
            score += diff / (float(t) if float(t) > 0 else 1.0)
        except (ValueError, TypeError): continue
    return score

@app.route('/recommend', methods=['POST'])
def recommend():
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

        return jsonify({
            "dish": candidate,
            "llm_choice": llm.get("choice"),
            "reason": llm.get("reason"),
            "used_target_macros": target
        })
    
    except Exception as e:
        print(f"Error in recommend: {e}")
        return jsonify(error="Internal server error"), 500

# Vercel требует этот хендлер
def handler(request, context):
    return app(request, context)

if __name__ == "__main__":
    app.run(debug=True)