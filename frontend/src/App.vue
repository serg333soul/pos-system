<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ProductCard from './components/ProductCard.vue'
import CartDrawer from './components/CartDrawer.vue'
import Warehouse from './components/Warehouse.vue'
import Statistics from './components/Statistics.vue'

// --- ЗМІННІ СТАНУ ---
const currentPage = ref('pos') // 'pos' (Каса) або 'warehouse' (Склад)

// Дані для каси
const products = ref([])
const loading = ref(true)
const error = ref(null)
const cartCount = ref(0)
const isCartOpen = ref(false)

// --- ЛОГІКА КАСИ (POS) ---

// 1. Завантаження товарів для продажу
const fetchProducts = async () => {
  try {
    // ВАЖЛИВО: Тут ми звертаємось до api/products (це йде на product_service)
    // Оскільки ми ще не зробили повноцінний список товарів в базі, 
    // цей запит може повернути пустий список, але помилки не буде.
    const res = await fetch('/api/products/') 
    if (res.ok) {
      products.value = await res.json()
    } else {
      // Тимчасова заглушка, якщо база пуста
      products.value = [] 
    }
  } catch (err) {
    error.value = "Не вдалося завантажити меню"
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 2. Оновлення лічильника кошика
const updateCartCount = async () => {
  try {
    const res = await fetch('/api/cart/')
    const cart = await res.json()
    // Парсимо в числа, щоб уникнути "0112"
    cartCount.value = Object.values(cart).reduce((sum, qty) => sum + parseInt(qty), 0)
  } catch (err) {
    console.error(err)
  }
}

// 3. Додавання в кошик
const addToCart = async (product) => {
  try {
    const res = await fetch(`/api/cart/${product.id}`, { method: 'POST' })
    if (res.ok) {
      await updateCartCount()
    }
  } catch (err) {
    console.error(err)
  }
}

// 4. Відкриття кошика
const openCart = () => {
  isCartOpen.value = true
}

// При старті
onMounted(() => {
  fetchProducts()
  updateCartCount()
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
    
    <Sidebar 
      :current-page="currentPage" 
      @change-page="(page) => currentPage = page" 
    />

    <main v-if="currentPage === 'pos'" class="flex-1 ml-64 flex flex-col h-screen relative">
      
      <header class="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gray-200 px-8 py-4 flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Меню</h2>
          <p class="text-sm text-gray-500">Оберіть товари для замовлення</p>
        </div>
        
        <button 
          @click="openCart"
          class="bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition shadow-lg flex items-center gap-3 active:scale-95">
          <i class="fas fa-shopping-cart"></i>
          <span>Кошик: {{ cartCount }}</span>
        </button>
      </header>

      <div class="p-8 overflow-y-auto flex-1 custom-scrollbar">
        <div v-if="loading" class="flex flex-col items-center justify-center h-64 text-gray-400">
          <i class="fas fa-circle-notch fa-spin text-3xl mb-4"></i>
          <p>Завантаження...</p>
        </div>

        <div v-else-if="products.length === 0" class="flex flex-col items-center justify-center h-64 text-gray-400">
          <i class="fas fa-mug-hot text-4xl mb-4 opacity-50"></i>
          <p>Меню поки порожнє. Додайте товари на Складі!</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <ProductCard 
            v-for="item in products" 
            :key="item.id" 
            :product="item" 
            @add-to-cart="addToCart(item)" 
          />
        </div>
      </div>

      <CartDrawer 
        :is-open="isCartOpen"
        :products="products"
        @close="isCartOpen = false"
        @clear-cart="updateCartCount"
      />
    </main>

    <Warehouse v-if="currentPage === 'warehouse'" />
    <Statistics v-if="currentPage === 'statistics'" />

  </div>
</template>

<style>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 20px; }
</style>