import pandas as pd

def get_data():
    dishes = [
        # name, category, diet, calories, proteins, fats, carbs, tags, image_url, recommendations
        ("Курица с овощами", "горячее", "обычное", 450, 35, 14, 40, "курица,без свинины,без остро", "https://img.freepik.com/free-photo/grilled-chicken-with-vegetables_140725-1687.jpg", "Салат Цезарь,Омлет с овощами"),
        ("Рыба на пару", "горячее", "диетическое", 220, 28, 6, 2, "рыба,легкое,без глютена", "https://img.freepik.com/free-photo/steamed-fish-with-herbs_1203-3583.jpg", "Гречка с мясом,Салат Цезарь"),
        ("Гречка с мясом", "горячее", "сытное", 520, 25, 12, 70, "говядина,сытно", "https://img.freepik.com/free-photo/buckwheat-with-meat-vegetables_140725-1623.jpg", "Рыба на пару,Омлет с овощами"),
        ("Омлет с овощами", "завтрак", "вегетарианское", 300, 18, 18, 8, "омлет,овощи", "https://img.freepik.com/free-photo/fluffy-omelette-with-vegetables_140725-1536.jpg", "Курица с овощами,Салат Цезарь"),
        ("Салат Цезарь", "салат", "обычное", 380, 24, 22, 20, "курица,салат", "https://img.freepik.com/free-photo/fresh-caesar-salad-with-chicken_140725-1582.jpg", "Курица с овощами,Паста с томатами"),
        ("Паста с томатами", "горячее", "вегетарианское", 430, 14, 12, 62, "паста,без свинины", "https://img.freepik.com/free-photo/pasta-with-tomato-sauce_140725-1468.jpg", "Салат Цезарь,Рыба на пару"),
    ]
    df = pd.DataFrame(dishes, columns=[
        "name", "category", "diet", "calories", "proteins", "fats", "carbs", "tags", "image_url", "recommendations"
    ])
    return df

def get_recommendations(dish_name, df):
    """Получить рекомендации для блюда"""
    try:
        dish_row = df[df["name"] == dish_name]
        if not dish_row.empty:
            recs = dish_row.iloc[0]["recommendations"]
            if pd.isna(recs) or not recs:
                return []
            return [rec.strip() for rec in recs.split(",")]
    except:
        pass
    return []
