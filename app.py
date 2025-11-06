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

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("⚠️ DEEPSEEK_API_KEY not found - using local logic")

df = get_data()
app = Flask(__name__)
CORS(app)

def get_nutrition_rules(category):
    """Возвращает nutritional правила в зависимости от категории блюда"""
    if category == 'десерт':
        return {
            'low_calories': 350,      # для десертов мало - до 350 (Сырники 320)
            'high_calories': 400,     # для десертов много - от 400 (Тирамису 460, Чизкейк 420)
            'low_proteins': 6,        # для десертов мало белков - до 6г (Мусс 6, Картошка 5)
            'high_proteins': 10,      # для десертов много белков - от 10г (Сырники 12)
            'low_carbs': 35,          # для десертов мало углеводов - до 35г
            'high_carbs': 38          # для десертов много углеводов - от 38г (Тирамису 38, Картошка 47)
        }
    else:
        return {
            'low_calories': 350,      # для основных блюд мало - до 350
            'high_calories': 500,     # для основных блюд много - от 500 (Лазанья 600, Стейк 550)
            'low_proteins': 15,       # для основных блюд мало белков - до 15г
            'high_proteins': 25,      # для основных блюд много белков - от 25г (Курица 35, Стейк 40)
            'low_carbs': 20,          # для основных блюд мало углеводов - до 20г
            'high_carbs': 40          # для основных блюд много углеводов - от 40г
        }

def apply_nutrition_filters(df, request_lower):
    """Применяет nutritional фильтры с ЖЕСТКОЙ привязкой к категории"""
    filtered_df = df.copy()
    
    # ЖЕСТКО определяем категорию из запроса
    target_category = None
    if 'десерт' in request_lower:
        target_category = 'десерт'
        filtered_df = filtered_df[filtered_df['category'] == 'десерт']
    elif 'салат' in request_lower:
        target_category = 'main'
        filtered_df = filtered_df[filtered_df['category'] == 'салат']
    elif 'горячее' in request_lower:
        target_category = 'main'
        filtered_df = filtered_df[filtered_df['category'] == 'горячее']
    elif 'завтрак' in request_lower:
        target_category = 'main'
        filtered_df = filtered_df[filtered_df['category'] == 'завтрак']
    
    # Если указана категория, применяем фильтры ТОЛЬКО в пределах этой категории
    if target_category:
        rules = get_nutrition_rules(target_category)
        
        # Фильтры по белкам
        if 'много белков' in request_lower or 'высокий белок' in request_lower:
            filtered_df = filtered_df[filtered_df['proteins'] >= rules['high_proteins']]
        elif 'мало белков' in request_lower or 'низкий белок' in request_lower:
            filtered_df = filtered_df[filtered_df['proteins'] <= rules['low_proteins']]
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
            filtered_df = filtered_df[filtered_df['calories'] <= rules['low_calories']]
        elif 'много калорий' in request_lower or 'калорийн' in request_lower:
            filtered_df = filtered_df[filtered_df['calories'] >= rules['high_calories']]
        
        # Фильтры по углеводам
        if 'мало углеводов' in request_lower or 'низкоуглевод' in request_lower:
            filtered_df = filtered_df[filtered_df['carbs'] <= rules['low_carbs']]
        elif 'много углеводов' in request_lower:
            filtered_df = filtered_df[filtered_df['carbs'] >= rules['high_carbs']]
    
    return filtered_df

def smart_filter_with_priority(df, user_request):
    """Фильтрует с ЖЕСТКОЙ привязкой к категории - ВСЕГДА возвращает результат"""
    request_lower = user_request.lower()
    
    # Сначала жестко фильтруем по категории если указана
    filtered_df = apply_nutrition_filters(df, request_lower)
    
    # ГАРАНТИЯ: Если после фильтрации ничего не осталось, но категория указана - возвращаем ВСЕ блюда этой категории
    if len(filtered_df) == 0:
        if 'десерт' in request_lower:
            filtered_df = df[df['category'] == 'десерт']
            return filtered_df, "no_nutrition_match"
        elif 'салат' in request_lower:
            filtered_df = df[df['category'] == 'салат']
            return filtered_df, "no_nutrition_match"
        elif 'горячее' in request_lower:
            filtered_df = df[df['category'] == 'горячее']
            return filtered_df, "no_nutrition_match"
        elif 'завтрак' in request_lower:
            filtered_df = df[df['category'] == 'завтрак']
            return filtered_df, "no_nutrition_match"
    
    # ГАРАНТИЯ: Если категория не указана, но есть nutritional фильтры и ничего не найдено
    if any(word in request_lower for word in ['белк', 'калори', 'углевод', 'жир']):
        if len(filtered_df) == 0:
            # Возвращаем лучшее блюдо по общим критериям
            return df, "no_matches"
        return filtered_df, "full_match"
    
    # ГАРАНТИЯ: Если вообще нет критериев или ничего не найдено
    if len(filtered_df) == 0:
        return df, "no_matches"
    
    return filtered_df, "full_match"

