import os, json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
from config import Config

from data import get_data

# === конфиг ===
load_dotenv()  # возьмёт OPENAI_API_KEY из .env локально
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # для Vercel добавь Env Var в проекте
api_key = Config.OPENAI_API_KEY
client = OpenAI(api_key=api_key)

df = get_data()  # твой каталог блюд

app = Flask(__name__, template_folder="templates", static_folder="static")

def llm_pick_dish(free_text: str):
    """
    Просим модель выбрать РОВНО ОДНО блюдо из имеющихся,
    возвращая JSON {choice: <name>, reason: <string>, target_macros?: {...}}
    """
    dish_names = df["name"].tolist()

    system = (
        "Ты помощник ресторана. Пользователь пишет свободным текстом. "
        "Твоя задача: понять запрос и выбрать ОДНО блюдо из данного списка. "
        "Учитывай вкусы, ограничения (без свинины/рыба/вегетарианское/острое), цель по калориям и КБЖУ, если они упомянуты. "
        "Если блюдо из списка не подходит, выбери наиболее близкое. "
        "Ответ строго в JSON без лишнего текста."
    )
    schema_hint = (
        "Формат ответа:\n"
        "{\n"
        '  "choice": "<точное_название_блюда_из_списка>",\n'
        '  "reason": "<краткое объяснение>",\n'
        '  "target_macros": {"calories": null|number, "proteins": null|number, "fats": null|number, "carbs": null|number}\n'
        "}\n"
    )
    user = (
        f"Список блюд: {dish_names}. Запрос пользователя: {free_text}\n"
        f"{schema_hint}"
        "Если нет КБЖУ в тексте — ставь null. Возвращай валидный JSON."
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user}
        ]
    )
    txt = resp.choices[0].message.content.strip()
    # Подстраховка: вытаскиваем JSON
    try:
        start = txt.find("{")
        end = txt.rfind("}") + 1
        data = json.loads(txt[start:end])
    except Exception:
        # падать нельзя — вернём дефолт
        data = {"choice": dish_names[0], "reason":"дефолтный выбор", "target_macros": {"calories": None, "proteins": None, "fats": None, "carbs": None}}
    return data

def score_by_macros(row, target):
    """Штраф за превышение целевых КБЖУ (если заданы). Меньше — лучше."""
    score = 0.0
    for k in ("calories","proteins","fats","carbs"):
        t = target.get(k)
        if t is None:
            continue
        diff = max(0.0, row[k] - float(t))  # штраф только за превышение
        score += diff / (t if t else 1.0)
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

    # 1) ChatGPT выбирает блюдо по имени (из списка)
    llm = llm_pick_dish(query)
    chosen_name = llm.get("choice")
    target = llm.get("target_macros") or {}

    # 2) Находим в каталоге и при необходимости доуточняем по КБЖУ
    if chosen_name in set(df["name"]):
        candidate = df[df["name"] == chosen_name].iloc[0].to_dict()
    else:
        candidate = df.iloc[0].to_dict()

    # 3) Если заданы КБЖУ — среди всех блюд выбираем ближайшее (мягкая проверка)
    if any(v not in (None, "") for v in (target.get("calories"), target.get("proteins"), target.get("fats"), target.get("carbs"))):
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
