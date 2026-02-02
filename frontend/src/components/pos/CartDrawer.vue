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
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 z-50" @click="$emit('close')"></div>
  <div class="fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-50 transform transition-transform duration-300 flex flex-col"
    :class="isOpen ? 'translate-x-0' : 'translate-x-full'">
    
    <div class="p-4 border-b flex justify-between bg-gray-50">
      <h2 class="font-bold text-lg">🛒 Кошик</h2>
      <button @click="$emit('close')">✕</button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-3">
      <div v-if="cartItems.length === 0" class="text-center text-gray-400 mt-10">Пусто...</div>
      
      <div v-for="(item, idx) in cartItems" :key="idx" class="flex justify-between border-b pb-2">
        <div>
          <div class="font-bold">{{ item.product_name || item.name }}</div>
          <div v-if="item.variant_name" class="text-xs text-purple-600">{{ item.variant_name }}</div>
          <div class="text-xs text-gray-400">{{ item.quantity }} x {{ item.price }} ₴</div>
        </div>
        <div class="flex flex-col items-end gap-2">
           <span class="font-bold">{{ (item.price * item.quantity).toFixed(2) }} ₴</span>
           <button @click="removeFromCart(item.id)" class="text-red-500 text-xs">🗑</button>
        </div>
      </div>
    </div>

    <div class="p-4 border-t bg-gray-50 space-y-4">
        <div v-if="selectedCustomer" class="flex justify-between bg-blue-100 p-2 rounded text-blue-800 text-sm font-bold">
            <span>👤 {{ selectedCustomer.name }}</span>
            <button @click="removeCustomer">✕</button>
        </div>
        <div v-else>
            <input v-model="customerSearch" @input="handleSearchCustomer" placeholder="Знайти клієнта..." class="w-full p-2 border rounded text-sm">
            <div v-if="customerResults.length" class="absolute bg-white border shadow-lg w-64 max-h-40 overflow-auto z-10 mt-1">
                <div v-for="c in customerResults" :key="c.id" @click="selectCustomerUI(c)" class="p-2 hover:bg-gray-100 cursor-pointer text-sm">
                    {{ c.name }} ({{ c.phone }})
                </div>
            </div>
        </div>

        <div class="flex gap-2">
            <button @click="paymentMethod='cash'" :class="paymentMethod==='cash' ? 'bg-green-100 text-green-700 border-green-500' : 'bg-white border-gray-300'" class="flex-1 py-2 border rounded font-bold transition">💵 Готівка</button>
            <button @click="paymentMethod='card'" :class="paymentMethod==='card' ? 'bg-blue-100 text-blue-700 border-blue-500' : 'bg-white border-gray-300'" class="flex-1 py-2 border rounded font-bold transition">💳 Картка</button>
        </div>

        <div class="flex justify-between text-xl font-bold">
            <span>Разом:</span>
            <span>{{ totalSum.toFixed(2) }} ₴</span>
        </div>

        <button @click="handleCheckout" :disabled="!cartItems.length || isProcessing" class="w-full py-3 bg-gray-800 text-white rounded-xl font-bold disabled:opacity-50">
            {{ isProcessing ? 'Обробка...' : '✅ Оплатити' }}
        </button>
    </div>
  </div>
</template>