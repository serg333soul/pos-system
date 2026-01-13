<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  isOpen: Boolean,
  products: Array // Список всіх товарів
})

const emit = defineEmits(['close', 'clear-cart'])
const cartItems = ref([])
const isProcessing = ref(false)
const paymentMethod = ref('cash')

// --- CRM (КЛІЄНТИ) ---
const customerSearch = ref('')
const customerResults = ref([])
const selectedCustomer = ref(null) // Тут буде об'єкт клієнта, якщо вибрали

// Пошук клієнта
const searchCustomer = async () => {
  if (customerSearch.value.length < 2) {
    customerResults.value = []
    return
  }
  try {
    const res = await fetch(`/api/customers/search/?q=${customerSearch.value}`)
    if (res.ok) customerResults.value = await res.json()
  } catch (err) {
    console.error(err)
  }
}

// Вибір клієнта зі списку
const selectCustomer = (customer) => {
  selectedCustomer.value = customer
  customerSearch.value = ''
  customerResults.value = []
}

// Скидання клієнта
const removeCustomer = () => {
  selectedCustomer.value = null
}

// --- ЗАВАНТАЖЕННЯ ДАНИХ ---
const loadCart = async () => {
  try {
    const res = await fetch('/api/cart/')
    if (!res.ok) return
    const rawCart = await res.json() 
    
    const items = []
    for (const [idStr, qty] of Object.entries(rawCart)) {
      const id = parseInt(idStr)
      const product = props.products.find(p => p.id === id)
      
      if (product) {
        items.push({
          product_id: id,
          name: product.name,
          price: product.price,
          quantity: parseInt(qty),
          image: product.image || null 
        })
      }
    }
    cartItems.value = items.sort((a, b) => a.name.localeCompare(b.name))
  } catch (err) {
    console.error("Помилка кошика:", err)
  }
}

// --- УПРАВЛІННЯ ТОВАРАМИ ---
const increaseQty = async (id) => {
  await fetch(`/api/cart/${id}`, { method: 'POST' })
  await loadCart()
}
const decreaseQty = async (id) => {
  await fetch(`/api/cart/${id}/decrease`, { method: 'POST' })
  await loadCart()
}
const removeItem = async (id) => {
  if(!confirm('Видалити цей товар з кошика?')) return
  await fetch(`/api/cart/${id}`, { method: 'DELETE' })
  await loadCart()
}
const clearAll = async () => {
  if(!confirm('Очистити весь кошик?')) return
  await fetch('/api/cart/', { method: 'DELETE' })
  await loadCart()
  emit('clear-cart')
}

// --- ОПЛАТА ---
const totalSum = computed(() => {
  return cartItems.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
})

const checkout = async () => {
  if (cartItems.value.length === 0) return
  isProcessing.value = true

  try {
    const payload = {
      items: cartItems.value.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
      })),
      payment_method: paymentMethod.value,
      total_price: totalSum.value,
      // Додаємо ID клієнта, якщо він вибраний
      customer_id: selectedCustomer.value ? selectedCustomer.value.id : null
    }

    const deductRes = await fetch('/api/orders/checkout/', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!deductRes.ok) throw new Error("Помилка списання зі складу")

    // Очистка
    await fetch('/api/cart/', { method: 'DELETE' })
    
    // Формуємо повідомлення
    let msg = `✅ Оплата успішна!\nСума: ${totalSum.value} ₴`
    if (selectedCustomer.value) {
        msg += `\nКлієнт: ${selectedCustomer.value.name}`
    }
    alert(msg)
    
    selectedCustomer.value = null // Скидаємо клієнта
    emit('clear-cart')
    emit('close')
    
  } catch (err) {
    alert("❌ Помилка при оплаті! Перевірте залишки на складі.")
    console.error(err)
  } finally {
    isProcessing.value = false
  }
}

