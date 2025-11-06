import pandas as pd

def get_data():
    dishes = [
        # Существующие блюда
        ("Курица с овощами", "горячее", "обычное", 450, 35, 14, 40, 450,
         "курица,без свинины,без остро",
         "https://img.iamcook.ru/old/upl/recipes/cat/u1378-b97469a2dddc017b00c8aacc4957cf14.jpg",
         "Салат Цезарь,Омлет с овощами"),
        ("Рыба на пару", "горячее", "диетическое", 220, 28, 6, 2, 380,
         "рыба,легкое,без глютена",
         "https://prostokvashino.ru/upload/resize_cache/iblock/370/800_800_0/3706c5d808e12659543fe4306c52eb23.jpg",
         "Гречка с мясом,Салат Цезарь"),
        ("Гречка с мясом", "горячее", "сытное", 520, 25, 12, 70, 320,
         "говядина,сытно",
         "https://img.povar.ru/mobile/5a/cc/22/2d/grechka_s_myasom-868085.JPG",
         "Рыба на пару,Салат Цезарь"),
        ("Омлет с овощами", "завтрак", "вегетарианское", 300, 18, 18, 8, 280,
         "омлет,овощи",
         "https://images.gastronom.ru/HGWEXxM5PcNnoMdU5TdvCHfTsApQ7XJflntpnlJBTwU/pr:recipe-cover-image/g:ce/rs:auto:0:0:0/L2Ntcy9hbGwtaW1hZ2VzLzY3YzMyNjNlLTRiYzItNDcyNC1iYTkwLTdmOTY3NmI1YjRhNy5qcGc.webp",
         "Курица с овощами,Салат Цезарь"),
        ("Салат Цезарь", "салат", "обычное", 380, 24, 22, 20, 350,
         "курица,салат",
         "https://images.gastronom.ru/-UHzDgNx-m0MMa6OR0ilz2qP7MB0mKQeGceObc9jpck/pr:recipe-cover-image/g:ce/rs:auto:0:0:0/L2Ntcy9hbGwtaW1hZ2VzLzVhNzFhZGY1LTM3MTYtNDlmMy04NDNlLTAwMTg4MGNiM2E0OS5qcGc.webp",
         "Курица с овощами,Паста с томатами"),
        ("Паста с томатами", "горячее", "вегетарианское", 430, 14, 12, 62, 420,
         "паста,без свинины",
         "https://lifehacker.ru/wp-content/uploads/2020/01/shutterstock_1315335506-1_1589978896.jpg",
         "Салат Цезарь,Рыба на пару"),

        # Новые блюда + десерты
        ("Сырники", "десерт", "вегетарианское", 320, 12, 10, 38, 280,
         "творог,жаренные,завтрак",
         "https://static.nv.ua/shared/system/MediaPhoto/images/000/475/411/original/77820e781064bb7ac2a07a0bbd4d7d5d.png",
         "Чизкейк Нью-Йорк,Омлет с овощами"),
        ("Картошка (десерт)", "десерт", "обычное", 380, 5, 18, 47, 220,
         "пирожное,бисквит,какао",
         "https://sladkiexroniki.ru/wp-content/uploads/2015/08/pirozhnom-kartoshka-po-gostu-sssr.jpg",
         "Тирамису,Сырники"),
        ("Лазанья", "горячее", "сытное", 600, 30, 28, 55, 580,
         "паста,мясо,сыр",
         "https://avatars.mds.yandex.net/get-vertis-journal/3911415/d9d13368-8493-4c8c-b2f1-51874751fe3d.jpeg/1600x1600",
         "Гречка с мясом,Паста с томатами"),
        ("Стейк с овощами", "горячее", "обычное", 550, 40, 22, 12, 890,
         "говядина,овощи,без углеводов",
         "https://alimero.ru/uploads/images/00/84/33/2016/07/21/bd3ce8_wmark.jpg",
         "Рыба на пару,Салат Цезарь"),

        # Дополнительные блюда
        ("Чизкейк Нью-Йорк", "десерт", "вегетарианское", 420, 7, 26, 34, 350,
         "чизкейк,творог,печенье",
         "https://annatomilchik.ru/wp-content/uploads/2021/07/chizkejk-nyu-jork.jpg",
         "Тирамису,Сырники"),
        ("Тирамису", "десерт", "обычное", 460, 8, 28, 38, 320,
         "тирамису,какао,кофе",
         "https://icdn.lenta.ru/images/2024/06/28/12/20240628123130464/wide_16_9_3e207633180b39e720c3f4c4fd23364e.jpg",
         "Чизкейк Нью-Йорк,Картошка (десерт)"),
        ("Паста Болоньезе", "горячее", "сытное", 580, 20, 22, 70, 480,
         "паста,говядина,томат",
         "https://primebeef.ru/images/cms/data/blog/284716036_6_1000x700_combino-spaghetti-1-kg-spagetti-barilla-1kg-barilla-n-5-v-nalichii-_rev023.jpg",
         "Лазанья,Стейк с овощами"),
        ("Салат греческий", "салат", "вегетарианское", 340, 10, 18, 28, 320,
         "салат,фета,оливки",
         "https://hoff.ru/upload/medialibrary/d94/5q86zk61fdvuks4g1ecs5sv3yg5rsh88.jpg",
         "Салат Цезарь,Омлет с овощами"),
        ("Мусс шоколадный", "десерт", "обычное", 390, 6, 24, 40, 290,
         "шоколад,сливки,десерт",
         "https://recipes.av.ru//media/recipes/100384_picture_CPkIZei.jpg",
         "Тирамису,Чизкейк Нью-Йорк"),
        ("Куриные крылышки BBQ", "горячее", "обычное", 510, 30, 28, 35, 420,
         "курица,BBQ,закуска",
         "https://the-challenger.ru/wp-content/uploads/2018/11/Hischnik_Kurinie_krylia-800x534.jpg",
         "Паста Болоньезе,Салат греческий"),
    ]

    df = pd.DataFrame(dishes, columns=[
        "name", "category", "diet", "calories",
        "proteins", "fats", "carbs", "price",
        "tags", "image_url", "recommendations"
    ])
    return df

# Пример использования
if __name__ == "__main__":
    df = get_data()
    print(df)
    print(f"\nВсего блюд: {len(df)}")
    print(f"Категории: {df['category'].unique()}")
    print(f"Десерты: {df[df['category'] == 'десерт']['name'].tolist()}")
