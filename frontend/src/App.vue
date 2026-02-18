<script setup>
import { ref, onMounted, computed } from 'vue'
// --- Імпортуємо НОВІ компоненти ---
import Sidebar from '@/components/common/Sidebar.vue'
import ProductCard from '@/components/pos/ProductCard.vue'
import CartDrawer from '@/components/pos/CartDrawer.vue'
import ProductModal from '@/components/pos/ProductModal.vue'
import ProductRoomModal from '@/components/pos/ProductRoomModal.vue'; // 🔥 Імпорт нової модалки [13, 14]

// --- Імпортуємо великі розділи ---
import Warehouse from '@/components/warehouse/Warehouse.vue'
import Statistics from '@/components/stats/Statistics.vue'
import Customers from '@/components/crm/Customers.vue'

// --- Імпортуємо логіку (Composables) ---
import { useProducts } from '@/composables/useProducts'
import { useCart } from '@/composables/useCart'
import { useWarehouse } from '@/composables/useWarehouse'

// Стан навігації
const currentPage = ref('pos')
const { products, productRooms, loading, fetchWarehouseData } = useWarehouse()

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

// Стан для кімнат
const isRoomModalOpen = ref(false)
const selectedRoom = ref(null)

const handleRoomClick = (room) => {
  selectedRoom.value = room;
  isRoomModalOpen.value = true;
}

// Фільтрація: показуємо лише товари, які НЕ входять в жодну кімнату [15, 16]
const independentProducts = computed(() => {
  return products.value.filter(p => p.room_id === null);
})

// Кімнати, що підпадають під пошук
const filteredRooms = computed(() => {
  if (!productSearch.value) return productRooms.value;
  const s = productSearch.value.toLowerCase();
  return productRooms.value.filter(r => r.name.toLowerCase().includes(s));
})

// Обробка кліку
const handleItemClick = (item, type) => {
  if (type === 'room') {
    selectedRoom.value = item;
    isRoomModalOpen.value = true;
  } else {
    selectedProduct.value = item;
    isModalOpen.value = true;
  }
}

// Товари, що підпадають під пошук ТА не належать до кімнат
const independentFilteredProducts = computed(() => {
  // 1. Спочатку беремо товари без кімнат
  const independent = products.value.filter(p => !p.room_id)
  
  // 2. Потім фільтруємо їх за пошуком
  if (!productSearch.value) return independent;
  const s = productSearch.value.toLowerCase();
  return independent.filter(p => p.name.toLowerCase().includes(s));
})

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
onMounted(async() => {

  // 1. Спочатку завантажуємо актуальні залишки зі складу
  await fetchWarehouseData()

  fetchProducts()
  // ВІДРАЗУ завантажуємо вміст кошика з сервера
  // Це наповнить cartItems і активує "м'яку броню" для ProductModal
  await fetchCart()
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
    <Sidebar :current-page="currentPage" @change-page="(page) => currentPage = page" />

    <main v-if="currentPage === 'pos'" class="flex-1 ml-64 flex flex-col h-screen relative">
      <!-- Header залишаємо без змін, він працює добре -->
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
          
          <!-- 1. РЕНДЕРИМО КІМНАТИ (ЯК ПАПКИ) -->
          <!-- Ми фільтруємо кімнати за пошуковим запитом назви кімнати -->
          <div 
            v-for="room in filteredRooms" 
            :key="'room-' + room.id"
            @click="handleRoomClick(room)"
            class="cursor-pointer bg-gradient-to-br from-purple-600 to-indigo-700 p-6 rounded-2xl text-white shadow-lg transform hover:scale-[1.02] transition-all flex flex-col items-center justify-center text-center group relative overflow-hidden"
          >
            <!-- Декор папки -->
            <div class="absolute -right-4 -top-4 bg-white/10 w-20 h-20 rounded-full blur-2xl group-hover:bg-white/20 transition-colors"></div>
            
            <div class="text-5xl mb-3 drop-shadow-md">📂</div>
            <div class="font-bold text-lg leading-tight">{{ room.name }}</div>
            <div class="text-xs opacity-80 mt-2 bg-black/20 px-3 py-1 rounded-full">
              {{ room.products?.length || 0 }} позицій
            </div>
          </div>

          <!-- 2. РЕНДЕРИМО НЕЗАЛЕЖНІ ТОВАРИ -->
          <!-- Використовуємо оновлений computed "independentFilteredProducts" -->
          <ProductCard 
            v-for="item in independentFilteredProducts" 
            :key="item.id" 
            :product="item" 
            @click="handleProductClick" 
          />
        </div>
        
        <!-- Стан порожнього пошуку -->
        <div v-if="independentFilteredProducts.length === 0 && filteredRooms.length === 0" class="text-center text-gray-400 mt-20">
            <i class="fas fa-mug-hot text-6xl mb-4 opacity-20"></i>
            <p>Товарів не знайдено</p>
        </div>
      </div>

      <CartDrawer 
        :is-open="isCartOpen"
        @close="isCartOpen = false"
      />
      
      <!-- СТАНДАРТНА МОДАЛКА (для товарів без кімнат) -->
      <ProductModal 
        v-if="selectedProduct"
        :is-open="isModalOpen"
        :product="selectedProduct"
        @close="isModalOpen = false"
      />

      <!-- НОВА МОДАЛКА КІМНАТИ (для вибору фасувань) -->
      <ProductRoomModal
        v-if="selectedRoom"
        :is-open="isRoomModalOpen"
        :group="selectedRoom"
        @close="isRoomModalOpen = false"
      />
    </main>

    <Warehouse v-if="currentPage === 'warehouse'" />
    <Statistics v-if="currentPage === 'statistics'" />
    <Customers v-if="currentPage === 'customers'" />
  </div>
</template>