watch(() => props.isOpen, (newVal) => {
  if (newVal) loadCart()
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex justify-end transition-opacity duration-300" 
       :class="isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'">
    
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="emit('close')"></div>

    <div class="relative w-full max-w-md bg-white h-full shadow-2xl flex flex-col transition-transform duration-300 transform"
         :class="isOpen ? 'translate-x-0' : 'translate-x-full'">
      
      <div class="p-5 bg-gray-900 text-white flex justify-between items-center shadow-md">
        <h2 class="text-xl font-bold flex items-center gap-2">
          <i class="fas fa-shopping-cart"></i> Кошик
        </h2>
        <div class="flex gap-3">
            <button @click="clearAll" class="text-gray-400 hover:text-red-400 transition" title="Очистити все">
                <i class="fas fa-trash-alt"></i>
            </button>
            <button @click="emit('close')" class="text-gray-400 hover:text-white transition">
                <i class="fas fa-times text-xl"></i>
            </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4 bg-gray-50">
        <div v-if="cartItems.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400">
          <i class="fas fa-shopping-basket text-6xl mb-4 opacity-20"></i>
          <p>Кошик порожній</p>
        </div>

        <div v-else class="space-y-3">
          <div v-for="item in cartItems" :key="item.product_id" 
               class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col gap-3">
            
            <div class="flex justify-between items-start">
              <span class="font-bold text-gray-800 text-lg">{{ item.name }}</span>
              <span class="font-mono font-bold text-gray-900">{{ item.price * item.quantity }} ₴</span>
            </div>

            <div class="flex justify-between items-center bg-gray-50 rounded-lg p-1">
                <div class="flex items-center gap-3">
                    <button @click="decreaseQty(item.product_id)" 
                            class="w-8 h-8 rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 flex items-center justify-center font-bold shadow-sm active:scale-95">
                        -
                    </button>
                    <span class="w-6 text-center font-bold text-gray-800">{{ item.quantity }}</span>
                    <button @click="increaseQty(item.product_id)" 
                            class="w-8 h-8 rounded-full bg-gray-800 text-white hover:bg-gray-700 flex items-center justify-center font-bold shadow-sm active:scale-95">
                        +
                    </button>
                </div>
                
                <button @click="removeItem(item.product_id)" class="text-red-400 hover:text-red-600 p-2">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
          </div>
        </div>
      </div>

      <div class="p-6 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        
        <div class="mb-4">
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Клієнт (Бонуси)</label>
            
            <div v-if="!selectedCustomer" class="relative">
                <div class="flex items-center border rounded-lg bg-gray-50 focus-within:ring-2 ring-blue-500 overflow-hidden">
                    <i class="fas fa-search text-gray-400 ml-3"></i>
                    <input 
                        v-model="customerSearch" 
                        @input="searchCustomer"
                        placeholder="Знайти за телефоном або ім'ям..." 
                        class="w-full p-2 bg-transparent outline-none text-sm"
                    >
                </div>
                <div v-if="customerResults.length > 0" class="absolute bottom-full left-0 w-full bg-white border shadow-xl rounded-lg mb-1 max-h-40 overflow-y-auto z-10">
                    <div v-for="c in customerResults" :key="c.id" 
                         @click="selectCustomer(c)"
                         class="p-2 hover:bg-blue-50 cursor-pointer border-b last:border-0 flex justify-between items-center">
                         <div>
                             <div class="font-bold text-sm">{{ c.name }}</div>
                             <div class="text-xs text-gray-500">{{ c.phone }}</div>
                         </div>
                         <i class="fas fa-plus-circle text-blue-500"></i>
                    </div>
                </div>
            </div>

            <div v-else class="flex justify-between items-center bg-blue-50 border border-blue-200 p-2 rounded-lg">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold">
                        {{ selectedCustomer.name.charAt(0) }}
                    </div>
                    <div>
                        <div class="font-bold text-sm text-blue-900">{{ selectedCustomer.name }}</div>
                        <div class="text-xs text-blue-600">{{ selectedCustomer.phone }}</div>
                    </div>
                </div>
                <button @click="removeCustomer" class="text-gray-400 hover:text-red-500 px-2">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>

        <div class="mb-4">
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Спосіб оплати</label>
            <div class="grid grid-cols-2 gap-3">
                <button @click="paymentMethod = 'cash'"
                    class="py-2 px-4 rounded-lg border-2 flex items-center justify-center gap-2 transition-all"
                    :class="paymentMethod === 'cash' ? 'border-green-500 bg-green-50 text-green-700 font-bold' : 'border-gray-200 text-gray-500 hover:border-gray-300'">
                    <i class="fas fa-money-bill-wave"></i> Готівка
                </button>
                <button @click="paymentMethod = 'card'"
                    class="py-2 px-4 rounded-lg border-2 flex items-center justify-center gap-2 transition-all"
                    :class="paymentMethod === 'card' ? 'border-blue-500 bg-blue-50 text-blue-700 font-bold' : 'border-gray-200 text-gray-500 hover:border-gray-300'">
                    <i class="fas fa-credit-card"></i> Картка
                </button>
            </div>
        </div>

        <div class="flex justify-between items-center text-2xl font-bold mb-4 text-gray-800">
          <span>Разом:</span>
          <span>{{ totalSum }} ₴</span>
        </div>
        
        <button 
          @click="checkout"
          :disabled="cartItems.length === 0 || isProcessing"
          class="w-full py-4 rounded-xl font-bold text-lg text-white transition shadow-lg flex justify-center items-center gap-2 disabled:bg-gray-400 disabled:cursor-not-allowed active:scale-95"
          :class="paymentMethod === 'cash' ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'">
          
          <span v-if="isProcessing"><i class="fas fa-spinner fa-spin"></i> Обробка...</span>
          <span v-else>
            Оплатити ({{ paymentMethod === 'cash' ? 'Готівка' : 'Картка' }})
          </span>
        </button>
      </div>
    </div>
  </div>
</template>