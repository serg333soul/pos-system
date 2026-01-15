<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ProductCard from './components/ProductCard.vue'
import CartDrawer from './components/CartDrawer.vue'
import Warehouse from './components/Warehouse.vue'
import Statistics from './components/Statistics.vue'
import Customers from './components/Customers.vue'
import ProductModal from './components/ProductModal.vue'

const currentPage = ref('pos')
const products = ref([])
const loading = ref(true)
const cartCount = ref(0)
const isCartOpen = ref(false)

// Стан модального вікна
const isModalOpen = ref(false)
const selectedProduct = ref(null)

// --- НОВЕ: Посилання на компонент кошика ---
const cartDrawerRef = ref(null)

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
    const cartItems = await res.json()
    cartCount.value = cartItems.reduce((sum, item) => sum + item.quantity, 0)
  } catch (err) { console.error(err) }
}

const handleProductClick = (product) => {
  if (product.has_variants || (product.modifier_groups && product.modifier_groups.length > 0)) {
    selectedProduct.value = product
    isModalOpen.value = true
  } else {
    addToCart({ 
        product: product,
        variant_id: null,
        modifiers: [],
        finalPrice: product.price,
        generatedName: product.name
    })
  }
}

const handleModalAddToCart = async (payload) => {
    await addToCart(payload)
}

const addToCart = async (payload) => {
  const cartPayload = {
      product_id: payload.product.id,
      variant_id: payload.variant_id,
      modifiers: payload.modifiers, 
      quantity: 1,
      name: payload.generatedName,
      price: payload.finalPrice    
  }

  try {
    const res = await fetch('/api/cart/add', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cartPayload)
    })
    
    if (res.ok) {
        // Оновлюємо бейдж з кількістю
        await updateCartCount()
        
        // --- ВАЖЛИВО: Примусово оновлюємо список у кошику! ---
        if (cartDrawerRef.value) {
            await cartDrawerRef.value.loadCart()
        }
    } else {
        console.error("Помилка додавання в кошик")
    }
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
        ref="cartDrawerRef"
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