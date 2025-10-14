import tensorflow as tf
from flask import Flask, render_template, request, jsonify
from data import get_data
import numpy as np
import os

# Загружаем данные
df, label_encoder, scaler = get_data()

# Проверяем, существует ли файл модели
MODEL_PATH = "model.h5"

if os.path.exists(MODEL_PATH):
    # Если модель уже обучена и сохранена, загружаем её
    model = tf.keras.models.load_model(MODEL_PATH)
else:
    # Если модели нет, создаем и обучаем её
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(4,)),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(3, activation='softmax')  # 3 категории: среднее, диетическое, высококалорийное
    ])

    # Компиляция модели
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    # Обучаем модель на примере данных
    X = df[['calories', 'proteins', 'fats', 'carbs']].values
    y = df['category_encoded'].values
    model.fit(X, y, epochs=100, batch_size=2)

    # Сохраняем модель после обучения
    model.save(MODEL_PATH)

# Инициализируем Flask
app = Flask(__name__)


# Маршрут для главной страницы с формой
@app.route('/')
def home():
    return render_template('index.html')


# Роут для получения рекомендаций
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json
    query = data['query'].lower()  # Преобразуем запрос в нижний регистр

    # Простая логика поиска ключевых слов в запросе
    if 'курица' in query and 'овощи' in query:
        recommended_dish = {
            "name": "Курица с овощами",
            "description": "Сытное блюдо с курицей и овощами, идеально для обеда."
        }
    elif 'рыба' in query:
        recommended_dish = {
            "name": "Рыба на пару",
            "description": "Легкое и полезное блюдо с рыбой на пару, отличное для диеты."
        }
    elif 'гречка' in query:
        recommended_dish = {
            "name": "Гречка с мясом",
            "description": "Питательное блюдо с гречкой и мясом, с высоким содержанием белков."
        }
    else:
        recommended_dish = {
            "name": "Омлет с овощами",
            "description": "Легкий омлет с овощами — идеальный вариант для завтрака."
        }

    return jsonify({'dish': recommended_dish})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

