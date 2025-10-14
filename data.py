import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Пример данных о блюдах (название, калории, белки, жиры, углеводы, категория)
def get_data():
    data = [
        {'name': 'Курица с картошкой', 'calories': 450, 'proteins': 30, 'fats': 15, 'carbs': 50, 'category': 'среднее'},
        {'name': 'Омлет с овощами', 'calories': 350, 'proteins': 20, 'fats': 20, 'carbs': 10, 'category': 'диетическое'},
        {'name': 'Гречка с мясом', 'calories': 500, 'proteins': 25, 'fats': 10, 'carbs': 60, 'category': 'высококалорийное'},
        {'name': 'Рыба на пару', 'calories': 200, 'proteins': 25, 'fats': 5, 'carbs': 0, 'category': 'диетическое'}
    ]

    # Преобразуем данные в DataFrame
    df = pd.DataFrame(data)

    # Преобразуем категорию блюда в числовое значение
    label_encoder = LabelEncoder()
    df['category_encoded'] = label_encoder.fit_transform(df['category'])

    # Стандартизируем числовые параметры КБЖУ
    scaler = StandardScaler()
    df[['calories', 'proteins', 'fats', 'carbs']] = scaler.fit_transform(df[['calories', 'proteins', 'fats', 'carbs']])

    # Возвращаем обработанные данные
    return df, label_encoder, scaler
