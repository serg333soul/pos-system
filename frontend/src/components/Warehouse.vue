<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('categories') // 'categories', 'units', 'ingredients', 'products'

// --- ДАНІ ---
const categories = ref([])
const units = ref([])
const ingredients = ref([])
const products = ref([]) // <--- НОВЕ: Список товарів
const loading = ref(false)

// --- ФОРМИ ---
const newCategory = ref({ name: '', slug: '' })
const newUnit = ref({ name: '', symbol: '' })
const newIngredient = ref({ name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 })

// <--- НОВЕ: Форма товару з рецептом
const newProduct = ref({
  name: '',
  price: 0,
  description: '',
  category_id: '',
  recipe: [] // Тут буде список: [{ ingredient_id: 5, quantity: 0.01 }, ...]
})

// --- ЗАВАНТАЖЕННЯ ДАНИХ ---
const fetchData = async () => {
  loading.value = true
  try {
    const [catRes, unitRes, ingRes, prodRes] = await Promise.all([
      fetch('/api/categories/'),
      fetch('/api/units/'),
      fetch('/api/ingredients/'),
      fetch('/api/products/') // <--- НОВЕ
    ])
    
    categories.value = await catRes.json()
    units.value = await unitRes.json()
    ingredients.value = await ingRes.json()
    products.value = await prodRes.json()
  } catch (err) {
    console.error("Помилка завантаження:", err)
  } finally {
    loading.value = false
  }
}

// --- ФУНКЦІЇ СТВОРЕННЯ ---
const createCategory = async () => {
  if (!newCategory.value.name) return
  await fetch('/api/categories/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newCategory.value)
  })
  newCategory.value = { name: '', slug: '' }
  fetchData()
}

const createUnit = async () => {
  if (!newUnit.value.name) return
  await fetch('/api/units/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newUnit.value)
  })
  newUnit.value = { name: '', symbol: '' }
  fetchData()
}

const createIngredient = async () => {
  if (!newIngredient.value.name || !newIngredient.value.unit_id) return
  await fetch('/api/ingredients/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newIngredient.value)
  })
  newIngredient.value = { name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 }
  fetchData()
}

// --- НОВЕ: ЛОГІКА ТОВАРІВ ---

// 1. Додати рядок у рецепт (візуально)
const addIngredientRow = () => {
  newProduct.value.recipe.push({ ingredient_id: '', quantity: 0 })
}

// 2. Видалити рядок з рецепта
const removeIngredientRow = (index) => {
  newProduct.value.recipe.splice(index, 1)
}

// 3. Зберегти товар
const createProduct = async () => {
  if (!newProduct.value.name || !newProduct.value.category_id) return alert("Вкажіть назву та категорію!")
  
  // Фільтруємо пусті рядки рецепта
  const cleanRecipe = newProduct.value.recipe.filter(r => r.ingredient_id && r.quantity > 0)
  
  const payload = { ...newProduct.value, recipe: cleanRecipe }

  const res = await fetch('/api/products/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  if (res.ok) {
    // Очищаємо форму
    newProduct.value = { name: '', price: 0, description: '', category_id: '', recipe: [] }
    fetchData()
  } else {
    alert("Помилка створення товару")
  }
}

