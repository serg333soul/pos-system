<script setup>
import { ref, onMounted } from 'vue'
// --- Імпортуємо НОВІ компоненти ---
import Sidebar from '@/components/common/Sidebar.vue'
import ProductCard from '@/components/pos/ProductCard.vue'
import CartDrawer from '@/components/pos/CartDrawer.vue'
import ProductModal from '@/components/pos/ProductModal.vue'

// --- Імпортуємо великі розділи ---
import Warehouse from '@/components/warehouse/Warehouse.vue'
import Statistics from '@/components/stats/Statistics.vue'
import Customers from '@/components/crm/Customers.vue'

// --- Імпортуємо логіку (Composables) ---
import { useProducts } from '@/composables/useProducts'
import { useCart } from '@/composables/useCart'

// Стан навігації
const currentPage = ref('pos')

// --- Логіка POS (Каси) ---
// Використовуємо useProducts для завантаження товарів на вітрину
const { 
  filteredProducts, // Вже відфільтровані пошуком
  productSearch, 
  fetchProducts 
} = useProducts()

// Використовуємо useCart для кошика (лічильник, відкриття)
const { 
  cartCount, 
  fetchCart // Щоб оновити лічильник при старті
} = useCart()

// Стан для UI каси
const isCartOpen = ref(false)
const isModalOpen = ref(false)
const selectedProduct = ref(null)

// Обробка кліку по товару
const handleProductClick = (product) => {
  // Якщо є варіанти або модифікатори -> відкриваємо модалку
  if (product.has_variants || (product.modifier_groups && product.modifier_groups.length > 0) || (product.process_groups && product.process_groups.length > 0)) {
    selectedProduct.value = product
    isModalOpen.value = true
  } else {
    // Якщо простий товар -> додаємо в кошик (через ProductModal логіку або напряму, 
    // але для простоти відкриємо модалку або можна викликати addToCart напряму.
    // Тут краще відкрити модалку для підтвердження або швидкого додавання)
    selectedProduct.value = product
    isModalOpen.value = true
  }
}

// Завантаження даних при старті
onMounted(() => {
  fetchProducts()
  fetchCart()
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
    <Sidebar :current-page="currentPage" @change-page="(page) => currentPage = page" />

    <main v-if="currentPage === 'pos'" class="flex-1 ml-64 flex flex-col h-screen relative">
      <header class="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gray-200 px-8 py-4 flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Меню</h2>
          <div class="flex items-center gap-2 mt-1">
             <i class="fas fa-search text-gray-400"></i>
             <input v-model="productSearch" type="text" placeholder="Пошук кави..." class="bg-transparent outline-none text-sm w-64">
          </div>
        </div>
        
        <button @click="isCartOpen = true" class="bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition shadow-lg flex items-center gap-3 active:scale-95">
          <i class="fas fa-shopping-cart"></i> <span>Кошик: {{ cartCount }}</span>
        </button>
      </header>

      <div class="p-8 overflow-y-auto flex-1 custom-scrollbar">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          <ProductCard 
            v-for="item in filteredProducts" 
            :key="item.id" 
            :product="item" 
            @click="handleProductClick" 
          />
        </div>
        
        <div v-if="filteredProducts.length === 0" class="text-center text-gray-400 mt-20">
            <i class="fas fa-mug-hot text-6xl mb-4 opacity-20"></i>
            <p>Товарів не знайдено</p>
        </div>
      </div>

      <CartDrawer 
        :is-open="isCartOpen"
        @close="isCartOpen = false"
      />
      
      <ProductModal 
        :is-open="isModalOpen"
        :product="selectedProduct"
        @close="isModalOpen = false"
      />
    </main>

    <Warehouse v-if="currentPage === 'warehouse'" />

    <Statistics v-if="currentPage === 'statistics'" />

    <Customers v-if="currentPage === 'customers'" />
    
  </div>
</template>