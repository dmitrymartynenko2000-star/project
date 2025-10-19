import pandas as pd

def get_data():
    dishes = [
        # name, category, diet, calories, proteins, fats, carbs, tags, image_url, recommendations
        ("Курица с овощами", "горячее", "обычное", 450, 35, 14, 40, "курица,без свинины,без остро", "https://img.iamcook.ru/old/upl/recipes/cat/u1378-b97469a2dddc017b00c8aacc4957cf14.jpg", "Салат Цезарь,Омлет с овощами"),
        ("Рыба на пару", "горячее", "диетическое", 220, 28, 6, 2, "рыба,легкое,без глютена", "https://prostokvashino.ru/upload/resize_cache/iblock/370/800_800_0/3706c5d808e12659543fe4306c52eb23.jpg", "Гречка с мясом,Салат Цезарь"),
        ("Гречка с мясом", "горячее", "сытное", 520, 25, 12, 70, "говядина,сытно", "https://img.povar.ru/mobile/5a/cc/22/2d/grechka_s_myasom-868085.JPG", "Рыба на пару,Омлет с овощами"),
        ("Омлет с овощами", "завтрак", "вегетарианское", 300, 18, 18, 8, "омлет,овощи", "https://images.gastronom.ru/HGWEXxM5PcNnoMdU5TdvCHfTsApQ7XJflntpnlJBTwU/pr:recipe-cover-image/g:ce/rs:auto:0:0:0/L2Ntcy9hbGwtaW1hZ2VzLzY3YzMyNjNlLTRiYzItNDcyNC1iYTkwLTdmOTY3NmI1YjRhNy5qcGc.webp", "Курица с овощами,Салат Цезарь"),
        ("Салат Цезарь", "салат", "обычное", 380, 24, 22, 20, "курица,салат", "https://static.1000.menu/img/content-v2/eb/79/19516/salat-cezar-klassicheskii-s-kuricei_1611309331_16_max.jpg", "Курица с овощами,Паста с томатами"),
        ("Паста с томатами", "горячее", "вегетарианское", 430, 14, 12, 62, "паста,без свинины", "https://lifehacker.ru/wp-content/uploads/2020/01/shutterstock_1315335506-1_1589978896.jpg", "Салат Цезарь,Рыба на пару"),
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
