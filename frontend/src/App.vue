<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ProductCard from './components/ProductCard.vue'
import CartDrawer from './components/CartDrawer.vue'
import Warehouse from './components/Warehouse.vue'
import Statistics from './components/Statistics.vue'
import Customers from './components/Customers.vue'
import ProductModal from './components/ProductModal.vue' // <--- ІМПОРТ

const currentPage = ref('pos')
const products = ref([])
const loading = ref(true)
const cartCount = ref(0)
const isCartOpen = ref(false)

// Стан модального вікна
const isModalOpen = ref(false)
const selectedProduct = ref(null)

const fetchProducts = async () => {
  try {
    const res = await fetch('/api/products/') 
    if (res.ok) products.value = await res.json()
    else products.value = [] 
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const updateCartCount = async () => {
  try {
    const res = await fetch('/api/cart/')
    const cart = await res.json()
    cartCount.value = Object.values(cart).reduce((sum, qty) => sum + parseInt(qty), 0)
  } catch (err) { console.error(err) }
}

// --- ЛОГІКА ВІДКРИТТЯ ТОВАРУ ---
const handleProductClick = (product) => {
  // Якщо товар має варіанти АБО групи модифікаторів -> відкриваємо вікно
  if (product.has_variants || (product.modifier_groups && product.modifier_groups.length > 0)) {
    selectedProduct.value = product
    isModalOpen.value = true
  } else {
    // Якщо простий товар - додаємо відразу
    addToCart({ 
        product_id: product.id, 
        quantity: 1
    })
  }
}

// --- ДОДАВАННЯ В КОШИК (СКЛАДНИЙ ТОВАР) ---
const handleModalAddToCart = async (payload) => {
    // payload приходить з ProductModal
    const cartItem = {
        product_id: payload.product.id,
        variant_id: payload.variant_id,
        modifiers: payload.modifiers,
        quantity: 1
    }
    await addToCart(cartItem)
}

// Універсальна функція API
const addToCart = async (payload) => {
  try {
    // Для простого додавання нам треба змінити API cart endpoint, 
    // АЛЕ поки що у нас order_service простий (Redis hash).
    // Тимчасово ми будемо використовувати стару логіку для лічильника, 
    // але Order Service треба буде оновити, щоб він зберігав варіанти в Redis.
    // Поки що ми просто робимо POST на /cart/{id} для сумісності з лічильником,
    // АЛЕ реальні дані для чекауту ми будемо збирати в Frontend CartDrawer.
    // (Це спрощення для поточного етапу, ідеально - Redis має зберігати JSON об'єкт)
    
    // Щоб не ускладнювати зараз Order Service, ми зробимо хитрість:
    // Ми будемо додавати в Redis просто ID товару (для лічильника),
    // А деталі варіантів зберігатимемо в LocalStorage на фронті (або передаватимемо в Order Service розширений об'єкт).
    
    // ДЛЯ ЗАРАЗ: Використовуємо старий ендпоінт для підрахунку кількості
    const res = await fetch(`/api/cart/${payload.product_id}`, { method: 'POST' })
    
    // ВАЖЛИВО: Оскільки Order Service (Redis) зараз тупий і зберігає тільки ID=QTY,
    // він не розрізнить "250г" і "500г". 
    // ДЛЯ ПОВНОЦІННОЇ РОБОТИ нам треба оновити CartDrawer, щоб він зберігав складні об'єкти.
    // Давай зробимо це наступним кроком. Поки що - просто оновлюємо лічильник.
    
    if (res.ok) await updateCartCount()
    
  } catch (err) { console.error(err) }
}

onMounted(() => {
  fetchProducts()
  updateCartCount()
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
    <Sidebar :current-page="currentPage" @change-page="(page) => currentPage = page" />

    <main v-if="currentPage === 'pos'" class="flex-1 ml-64 flex flex-col h-screen relative">
      <header class="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gray-200 px-8 py-4 flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Меню</h2>
          <p class="text-sm text-gray-500">Оберіть товари для замовлення</p>
        </div>
        <button @click="isCartOpen = true" class="bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition shadow-lg flex items-center gap-3 active:scale-95">
          <i class="fas fa-shopping-cart"></i> <span>Кошик: {{ cartCount }}</span>
        </button>
      </header>

      <div class="p-8 overflow-y-auto flex-1 custom-scrollbar">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <ProductCard 
            v-for="item in products" 
            :key="item.id" 
            :product="item" 
            @click="handleProductClick(item)" 
          />
        </div>
      </div>

      <CartDrawer 
        :is-open="isCartOpen"
        :products="products"
        @close="isCartOpen = false"
        @clear-cart="updateCartCount"
      />
      
      <ProductModal 
        :is-open="isModalOpen"
        :product="selectedProduct"
        @close="isModalOpen = false"
        @add-to-cart="handleModalAddToCart"
      />
    </main>

    <Warehouse v-if="currentPage === 'warehouse'" />
    <Statistics v-if="currentPage === 'statistics'" />
    <Customers v-if="currentPage === 'customers'" />
  </div>
</template>