import { ref } from 'vue'

// Глобальний стан
const products = ref([]) // <--- 1. ДОДАНО: Сховище для товарів
const categories = ref([])
const units = ref([])
const ingredients = ref([])
const consumables = ref([])
const processGroups = ref([])
const recipes = ref([])
const loading = ref(false)
const productRooms = ref([]) // <--- 2. ДОДАНО: Сховище для кімнат

export function useWarehouse() {

  // Перейменували на fetchWarehouseData для сумісності з компонентами
  const fetchWarehouseData = async () => {
    loading.value = true
    
    // Функція безпечного запиту
    const safeFetch = async (url) => {
      try {
        const res = await fetch(url)
        return res.ok ? await res.json() : []
      } catch (e) { 
        console.error(`Error fetching ${url}:`, e)
        return [] 
      }
    }

    console.log("🔄 Завантаження даних складу...")

    // Паралельне завантаження всіх довідників + ТОВАРІВ
    const results = await Promise.all([
      safeFetch('/api/categories/'),
      safeFetch('/api/units/'),
      safeFetch('/api/ingredients/'),
      safeFetch('/api/consumables/'),
      safeFetch('/api/processes/groups/'),
      safeFetch('/api/recipes/'),
      safeFetch('/api/products/'), // <--- 2. ДОДАНО: Запит на товари
      safeFetch('/api/product_rooms/') // <--- 3. ДОДАНО: Запит на кімнати

    ])

    // Розподіляємо результати
    categories.value = results[0]
    units.value = results[1]
    ingredients.value = results[2]
    consumables.value = results[3]
    processGroups.value = results[4]
    recipes.value = results[5]
    products.value = results[6] // <--- 3. ДОДАНО: Збереження товарів
    productRooms.value = results[7] // <--- 4. ДОДАНО: Збереження кімнат

    console.log(`✅ Дані оновлено. Товарів: ${products.value.length}`)
    
    loading.value = false
  }

  // Універсальна функція створення
  const createItem = async (url, payload, refreshFn = fetchWarehouseData) => {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        await refreshFn() // Оновлюємо списки
        return true
      }
      const err = await res.json()
      alert("Помилка: " + (err.detail || "Не вдалося створити"))
      return false
    } catch (e) { 
      console.error(e)
      return false 
    }
  }

  // Універсальна функція видалення
  const deleteItem = async (url, refreshFn = fetchWarehouseData) => {
    if(!confirm("Ви впевнені, що хочете видалити це?")) return
    try {
      await fetch(url, { method: 'DELETE' })
      await refreshFn()
    } catch (e) { console.error(e) }
  }

  // Універсальна функція оновлення (PUT)
  const updateItem = async (url, payload, refreshFn = fetchWarehouseData) => {
    try {
      const res = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (res.ok) {
        await refreshFn()
        return true
      }
      
      const err = await res.json()
      alert("Помилка оновлення: " + (err.detail || "Щось пішло не так"))
      return false
    } catch (e) {
      console.error(e)
      alert("Помилка мережі")
      return false
    }
  }

  // --- ШВИДКЕ КОРИГУВАННЯ ЗАЛИШКІВ (ІНВЕНТАРИЗАЦІЯ) ---
  const adjustItemStock = async (payload) => {
      try {
          const response = await fetch('/api/adjustments/', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json'
              },
              body: JSON.stringify(payload)
          })

          if (!response.ok) {
              const errData = await response.json()
              throw new Error(errData.detail || 'Помилка коригування залишку')
          }

          const result = await response.json()
            
          // 🔥 Автоматично оновлюємо всі дані складу, щоб нова цифра з'явилася на екрані
          await fetchWarehouseData() 
            
          return { success: true, data: result }
      } catch (err) {
          console.error("Помилка при коригуванні:", err)
          return { success: false, error: err.message }
      }
  }

  return {
    // Експортуємо products
    products, productRooms, categories, units, ingredients, consumables, processGroups, recipes, loading,
    // Експортуємо правильну назву функції
    fetchWarehouseData, 
    // Залишаємо стару назву як аліас про всяк випадок
    fetchData: fetchWarehouseData,
    createItem, deleteItem, updateItem, adjustItemStock
  }
}