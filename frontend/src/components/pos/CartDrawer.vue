<script setup>
import { ref, watch, onMounted } from 'vue'
import { useCart } from '@/composables/useCart'

const props = defineProps({
  isOpen: Boolean
})

const emit = defineEmits(['close'])

// Підключаємо логіку кошика
const { 
  cartItems, 
  totalSum, 
  paymentMethod, 
  isProcessing, 
  selectedCustomer,
  fetchCart, 
  updateQty, 
  removeItem, 
  clearCart, 
  processCheckout,
  setCustomer,
  removeCustomer
} = useCart()

// --- UI Local State (Пошук клієнта) ---
const customerSearch = ref('')
const customerResults = ref([])

const handleSearchCustomer = async () => {
  if (customerSearch.value.length < 2) { customerResults.value = []; return }
  try {
    const res = await fetch(`/api/customers/search/?q=${customerSearch.value}`)
    if (res.ok) customerResults.value = await res.json()
  } catch (err) { console.error(err) }
}

const selectCustomerUI = (c) => {
  setCustomer(c) // Записуємо в глобальний стан
  customerSearch.value = ''
  customerResults.value = []
}

const handleCheckout = async () => {
  const res = await processCheckout()
  alert(res.text)
  if (res.success) {
    emit('close')
  }
}

// Завантажуємо кошик при відкритті
watch(() => props.isOpen, (val) => {
  if (val) fetchCart()
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex justify-end transition-opacity duration-300" 
       :class="isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'">
    
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="emit('close')"></div>

    <div class="relative w-full max-w-md bg-white h-full shadow-2xl flex flex-col transition-transform duration-300 transform"
         :class="isOpen ? 'translate-x-0' : 'translate-x-full'">
      
      <div class="p-5 bg-gray-900 text-white flex justify-between items-center shadow-md">
        <h2 class="text-xl font-bold flex items-center gap-2"><i class="fas fa-shopping-cart"></i> Кошик</h2>
        <div class="flex gap-3">
            <button @click="clearCart(false)" class="text-gray-400 hover:text-red-400 transition" title="Очистити все"><i class="fas fa-trash-alt"></i></button>
            <button @click="emit('close')" class="text-gray-400 hover:text-white transition"><i class="fas fa-times text-xl"></i></button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4 bg-gray-50 custom-scrollbar">
        <div v-if="cartItems.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400">
          <i class="fas fa-shopping-basket text-6xl mb-4 opacity-20"></i>
          <p>Кошик порожній</p>
        </div>

        <div v-else class="space-y-3">
          <div v-for="item in cartItems" :key="item.cart_item_id" 
               class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col gap-3">
            
            <div class="flex justify-between items-start">
              <span class="font-bold text-gray-800 text-lg leading-tight">{{ item.name }}</span>
              <span class="font-mono font-bold text-gray-900 whitespace-nowrap">{{ (item.price * item.quantity).toFixed(2) }} ₴</span>
            </div>

            <div class="flex justify-between items-center bg-gray-50 rounded-lg p-1">
                <div class="flex items-center gap-3">
                    <button @click="updateQty(item.cart_item_id, -1)" 
                            class="w-8 h-8 rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 flex items-center justify-center font-bold shadow-sm active:scale-95">-</button>
                    <span class="w-6 text-center font-bold text-gray-800">{{ item.quantity }}</span>
                    <button @click="updateQty(item.cart_item_id, 1)" 
                            class="w-8 h-8 rounded-full bg-gray-800 text-white hover:bg-gray-700 flex items-center justify-center font-bold shadow-sm active:scale-95">+</button>
                </div>
                
                <button @click="removeItem(item.cart_item_id)" class="text-red-400 hover:text-red-600 p-2">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
          </div>
        </div>
      </div>

      <div class="p-6 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        
        <div class="mb-4">
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Клієнт</label>
            <div v-if="!selectedCustomer" class="relative">
                <div class="flex items-center border rounded-lg bg-gray-50 overflow-hidden">
                    <i class="fas fa-search text-gray-400 ml-3"></i>
                    <input v-model="customerSearch" @input="handleSearchCustomer" placeholder="Телефон або ім'я..." class="w-full p-2 bg-transparent outline-none text-sm">
                </div>
                <div v-if="customerResults.length > 0" class="absolute bottom-full left-0 w-full bg-white border shadow-xl rounded-lg mb-1 max-h-40 overflow-y-auto z-10">
                    <div v-for="c in customerResults" :key="c.id" @click="selectCustomerUI(c)" class="p-2 hover:bg-blue-50 cursor-pointer border-b flex justify-between items-center">
                         <div><div class="font-bold text-sm">{{ c.name }}</div><div class="text-xs text-gray-500">{{ c.phone }}</div></div>
                         <i class="fas fa-plus-circle text-blue-500"></i>
                    </div>
                </div>
            </div>
            <div v-else class="flex justify-between items-center bg-blue-50 border border-blue-200 p-2 rounded-lg">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold">{{ selectedCustomer.name.charAt(0) }}</div>
                    <div><div class="font-bold text-sm text-blue-900">{{ selectedCustomer.name }}</div><div class="text-xs text-blue-600">{{ selectedCustomer.phone }}</div></div>
                </div>
                <button @click="removeCustomer" class="text-gray-400 hover:text-red-500 px-2"><i class="fas fa-times"></i></button>
            </div>
        </div>

        <div class="mb-4">
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Оплата</label>
            <div class="grid grid-cols-2 gap-3">
                <button @click="paymentMethod = 'cash'" class="py-2 px-4 rounded-lg border-2 flex items-center justify-center gap-2 transition-all" :class="paymentMethod === 'cash' ? 'border-green-500 bg-green-50 text-green-700 font-bold' : 'border-gray-200 text-gray-500'"> <i class="fas fa-money-bill-wave"></i> Готівка </button>
                <button @click="paymentMethod = 'card'" class="py-2 px-4 rounded-lg border-2 flex items-center justify-center gap-2 transition-all" :class="paymentMethod === 'card' ? 'border-blue-500 bg-blue-50 text-blue-700 font-bold' : 'border-gray-200 text-gray-500'"> <i class="fas fa-credit-card"></i> Картка </button>
            </div>
        </div>

        <div class="flex justify-between items-center text-2xl font-bold mb-4 text-gray-800">
          <span>Разом:</span><span>{{ totalSum.toFixed(2) }} ₴</span>
        </div>
        
        <button @click="handleCheckout" :disabled="cartItems.length === 0 || isProcessing" class="w-full py-4 rounded-xl font-bold text-lg text-white transition shadow-lg flex justify-center items-center gap-2 disabled:bg-gray-400" :class="paymentMethod === 'cash' ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'">
          <span v-if="isProcessing"><i class="fas fa-spinner fa-spin"></i> Обробка...</span>
          <span v-else>Оплатити</span>
        </button>
      </div>
    </div>
  </div>
</template>