// 4. Видалити товар (щоб почистити дублікати)
const deleteProduct = async (id) => {
  if(!confirm("Видалити цей товар?")) return
  // Оскільки ми ще не зробили DELETE в API product_service для products, 
  // це поки що не спрацює, але підготуємо UI.
  // Давай поки видалятимемо через базу, а тут просто заглушка.
  alert("Функція видалення скоро буде доступна!")
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-3xl font-bold text-gray-800">📦 Складський облік</h2>
        <p class="text-gray-500">Керування товарами, рецептами та сировиною</p>
      </div>
      <button @click="fetchData" class="text-blue-600 hover:bg-blue-50 p-2 rounded-full transition">
        <i class="fas fa-sync-alt" :class="{'fa-spin': loading}"></i>
      </button>
    </div>

    <div class="flex space-x-1 bg-gray-200 p-1 rounded-xl w-fit mb-8 overflow-x-auto">
      <button @click="activeTab = 'categories'" :class="activeTab === 'categories' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'" class="px-6 py-2 rounded-lg font-bold transition-all">Категорії</button>
      <button @click="activeTab = 'units'" :class="activeTab === 'units' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'" class="px-6 py-2 rounded-lg font-bold transition-all whitespace-nowrap">Одиниці вим.</button>
      <button @click="activeTab = 'ingredients'" :class="activeTab === 'ingredients' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'" class="px-6 py-2 rounded-lg font-bold transition-all">Інгредієнти</button>
      <button @click="activeTab = 'products'" :class="activeTab === 'products' ? 'bg-white text-purple-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'" class="px-6 py-2 rounded-lg font-bold transition-all">Товари та Рецепти</button>
    </div>

    <div v-if="activeTab === 'categories'" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 class="font-bold mb-4 text-gray-700">Список категорій</h3>
        <ul>
          <li v-for="c in categories" :key="c.id" class="flex justify-between border-b py-3">
            <span>{{ c.name }}</span>
            <span class="bg-gray-100 text-xs px-2 py-1 rounded text-gray-500">{{ c.slug }}</span>
          </li>
        </ul>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
        <h3 class="font-bold mb-4">Нова категорія</h3>
        <input v-model="newCategory.name" class="w-full border p-2 rounded mb-2" placeholder="Назва">
        <input v-model="newCategory.slug" class="w-full border p-2 rounded mb-4" placeholder="Slug">
        <button @click="createCategory" class="w-full bg-blue-600 text-white py-2 rounded font-bold">Додати</button>
      </div>
    </div>

    <div v-if="activeTab === 'units'" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
         <h3 class="font-bold mb-4 text-gray-700">Одиниці виміру</h3>
         <ul>
          <li v-for="u in units" :key="u.id" class="flex justify-between border-b py-3">
            <span>{{ u.name }}</span>
            <span class="font-bold text-green-600">{{ u.symbol }}</span>
          </li>
        </ul>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
        <h3 class="font-bold mb-4">Нова одиниця</h3>
        <input v-model="newUnit.name" class="w-full border p-2 rounded mb-2" placeholder="Назва">
        <input v-model="newUnit.symbol" class="w-full border p-2 rounded mb-4" placeholder="Символ">
        <button @click="createUnit" class="w-full bg-blue-600 text-white py-2 rounded font-bold">Додати</button>
      </div>
    </div>

    <div v-if="activeTab === 'ingredients'" class="grid grid-cols-1 xl:grid-cols-3 gap-8">
      <div class="xl:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <table class="w-full text-left">
          <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr><th class="p-4">Назва</th><th class="p-4 text-right">Ціна/од</th><th class="p-4 text-right">Залишок</th></tr>
          </thead>
          <tbody>
            <tr v-for="i in ingredients" :key="i.id" class="border-b hover:bg-gray-50">
              <td class="p-4">{{ i.name }}</td>
              <td class="p-4 text-right">{{ i.cost_per_unit }} ₴</td>
              <td class="p-4 text-right font-bold" :class="i.stock_quantity > 0 ? 'text-green-600':'text-red-500'">
                {{ i.stock_quantity }} {{ i.unit?.symbol }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
        <h3 class="font-bold mb-4">Новий інгредієнт</h3>
        <input v-model="newIngredient.name" class="w-full border p-2 rounded mb-2" placeholder="Назва">
        <select v-model="newIngredient.unit_id" class="w-full border p-2 rounded mb-2 bg-white">
          <option value="" disabled>Одиниця...</option>
          <option v-for="u in units" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
        <div class="grid grid-cols-2 gap-2 mb-4">
          <input v-model="newIngredient.cost_per_unit" type="number" placeholder="Ціна" class="border p-2 rounded">
          <input v-model="newIngredient.stock_quantity" type="number" placeholder="Залишок" class="border p-2 rounded">
        </div>
        <button @click="createIngredient" class="w-full bg-orange-500 text-white py-2 rounded font-bold">Додати</button>
      </div>
    </div>

    <div v-if="activeTab === 'products'" class="grid grid-cols-1 xl:grid-cols-3 gap-8 animate-fade-in">
      
      <div class="xl:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <table class="w-full text-left">
          <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th class="p-4">Назва</th>
              <th class="p-4">Категорія</th>
              <th class="p-4 text-right">Ціна</th>
              <th class="p-4 text-center">Дії</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in products" :key="p.id" class="border-b hover:bg-gray-50">
              <td class="p-4 font-bold">{{ p.name }}</td>
              <td class="p-4 text-sm text-gray-500">
                {{ p.category ? p.category.name : 'Без категорії' }}
              </td>
              <td class="p-4 text-right font-mono">{{ p.price }} ₴</td>
              <td class="p-4 text-center">
                <button @click="deleteProduct(p.id)" class="text-red-400 hover:text-red-600 transition">
                  <i class="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bg-white p-6 rounded-2xl shadow-sm border border-purple-100 h-fit border-2">
        <h3 class="text-lg font-bold mb-4 text-purple-700 flex items-center gap-2">
          <i class="fas fa-magic"></i> Створити товар
        </h3>
        
        <div class="space-y-3">
          <div>
            <label class="text-xs font-bold text-gray-400 uppercase">Назва</label>
            <input v-model="newProduct.name" type="text" placeholder="Напр: Лате XL" class="w-full border p-2 rounded mt-1">
          </div>
          
          <div class="grid grid-cols-2 gap-3">
             <div>
                <label class="text-xs font-bold text-gray-400 uppercase">Категорія</label>
                <select v-model="newProduct.category_id" class="w-full border p-2 rounded mt-1 bg-white">
                  <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
             </div>
             <div>
                <label class="text-xs font-bold text-gray-400 uppercase">Ціна продажу</label>
                <input v-model="newProduct.price" type="number" class="w-full border p-2 rounded mt-1 text-right">
             </div>
          </div>

          <div class="pt-4 border-t border-dashed">
            <label class="text-xs font-bold text-purple-600 uppercase mb-2 block">Технологічна карта (Рецепт)</label>
            
            <div v-for="(row, index) in newProduct.recipe" :key="index" class="flex gap-2 mb-2 items-center">
              <select v-model="row.ingredient_id" class="flex-1 border p-2 rounded bg-gray-50 text-sm">
                <option value="" disabled>Сировина...</option>
                <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">
                  {{ ing.name }}
                </option>
              </select>
              
              <input v-model="row.quantity" type="number" step="0.001" placeholder="Кіл-ть" class="w-20 border p-2 rounded text-sm text-right">
              
              <button @click="removeIngredientRow(index)" class="text-red-400 hover:text-red-600 px-1">
                <i class="fas fa-times"></i>
              </button>
            </div>

            <button @click="addIngredientRow" class="text-sm text-purple-600 font-bold hover:underline mt-1">
              + Додати інгредієнт
            </button>
          </div>

          <button @click="createProduct" class="w-full bg-purple-600 text-white py-3 rounded-xl font-bold hover:bg-purple-700 transition mt-4 shadow-lg shadow-purple-200">
            Зберегти товар
          </button>
        </div>
      </div>

    </div>

  </div>
</template>