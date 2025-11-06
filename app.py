import os, json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import numpy as np
from data import get_data
from flask_cors import CORS
import re

# === конфиг ===
load_dotenv()

# Получаем API ключ безопасно
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("⚠️ DEEPSEEK_API_KEY not found - using local logic")

df = get_data()
app = Flask(__name__)
CORS(app)  # Важно для Vercel!

def analyze_request_priority(user_request):
    """Определяет главный критерий в запросе"""
    request_lower = user_request.lower()
    
    category_keywords = ['десерт', 'салат', 'горячее', 'завтрак', 'основное', 'второе', 'паста', 'суп']
    nutrition_keywords = ['белк', 'калори', 'углевод', 'жир', 'диетич', 'калорий']
    
    has_category = any(word in request_lower for word in category_keywords)
    has_nutrition = any(word in request_lower for word in nutrition_keywords)
    
    if has_category and has_nutrition:
        if 'десерт' in request_lower or 'салат' in request_lower:
            return 'category_first'
        elif any(word in request_lower for word in ['белк', 'белки', 'протеин']):
            protein_match = re.search(r'(\d+)\s*г?р?а?м?м?\s*белк', request_lower)
            if protein_match:
                return 'nutrition_first'
        return 'category_first'
    elif has_category:
        return 'category_first'
    elif has_nutrition:
        return 'nutrition_first'
    else:
        return 'balanced'

def apply_nutrition_filters(df, request_lower):
    """Применяет nutritional фильтры"""
    filtered_df = df.copy()
    
    # Фильтры по белкам
    if 'много белков' in request_lower or 'высокий белок' in request_lower:
        filtered_df = filtered_df[filtered_df['proteins'] >= 25]
    elif 'белк' in request_lower:
        protein_match = re.search(r'(\d+)\s*г?р?а?м?м?\s*белк', request_lower)
        if protein_match:
            target_protein = int(protein_match.group(1))
            filtered_df = filtered_df[
                (filtered_df['proteins'] >= target_protein - 3) & 
                (filtered_df['proteins'] <= target_protein + 3)
            ]
    
    # Фильтры по калориям
    if 'мало калорий' in request_lower or 'низкокалорий' in request_lower:
        filtered_df = filtered_df[filtered_df['calories'] <= 350]
    elif 'много калорий' in request_lower or 'калорийн' in request_lower:
        filtered_df = filtered_df[filtered_df['calories'] >= 500]
    
    # Фильтры по углеводам
    if 'мало углеводов' in request_lower or 'низкоуглевод' in request_lower:
        filtered_df = filtered_df[filtered_df['carbs'] <= 20]
    elif 'много углеводов' in request_lower:
        filtered_df = filtered_df[filtered_df['carbs'] >= 40]
    
    return filtered_df

def smart_filter_with_priority(df, user_request):
    """Фильтрует с учетом приоритетов критериев"""
    priority = analyze_request_priority(user_request)
    request_lower = user_request.lower()
    
    # Вариант 1: Категория важнее
    if priority == 'category_first':
        category_df = df.copy()
        
        # Определяем категорию из запроса
        if 'десерт' in request_lower:
            category_df = df[df['category'] == 'десерт']
        elif 'салат' in request_lower:
            category_df = df[df['category'] == 'салат']
        elif 'горячее' in request_lower:
            category_df = df[df['category'] == 'горячее']
        elif 'завтрак' in request_lower:
            category_df = df[df['category'] == 'завтрак']
        
        # Пытаемся применить nutritional фильтры
        result_df = apply_nutrition_filters(category_df, request_lower)
        
        if len(result_df) == 0:
            return category_df, "no_nutrition_match"
        return result_df, "full_match"
    
    # Вариант 2: Nutrition важнее
    elif priority == 'nutrition_first':
        nutrition_df = apply_nutrition_filters(df, request_lower)
        
        # Пытаемся применить категорию
        if 'десерт' in request_lower:
            category_nutrition_df = nutrition_df[nutrition_df['category'] == 'десерт']
            if len(category_nutrition_df) > 0:
                return category_nutrition_df, "full_match"
        elif 'салат' in request_lower:
            category_nutrition_df = nutrition_df[nutrition_df['category'] == 'салат']
            if len(category_nutrition_df) > 0:
                return category_nutrition_df, "full_match"
        
        if len(nutrition_df) == 0:
            return df, "no_matches"
        return nutrition_df, "no_category_match"
    
    # Вариант 3: Сбалансированный подход
    else:
        result_df = apply_nutrition_filters(df, request_lower)
        if len(result_df) == 0:
            return df, "no_nutrition_match"
        return result_df, "full_match"

