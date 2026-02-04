import pytest

def test_create_consumable_basic(client):
    """
    Тест створення простого витратного матеріалу (наприклад, серветки).
    Перевіряємо, що stock_quantity приймає int.
    """
    # 1. Створюємо Unit (пачка)
    u_resp = client.post("/units/", json={"name": "Пачка", "symbol": "пач"})
    unit_id = u_resp.json()["id"]

    # 2. Створюємо витратний матеріал
    payload = {
        "name": "Серветки білі",
        "cost_per_unit": 25.00,
        "stock_quantity": 100,  # Integer
        "unit_id": unit_id
    }
    response = client.post("/consumables/", json=payload)

    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Серветки білі"
    assert data["stock_quantity"] == 100
    assert isinstance(data["stock_quantity"], int)
    assert data["unit_id"] == unit_id

def test_create_consumable_with_category(client):
    """
    Тест створення витратного матеріалу з категорією (наприклад, "Упаковка").
    """
    # 1. Створюємо Unit (штука)
    u_resp = client.post("/units/", json={"name": "Штука", "symbol": "шт"})
    unit_id = u_resp.json()["id"]

    # 2. Створюємо Категорію
    c_resp = client.post("/categories/", json={
        "name": "Упаковка", 
        "slug": "packaging", 
        "color": "#cccccc"
    })
    cat_id = c_resp.json()["id"]

    # 3. Створюємо Consumable
    payload = {
        "name": "Стакан паперовий 350мл",
        "cost_per_unit": 2.50,
        "stock_quantity": 500,
        "unit_id": unit_id,
        "category_id": cat_id
    }
    response = client.post("/consumables/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["category_id"] == cat_id
    # Перевірка зв'язку
    assert data["name"] == "Стакан паперовий 350мл"

def test_update_consumable_stock(client):
    """
    Тест зміни залишків (інвентаризація).
    """
    # Створюємо
    u_resp = client.post("/units/", json={"name": "шт", "symbol": "шт"})
    unit_id = u_resp.json()["id"]
    
    create_resp = client.post("/consumables/", json={
        "name": "Трубочки",
        "cost_per_unit": 0.1,
        "stock_quantity": 1000,
        "unit_id": unit_id
    })
    consumable_id = create_resp.json()["id"]

    # Оновлюємо (наприклад, приїхала нова партія)
    update_payload = {
        "name": "Трубочки",
        "cost_per_unit": 0.12, # ціна змінилася
        "stock_quantity": 2000, # кількість змінилася
        "unit_id": unit_id
    }
    response = client.put(f"/consumables/{consumable_id}", json=update_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["stock_quantity"] == 2000
    assert data["cost_per_unit"] == 0.12

def test_delete_consumable(client):
    """
    Тест видалення витратного матеріалу.
    """
    # Створюємо
    u_resp = client.post("/units/", json={"name": "шт", "symbol": "шт"})
    create_resp = client.post("/consumables/", json={
        "name": "Видали мене",
        "cost_per_unit": 1,
        "stock_quantity": 1,
        "unit_id": u_resp.json()["id"]
    })
    c_id = create_resp.json()["id"]

    # Видаляємо
    del_resp = client.delete(f"/consumables/{c_id}")
    assert del_resp.status_code == 200

    # Перевіряємо через список
    list_resp = client.get("/consumables/")
    ids = [item["id"] for item in list_resp.json()]
    assert c_id not in ids