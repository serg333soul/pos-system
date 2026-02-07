<script setup>
import { ref, watch } from 'vue'
import { useCart } from '@/composables/useCart'

const props = defineProps({ isOpen: Boolean })
const emit = defineEmits(['close'])

const { 
  cartItems, totalSum, paymentMethod, isProcessing, selectedCustomer,
  fetchCart, removeFromCart, clearCart, processCheckout,
  setCustomer, removeCustomer
} = useCart()

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
  setCustomer(c)
  customerSearch.value = ''
  customerResults.value = []
}

// --- НОВА ФУНКЦІЯ: ОЧИЩЕННЯ КОШИКА ---
const handleClearCart = async () => {
    if (cartItems.value.length === 0) return
    
    if (confirm('Ви впевнені, що хочете повністю очистити кошик?')) {
        await clearCart()
    }
}

const handleCheckout = async () => {
  const res = await processCheckout()
  
  if (res && res.success) {
    alert(res.text) // Покажемо суму від сервера
    emit('close')
  } else {
    alert(res ? res.text : "Невідома помилка")
  }
}

watch(() => props.isOpen, (val) => {
  if (val) fetchCart()
})
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex">
    <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="emit('close')"></div>
    
    <div class="relative flex flex-col h-full bg-white shadow-xl w-full max-w-md ml-auto animate-slide-in">
        
        <div class="p-4 border-b flex justify-between items-center bg-gray-50">
            <div class="flex items-center gap-3">
                <h2 class="font-bold text-lg text-gray-800">Кошик</h2>
                <button 
                    v-if="cartItems.length > 0"
                    @click="handleClearCart" 
                    class="text-red-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded-lg transition"
                    title="Очистити все"
                >
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>

            <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">
                <i class="fas fa-times text-xl"></i>
            </button>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <div v-if="cartItems.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400">
                <i class="fas fa-shopping-basket text-4xl mb-2 opacity-30"></i>
                <p>Кошик порожній</p>
            </div>
            
            <div v-else v-for="(item, idx) in cartItems" :key="idx" class="flex gap-3 relative group border-b pb-3 last:border-0">
                <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0 text-2xl">
                    {{ item.image_url ? '' : '☕' }}
                    <img v-if="item.image_url" :src="item.image_url" class="w-full h-full object-cover rounded-lg">
                </div>

                <div class="flex-1">
                    <div class="flex justify-between items-start">
                        <h4 class="font-bold text-gray-800 text-sm leading-tight pr-6">{{ item.name }}</h4>
                        <span class="font-bold text-gray-900">{{ (item.price * item.quantity).toFixed(2) }}₴</span>
                    </div>
                    
                    <div v-if="item.variant_name" class="text-xs text-gray-500 mt-0.5">
                        {{ item.variant_name }}
                    </div>

                    <div v-if="item.modifiers && item.modifiers.length" class="flex flex-wrap gap-1 mt-1">
                        <span v-for="mod in item.modifiers" :key="mod.id" class="text-[10px] bg-yellow-50 text-yellow-700 px-1 rounded border border-yellow-100">
                            +{{ mod.name }}
                        </span>
                    </div>

                    <div class="flex justify-between items-end mt-2">
                        <div class="text-sm text-gray-500">
                            {{ item.quantity }} x {{ item.price }} ₴
                        </div>
                        <button @click="removeFromCart(item.product_id, item.variant_id)" class="text-red-400 hover:text-red-600 text-xs font-medium">
                            Видалити
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div class="p-4 border-t bg-gray-50 space-y-4">
            
            <div class="relative">
                <div v-if="selectedCustomer" class="flex justify-between items-center p-2 bg-blue-50 border border-blue-200 rounded text-sm">
                    <span class="font-bold text-blue-800"><i class="fas fa-user mr-1"></i> {{ selectedCustomer.name }}</span>
                    <button @click="removeCustomer" class="text-blue-500 hover:text-blue-700"><i class="fas fa-times"></i></button>
                </div>
                <div v-else>
                    <input v-model="customerSearch" @input="handleSearchCustomer" placeholder="Знайти клієнта..." class="w-full p-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none">
                    <div v-if="customerResults.length" class="absolute bg-white border shadow-xl w-full max-h-48 overflow-auto z-10 mt-1 rounded-lg">
                        <div v-for="c in customerResults" :key="c.id" @click="selectCustomerUI(c)" class="p-2.5 hover:bg-gray-100 cursor-pointer text-sm border-b last:border-0">
                            {{ c.name }} <span class="text-gray-400 text-xs ml-1">{{ c.phone }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex gap-2">
                <button @click="paymentMethod='cash'" :class="paymentMethod==='cash' ? 'bg-green-100 text-green-700 border-green-500 ring-1 ring-green-500' : 'bg-white border-gray-300 hover:bg-gray-50'" class="flex-1 py-2.5 border rounded-lg font-bold transition flex items-center justify-center gap-2 text-sm">
                    <i class="fas fa-money-bill-wave"></i> Готівка
                </button>
                <button @click="paymentMethod='card'" :class="paymentMethod==='card' ? 'bg-blue-100 text-blue-700 border-blue-500 ring-1 ring-blue-500' : 'bg-white border-gray-300 hover:bg-gray-50'" class="flex-1 py-2.5 border rounded-lg font-bold transition flex items-center justify-center gap-2 text-sm">
                    <i class="fas fa-credit-card"></i> Картка
                </button>
            </div>

            <button 
                @click="handleCheckout"
                :disabled="cartItems.length === 0 || isProcessing"
                class="w-full py-3.5 bg-purple-600 text-white rounded-xl font-bold text-lg hover:bg-purple-700 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] transition flex items-center justify-center gap-2"
            >
                <span v-if="isProcessing"><i class="fas fa-spinner fa-spin"></i></span>
                <span v-else>Оплатити {{ totalSum.toFixed(2) }} ₴</span>
            </button>
        </div>
    </div>
  </div>
</template>

<style scoped>
.animate-slide-in {
    animation: slideIn 0.3s ease-out;
}
@keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
}
</style>