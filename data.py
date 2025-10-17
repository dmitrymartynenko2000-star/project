import pandas as pd

def get_data():
    dishes = [
        # name, category, diet, calories, proteins, fats, carbs, tags, image_url
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