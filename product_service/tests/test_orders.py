import pytest
from sqlalchemy.orm import Session
import models  # Імпортуємо моделі напряму для налаштування меню

def setup_menu(db: Session):
    """
    Допоміжна функція, яка наповнює 'віртуальне кафе' товарами та техкартами.
    Ми робимо це напряму через DB, щоб ізолювати тест замовлень від тестів адмінки.
    """
    # 1. Створюємо Одиниці та Інгредієнти
    unit_ml = models.Unit(name="Мілілітри", symbol="мл")
    unit_pcs = models.Unit(name="Штуки", symbol="шт")
    db.add_all([unit_ml, unit_pcs])
    db.commit()

    # Склад: 5 літрів молока, 100 стаканчиків
    milk = models.Ingredient(name="Молоко", unit_id=unit_ml.id, stock_quantity=5000, cost_per_unit=0.05)
    cup = models.Consumable(name="Стакан XL", unit_id=unit_pcs.id, stock_quantity=100, cost_per_unit=2.0)
    db.add_all([milk, cup])
    db.commit()

    # 2. Створюємо Категорію та Товар
    category = models.Category(name="Кава", slug="coffee", color="#000000")
    db.add(category)
    db.commit()

    product = models.Product(
        name="Капучино", 
        category_id=category.id, 
        price=0, # Ціна буде на варіантах
        is_active=True
    )
    db.add(product)
    db.commit()

    # 3. Створюємо Варіант (XL) - Ціна 70 грн
    variant_xl = models.ProductVariant(
        product_id=product.id,
        name="XL 400ml",
        price=70.0,
        sku="CAP-XL"
    )
    db.add(variant_xl)
    db.commit()

    # 4. Створюємо Техкарту (Зв'язки)
    # Капучино XL витрачає: 300 мл молока
    recipe_milk = models.ProductVariantIngredient(
        variant_id=variant_xl.id,
        ingredient_id=milk.id,
        quantity=300 # 300 мл на порцію
    )
    db.add(recipe_milk)
    db.commit()

    # ... і можливо витрачає 1 стаканчик (якщо у вас є логіка прив'язки Consumables до товару)
    # Поки що тестуємо тільки інгредієнти, як найскладнішу частину.

    return {
        "product_id": product.id,
        "variant_id": variant_xl.id,
        "ingredient_id": milk.id,
        "consumable_id": cup.id
    }

def test_create_order_zero_trust(client, db_session):
    """
    ГОЛОВНИЙ ТЕСТ: Перевірка розрахунку ціни та списання складу.
    """
    # 1. Підготовка даних (наповнюємо БД)
    menu = setup_menu(db_session)
    
    # 2. Емуляція запиту від Фронтенду (ZERO TRUST - ми не шлемо ціну)
    # Замовляємо 2 великих Капучино
    payload = {
        "payment_method": "cash",
        "items": [
            {
                "product_id": menu["product_id"],
                "variant_id": menu["variant_id"],
                "quantity": 2, # Дві порції
                "modifiers": []
            }
        ]
    }

    # 3. Виконуємо запит
    response = client.post("/orders/", json=payload)
    
    # 4. Перевірки
    assert response.status_code == 200, f"Помилка замовлення: {response.text}"
    order_data = response.json()

    # А. Перевірка грошей
    # 2 порції * 70 грн = 140 грн
    # Якщо бекенд повертає total_amount в response:
    if "total_amount" in order_data:
        assert order_data["total_amount"] == 140.0
    
    # Б. Перевірка запису в БД (для надійності)
    order_id = order_data["id"]
    db_order = db_session.query(models.Order).filter(models.Order.id == order_id).first()
    assert db_order is not None
    assert db_order.total_amount == 140.0
    assert db_order.status == "completed" # або "new", залежно від вашої логіки

    # В. КРИТИЧНО: Перевірка списання зі складу
    # Було 5000 мл. Витратили: 2 порції * 300 мл = 600 мл.
    # Має залишитися: 4400 мл.
    milk = db_session.query(models.Ingredient).filter(models.Ingredient.id == menu["ingredient_id"]).first()
    
    assert milk.stock_quantity == 4400.0, f"Склад не списався! Очікували 4400, маємо {milk.stock_quantity}"

def test_order_validation_stock(client, db_session):
    """
    Тест: чи дозволить система продати, якщо товару недостатньо на складі?
    """
    menu = setup_menu(db_session)
    
    # Встановлюємо малий залишок молока (тільки 100 мл)
    milk = db_session.query(models.Ingredient).filter(models.Ingredient.id == menu["ingredient_id"]).first()
    milk.stock_quantity = 100 
    db_session.commit()

    # Спроба замовити Капучино XL (треба 300 мл)
    payload = {
        "payment_method": "card",
        "items": [
            {
                "product_id": menu["product_id"],
                "variant_id": menu["variant_id"],
                "quantity": 1
            }
        ]
    }

    response = client.post("/orders/", json=payload)

    # Тут залежить від бізнес-логіки:
    # Варіант А: 400 Bad Request (Недостатньо інгредієнтів)
    # Варіант Б: 200 OK (Продати в мінус)
    # Зазвичай у POS дозволяють продавати в мінус, але ми перевіримо, як налаштовано у тебе.
    
    if response.status_code == 400:
        assert "недостатньо" in response.text.lower()
    elif response.status_code == 200:
        # Якщо дозволено мінус, перевіряємо, що стало -200
        db_session.refresh(milk)
        assert milk.stock_quantity == -200.0