def create_smart_prompt(filtered_df, user_request, match_type):
    """Создает умный промпт для DeepSeek с учетом фильтрации"""
    
    # ГАРАНТИЯ: Всегда есть блюда для выбора
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
    
    # Получаем правила для разных категорий
    dessert_rules = get_nutrition_rules('десерт')
    main_rules = get_nutrition_rules('main')
    
    context_messages = {
        "full_match": "✅ Найдены блюда, полностью соответствующие запросу пользователя.",
        "no_nutrition_match": "⚠️ Не найдено блюд с нужными nutritional параметрами в запрошенной категории. Показаны ВСЕ блюда из этой категории.",
        "no_matches": "❌ Не найдено блюд по критериям. Показаны лучшие варианты из всего меню."
    }
    
    prompt = f"""
Запрос пользователя: "{user_request}"
{context_messages[match_type]}

Доступные блюда (уже отфильтрованы под запрос, ВСЕГДА есть хотя бы одно блюдо):
{json.dumps(dishes_info, ensure_ascii=False, indent=2)}

ВАЖНОЕ ПРАВИЛО: ЕСЛИ В ЗАПРОСЕ УКАЗАНА КАТЕГОРИЯ (десерт/салат/горячее/завтрак) - ВЫБИРАЙ ТОЛЬКО ИЗ ЭТОЙ КАТЕГОРИИ!

РАЗНЫЕ ПРАВИЛА ДЛЯ РАЗНЫХ КАТЕГОРИЙ:

ДЛЯ ДЕСЕРТОВ:
- МАЛО калорий: до {dessert_rules['low_calories']} ккал (Сырники {320})
- МНОГО калорий: от {dessert_rules['high_calories']} ккал (Тирамису {460}, Чизкейк {420})  
- МАЛО белков: до {dessert_rules['low_proteins']}г (Мусс {6}, Картошка {5})
- МНОГО белков: от {dessert_rules['high_proteins']}г (Сырники {12})

ДЛЯ ОСНОВНЫХ БЛЮД (горячее, салаты, завтраки):
- МАЛО калорий: до {main_rules['low_calories']} ккал (Рыба {220}, Омлет {300})
- МНОГО калорий: от {main_rules['high_calories']} ккал (Лазанья {600}, Стейк {550})  
- МАЛО белков: до {main_rules['low_proteins']}г
- МНОГО белков: от {main_rules['high_proteins']}г (Курица {35}, Стейк {40})

Верни JSON:
{{
    "choice": "название блюда",
    "reason": "подробное обоснование на русском с цифрами. ЕСЛИ УКАЗАНА КАТЕГОРИЯ - ВЫБИРАЙ ТОЛЬКО ИЗ НЕЁ! Всегда выбирай конкретное блюдо.",
    "target_macros": {{
        "calories": число или null,
        "proteins": число или null, 
        "fats": число или null,
        "carbs": число или null
    }},
    "match_quality": "perfect|good|compromise"
}}

ЖЕСТКИЕ ПРАВИЛА:
1. Если в запросе есть "десерт" - выбирай ТОЛЬКО из десертов
2. Если в запросе есть "салат" - выбирай ТОЛЬКО из салатов  
3. Если в запросе есть "горячее" - выбирай ТОЛЬКО из горячих блюд
4. Если в запросе есть "завтрак" - выбирай ТОЛЬКО из завтраков
5. ВСЕГДА выбирай конкретное блюдо - никогда не возвращай пустой результат
6. Если нет идеального match - выбери лучший вариант из доступных и объясни почему
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
                "content": "Ты помощник по подбору блюд. Учитывай что для десертов и основных блюд разные nutritional нормы. ВСЕГДА выбирай конкретное блюдо - никогда не возвращай пустой результат."
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
    """Умный выбор блюда через DeepSeek - ВСЕГДА возвращает результат"""
    
    # Сначала применяем умную фильтрацию (гарантирует хотя бы одно блюдо)
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
                
                # ГАРАНТИЯ: Проверяем что выбранное блюдо есть в DataFrame
                if 'choice' in result and result['choice'] in df["name"].tolist():
                    print("✅ DeepSeek API успешно сработал!")
                    return result
                else:
                    # Если DeepSeek вернул несуществующее блюдо, выбираем первое из filtered_df
                    fallback_dish = filtered_df.iloc[0]
                    print("⚠️ DeepSeek вернул несуществующее блюдо, используем fallback")
                    return {
                        "choice": fallback_dish["name"],
                        "reason": f"Подобрано по вашему запросу '{free_text}' (автоматический выбор)",
                        "target_macros": {"calories": None, "proteins": None, "fats": None, "carbs": None},
                        "match_quality": "good"
                    }
        except Exception as e:
            print(f"❌ DeepSeek failed: {e}")
    
    # Локальная логика как запасной вариант - ВСЕГДА работает
    print("🔄 Используем локальную логику")
    query_lower = free_text.lower()
    
    # ГАРАНТИЯ: Всегда есть filtered_df с хотя бы одним блюдом
    if 'десерт' in query_lower:
        dessert_df = filtered_df[filtered_df['category'] == 'десерт']
        if len(dessert_df) == 0:
            dessert_df = df[df['category'] == 'десерт']  # Fallback на все десерты
        
        if 'много калорий' in query_lower:
            # Для десертов много калорий - от 400
            high_cal_desserts = dessert_df[dessert_df['calories'] >= 400]
            if len(high_cal_desserts) > 0:
                best_dish = high_cal_desserts.iloc[0]
            else:
                best_dish = dessert_df.iloc[0]  # Берем первый десерт если нет высококалорийных
        elif 'мало калорий' in query_lower:
            # Для десертов мало калорий - до 350
            low_cal_desserts = dessert_df[dessert_df['calories'] <= 350]
            if len(low_cal_desserts) > 0:
                best_dish = low_cal_desserts.iloc[0]
            else:
                best_dish = dessert_df.iloc[0]  # Берем первый десерт если нет низкокалорийных
        elif 'много белков' in query_lower:
            # Для десертов много белков - от 10г
            high_protein_desserts = dessert_df[dessert_df['proteins'] >= 10]
            if len(high_protein_desserts) > 0:
                best_dish = high_protein_desserts.iloc[0]
            else:
                best_dish = dessert_df.iloc[0]  # Берем первый десерт если нет белковых
        else:
            best_dish = dessert_df.iloc[0]  # Просто первый десерт
        
        return {
            "choice": best_dish["name"],
            "reason": f"Десерт '{best_dish['name']}' ({best_dish['calories']} ккал, {best_dish['proteins']}г белка)",
            "target_macros": {"calories": None, "proteins": None, "fats": None, "carbs": None},
            "match_quality": "good"
        }
    
    # ГАРАНТИЯ: Если дошли сюда - берем первое блюдо из filtered_df (оно всегда есть)
    best_dish = filtered_df.iloc[0]
    reason = f"Подобрано по вашему запросу '{free_text}'"
    
    if match_type != "full_match":
        reason += " (найдено ближайшее соответствие)"
        
    return {
        "choice": best_dish["name"],
        "reason": reason,
        "target_macros": {"calories": None, "proteins": None, "fats": None, "carbs": None},
        "match_quality": "good" if match_type == "full_match" else "compromise"
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

        # ГАРАНТИЯ: llm_pick_dish ВСЕГДА возвращает результат
        llm = llm_pick_dish(query)
        chosen_name = llm.get("choice")
        target = llm.get("target_macros") or {}

        # ГАРАНТИЯ: Находим блюдо в каталоге (если почему-то нет, берем первое)
        if chosen_name in set(df["name"]):
            candidate = df[df["name"] == chosen_name].iloc[0].to_dict()
        else:
            candidate = df.iloc[0].to_dict()
            print(f"⚠️ Блюдо '{chosen_name}' не найдено, используем первое из меню")

        # Уточняем по КБЖУ если нужно
        if any(v not in (None, "") for v in target.values()):
            scored = [(score_by_macros(row, target), row.to_dict()) for _, row in df.iterrows()]
            scored.sort(key=lambda x: x[0])
            candidate = scored[0][1]

        # Рекомендации
        recommendations = []
        dish_name = candidate["name"]
        
        # ... (твоя существующая логика рекомендаций)
        
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
        # ГАРАНТИЯ: Даже при ошибке возвращаем какое-то блюдо
        fallback_dish = df.iloc[0].to_dict()
        response = jsonify({
            "dish": fallback_dish,
            "llm_choice": fallback_dish["name"],
            "reason": "Произошла ошибка, но мы подобрали для вас это блюдо",
            "used_target_macros": {},
            "match_quality": "compromise",
            "recommendations": []
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