def create_smart_prompt(filtered_df, user_request, match_type):
    """Создает умный промпт для DeepSeek с учетом фильтрации"""
    
    if len(filtered_df) == 0:
        filtered_df = df
    
    dishes_info = []
    for _, dish in filtered_df.iterrows():
        dish_info = {
            "name": dish["name"],
            "category": dish["category"],
            "calories": dish["calories"],
            "proteins": dish["proteins"],
            "fats": dish["fats"],
            "carbs": dish["carbs"],
            "diet": dish["diet"],
            "tags": dish["tags"]
        }
        dishes_info.append(dish_info)
    
    context_messages = {
        "full_match": "✅ Найдены блюда, полностью соответствующие запросу пользователя.",
        "no_nutrition_match": "⚠️ Не найдено блюд с нужными nutritional параметрами в запрошенной категории. Показаны лучшие варианты из категории.",
        "no_category_match": "⚠️ Не найдено блюд нужной категории с указанными nutritional параметрами. Показаны лучшие варианты по nutritional критериям.",
        "no_matches": "❌ Не найдено блюд по критериям. Показано все меню."
    }
    
    prompt = f"""
Запрос пользователя: "{user_request}"
{context_messages[match_type]}

Доступные блюда (уже отфильтрованы под запрос):
{json.dumps(dishes_info, ensure_ascii=False, indent=2)}

ПРАВИЛА АНАЛИЗА NUTRITION:
- МАЛО калорий: до 350 ккал
- МНОГО калорий: от 500 ккал  
- МАЛО белков: до 15г
- МНОГО белков: от 25г
- МАЛО углеводов: до 20г
- МНОГО углеводов: от 40г

Верни JSON:
{{
    "choice": "название блюда",
    "reason": "подробное обоснование на русском с цифрами",
    "target_macros": {{
        "calories": число или null,
        "proteins": число или null, 
        "fats": число или null,
        "carbs": число или null
    }},
    "match_quality": "perfect|good|compromise" // perfect - все критерии, good - главные критерии, compromise - пришлось идти на уступки
}}

Если нет идеального соответствия - выбери лучший компромисс и честно объясни в reason.
"""
    return prompt

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
                "content": "Ты помощник по подбору блюд. Анализируй nutritional значения. Будь честен - если нет идеального match, так и скажи."
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
    """Умный выбор блюда через DeepSeek с приоритетами"""
    
    # Сначала применяем умную фильтрацию
    filtered_df, match_type = smart_filter_with_priority(df, free_text)
    
    # Создаем умный промпт
    prompt = create_smart_prompt(filtered_df, free_text, match_type)
    
    # Пытаемся использовать DeepSeek API
    if api_key:
        try:
            api_response = call_deepseek_api(prompt)
            if api_response and 'choices' in api_response:
                content = api_response['choices'][0]['message']['content']
                result = json.loads(content)
                
                # Проверяем, что выбранное блюдо есть в DataFrame
                if 'choice' in result and result['choice'] in df["name"].tolist():
                    print("✅ DeepSeek API успешно сработал!")
                    return result
        except Exception as e:
            print(f"❌ DeepSeek failed: {e}")
    
    # Локальная логика как запасной вариант
    print("🔄 Используем локальную логику")
    query_lower = free_text.lower()
    target_macros = {"calories": None, "proteins": None, "fats": None, "carbs": None}
    
    # Применяем ту же логику фильтрации для локального выбора
    if len(filtered_df) > 0:
        # Выбираем первое блюдо из отфильтрованного списка
        best_dish = filtered_df.iloc[0]
        reason = f"Подобрано по вашему запросу '{free_text}'"
        
        if match_type != "full_match":
            reason += " (найдено ближайшее соответствие)"
            
        return {
            "choice": best_dish["name"],
            "reason": reason,
            "target_macros": target_macros,
            "match_quality": "good" if match_type == "full_match" else "compromise"
        }
    else:
        # Полный фолбэк
        return {
            "choice": "Курица с овощами", 
            "reason": "Сбалансированное блюдо", 
            "target_macros": target_macros,
            "match_quality": "compromise"
        }

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
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response
    
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

        # Рекомендации
        recommendations = []
        dish_name = candidate["name"]
        
        if dish_name == "Курица с овощами":
            recommendations = ["Салат Цезарь", "Омлет с овощами"]
        elif dish_name == "Рыба на пару":
            recommendations = ["Гречка с мясом", "Салат Цезарь"]
        elif dish_name == "Гречка с мясом":
            recommendations = ["Рыба на пару", "Салат Цезарь"]
        elif dish_name == "Омлет с овощами":
            recommendations = ["Курица с овощами", "Салат Цезарь"]
        elif dish_name == "Салат Цезарь":
            recommendations = ["Курица с овощами", "Паста с томатами"]
        elif dish_name == "Паста с томатами":
            recommendations = ["Салат Цезарь", "Рыба на пару"]
        elif dish_name == "Сырники":
            recommendations = ["Медовик", "Омлет с овощами"]
        elif dish_name == "Картошка (десерт‑«Картошка»)":
            recommendations = ["Медовик", "Сырники"]
        elif dish_name == "Лазанья":
            recommendations = ["Гречка с мясом", "Паста с томатами"]
        elif dish_name == "Стейк с овощами":
            recommendations = ["Рыба на пару", "Салат Цезарь"]
        elif dish_name == "Чизкейк Нью‑Йорк":
            recommendations = ["Медовик", "Сырники"]
        elif dish_name == "Тирамису":
            recommendations = ["Чизкейк Нью‑Йорк", "Картошка (десерт‑«Картошка»)"]
        elif dish_name == "Паста Болоньезе":
            recommendations = ["Лазанья", "Стейк с овощами"]
        elif dish_name == "Салат греческий":
            recommendations = ["Салат Цезарь", "Омлет с овощами"]
        elif dish_name == "Мусс шоколадный":
            recommendations = ["Тирамису", "Чизкейк Нью‑Йорк"]
        elif dish_name == "Куриные крылышки BBQ":
            recommendations = ["Паста Болоньезе", "Салат греческий"]
        else:
            recommendations = ["Салат Цезарь", "Курица с овощами"]

        response = jsonify({
            "dish": candidate,
            "llm_choice": llm.get("choice"),
            "reason": llm.get("reason"),
            "used_target_macros": target,
            "match_quality": llm.get("match_quality", "good"),
            "recommendations": recommendations
        })
        
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    
    except Exception as e:
        print(f"❌ Error in recommend: {e}")
        return jsonify(error="Internal server error"), 500

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
