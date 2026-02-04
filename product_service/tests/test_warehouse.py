import pytest

def test_create_unit(client):
    """
    Тест створення одиниці виміру (Unit).
    Перевіряємо поля name та symbol.
    """
    payload = {
        "name": "Кілограм",
        "symbol": "кг"
    }
    response = client.post("/units/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Кілограм"
    assert data["symbol"] == "кг"
    assert "id" in data

def test_create_ingredient_simple(client):
    """
    Базовий тест створення інгредієнта (без категорії).
    """
    # 1. Створюємо Unit (бо без нього не можна)
    unit_resp = client.post("/units/", json={"name": "Літр", "symbol": "л"})
    unit_id = unit_resp.json()["id"]

    # 2. Створюємо Ingredient
    payload = {
        "name": "Молоко 3.2%",
        "cost_per_unit": 45.50,
        "stock_quantity": 10.0,
        "unit_id": unit_id
        # category_id не передаємо (він Optional)
    }
    response = client.post("/ingredients/", json=payload)

    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Молоко 3.2%"
    assert data["unit_id"] == unit_id
    assert data["stock_quantity"] == 10.0
    # Перевіряємо, що cost_per_unit зберігся (float)
    assert float(data["cost_per_unit"]) == 45.50

def test_create_ingredient_with_category(client):
    """
    Тест створення інгредієнта, прив'язаного до категорії.
    Це важливо для сортування на складі.
    """
    # 1. Створюємо Unit
    u_resp = client.post("/units/", json={"name": "Штука", "symbol": "шт"})
    unit_id = u_resp.json()["id"]

    # 2. Створюємо Category (для інгредієнтів)
    c_resp = client.post("/categories/", json={
        "name": "Овочі", 
        "slug": "vegetables",
        "color": "#00ff00"
    })
    cat_id = c_resp.json()["id"]

    # 3. Створюємо Ingredient з category_id
    payload = {
        "name": "Авокадо",
        "cost_per_unit": 35.0,
        "stock_quantity": 50,
        "unit_id": unit_id,
        "category_id": cat_id 
    }
    response = client.post("/ingredients/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == cat_id
    
    # Якщо твій бекенд підтримує вкладеність (lazy loading), 
    # можна перевірити, чи повернулась назва категорії, але це опціонально
    # assert data["category"]["name"] == "Овочі"

def test_ingredient_validation(client):
    """
    Перевірка обов'язкових полів.
    """
    # Спроба створити без unit_id
    payload_bad = {
        "name": "Повітря",
        "cost_per_unit": 0,
        "stock_quantity": 0
    }
    response = client.post("/ingredients/", json=payload_bad)
    assert response.status_code == 422  # Validation Error

def test_list_ingredients(client):
    """
    Перевірка отримання списку інгредієнтів.
    """
    # Підготовка даних
    u_resp = client.post("/units/", json={"name": "Грам", "symbol": "г"})
    uid = u_resp.json()["id"]
    
    client.post("/ingredients/", json={
        "name": "Сіль", "cost_per_unit": 0.1, "stock_quantity": 1000, "unit_id": uid
    })
    client.post("/ingredients/", json={
        "name": "Цукор", "cost_per_unit": 0.15, "stock_quantity": 2000, "unit_id": uid
    })

    # Отримання списку
    response = client.get("/ingredients/")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 2
    names = [i["name"] for i in data]
    assert "Сіль" in names
    assert "Цукор" in names