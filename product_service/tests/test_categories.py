import pytest
from sqlalchemy.exc import IntegrityError

def test_create_category_success(client):
    """
    Тест успішного створення категорії (з color замість icon).
    """
    payload = {
        "name": "Гарячі напої",
        "slug": "hot-drinks",
        "color": "#ff0000"  # Використовуємо реальне поле з твоєї моделі
    }
    response = client.post("/categories/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == payload["name"]
    assert data["slug"] == payload["slug"]
    assert data["color"] == payload["color"]
    assert "id" in data
    assert data["parent_id"] is None # За замовчуванням None

def test_create_subcategory(client):
    """
    Тест створення підкатегорії (використовуємо parent_id).
    """
    # 1. Створюємо батьківську
    parent_resp = client.post("/categories/", json={
        "name": "Напої", 
        "slug": "drinks", 
        "color": "#0000ff"
    })
    parent_id = parent_resp.json()["id"]

    # 2. Створюємо дочірню
    child_payload = {
        "name": "Кава",
        "slug": "coffee",
        "color": "#6f4e37",
        "parent_id": parent_id  # Прив'язуємо до батька
    }
    response = client.post("/categories/", json=child_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] == parent_id

def test_create_category_duplicate_slug(client):
    """
    Тест на унікальність slug.
    """
    payload = {
        "name": "Перша",
        "slug": "unique-slug",
        "color": "#ffffff"
    }
    client.post("/categories/", json=payload)
    
    # Очікуємо помилку IntegrityError при спробі створити дублікат
    with pytest.raises(IntegrityError):
        client.post("/categories/", json={
            "name": "Друга",
            "slug": "unique-slug",
            "color": "#000000"
        })

def test_update_category(client):
    """Тест оновлення."""
    # 1. Створили
    create_resp = client.post("/categories/", json={
        "name": "Old", "slug": "old", "color": "#111111"
    })
    cat_id = create_resp.json()["id"]

    # 2. Оновили
    update_payload = {
        "name": "New", "slug": "new", "color": "#222222"
    }
    response = client.put(f"/categories/{cat_id}", json=update_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New"
    assert data["color"] == "#222222"

def test_delete_category(client):
    """
    Тест видалення (перевірка через список).
    """
    # 1. Створили
    create_resp = client.post("/categories/", json={
        "name": "Delete Me", "slug": "del", "color": "#000000"
    })
    cat_id = create_resp.json()["id"]

    # 2. Видалили
    del_response = client.delete(f"/categories/{cat_id}")
    assert del_response.status_code == 200

    # 3. Перевіряємо, що категорії немає у загальному списку
    list_response = client.get("/categories/")
    all_categories = list_response.json()
    
    found_ids = [cat["id"] for cat in all_categories]
    assert cat_id not in found_ids