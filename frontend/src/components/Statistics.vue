<script setup>
import { ref, onMounted } from 'vue'

const orders = ref([])
const loading = ref(true)

// Функція форматування дати (з "2026-01-12T20:00:00" робить "12.01.2026 20:00")
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

// Завантаження історії
const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/orders/')
    if (res.ok) {
      orders.value = await res.json()
    }
  } catch (err) {
    console.error("Помилка завантаження статистики:", err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchOrders()
})
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-3xl font-bold text-gray-800">📊 Історія продажів</h2>
        <p class="text-gray-500">Перегляд всіх транзакцій та чеків</p>
      </div>
      <button @click="fetchOrders" class="text-blue-600 hover:bg-blue-50 p-2 rounded-full transition">
        <i class="fas fa-sync-alt" :class="{'fa-spin': loading}"></i>
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-gray-100 text-gray-500 uppercase text-xs">
          <tr>
            <th class="p-4">ID / Час</th>
            <th class="p-4">Товари в чеку</th>
            <th class="p-4">Оплата</th>
            <th class="p-4 text-right">Сума</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="orders.length === 0" class="text-center text-gray-400">
            <td colspan="4" class="p-8">Історія замовлень порожня</td>
          </tr>

          <tr v-for="order in orders" :key="order.id" class="hover:bg-gray-50 transition">
            
            <td class="p-4">
              <div class="font-bold text-gray-800">#{{ order.id }}</div>
              <div class="text-sm text-gray-500">{{ formatDate(order.created_at) }}</div>
            </td>

            <td class="p-4">
              <div class="flex flex-col gap-1">
                <div v-for="item in order.items" :key="item.id" class="text-sm">
                  <span class="font-bold">{{ item.product_name }}</span> 
                  <span class="text-gray-500">x{{ item.quantity }}</span>
                </div>
              </div>
            </td>

            <td class="p-4">
              <span v-if="order.payment_method === 'card'" class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">
                <i class="fas fa-credit-card mr-1"></i> Картка
              </span>
              <span v-else class="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">
                <i class="fas fa-money-bill-wave mr-1"></i> Готівка
              </span>
            </td>

            <td class="p-4 text-right font-mono font-bold text-lg">
              {{ order.total_price }} ₴
            </td>

          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>