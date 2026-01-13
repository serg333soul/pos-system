<script setup>
import { ref, onMounted } from 'vue'

const orders = ref([])
const loading = ref(true)

// Для модального вікна
const showDetailModal = ref(false)
const selectedOrder = ref(null)

// Функція форматування дати
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

// Відкрити деталі
const openDetails = (order) => {
  selectedOrder.value = order
  showDetailModal.value = true
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
        <p class="text-gray-500">Натисніть на замовлення для деталей</p>
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
            <th class="p-4">Клієнт</th> <th class="p-4">Товари (Коротко)</th>
            <th class="p-4">Оплата</th>
            <th class="p-4 text-right">Сума</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="orders.length === 0" class="text-center text-gray-400">
            <td colspan="5" class="p-8">Історія замовлень порожня</td>
          </tr>

          <tr v-for="order in orders" :key="order.id" 
              @click="openDetails(order)"
              class="hover:bg-blue-50 transition cursor-pointer group">
            
            <td class="p-4">
              <div class="font-bold text-gray-800 group-hover:text-blue-600 transition">#{{ order.id }}</div>
              <div class="text-sm text-gray-500">{{ formatDate(order.created_at) }}</div>
            </td>

            <td class="p-4">
                <div v-if="order.customer">
                    <div class="font-bold text-gray-700">{{ order.customer.name }}</div>
                    <div class="text-xs text-gray-400">{{ order.customer.phone }}</div>
                </div>
                <div v-else class="text-gray-400 text-sm italic">Гість</div>
            </td>

            <td class="p-4">
              <div class="text-sm text-gray-600">
                 {{ order.items.length }} позицій
                 <span class="text-xs text-gray-400">({{ order.items[0]?.product_name }}...)</span>
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

            <td class="p-4 text-right font-mono font-bold text-lg text-gray-800">
              {{ order.total_price }} ₴
            </td>

          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showDetailModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg relative overflow-hidden flex flex-col max-h-[90vh]">
            
            <div class="p-6 bg-gray-50 border-b flex justify-between items-start">
                <div>
                    <h3 class="text-2xl font-bold text-gray-800">Чек #{{ selectedOrder.id }}</h3>
                    <p class="text-gray-500 text-sm">{{ formatDate(selectedOrder.created_at) }}</p>
                </div>
                <button @click="showDetailModal = false" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-2xl"></i>
                </button>
            </div>

            <div class="p-6 overflow-y-auto">
                
                <div class="mb-6 bg-blue-50 p-4 rounded-xl border border-blue-100 flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-blue-200 text-blue-600 flex items-center justify-center text-lg">
                        <i class="fas" :class="selectedOrder.customer ? 'fa-user' : 'fa-user-secret'"></i>
                    </div>
                    <div>
                        <div class="text-xs font-bold text-blue-400 uppercase">Покупець</div>
                        <div class="font-bold text-gray-800 text-lg">
                            {{ selectedOrder.customer ? selectedOrder.customer.name : 'Гість' }}
                        </div>
                        <div v-if="selectedOrder.customer" class="text-sm text-gray-600">
                            {{ selectedOrder.customer.phone }}
                        </div>
                    </div>
                </div>

                <h4 class="font-bold text-gray-700 mb-3 border-b pb-2">Товари</h4>
                <div class="space-y-3">
                    <div v-for="item in selectedOrder.items" :key="item.id" class="flex justify-between items-center text-sm">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-gray-800">{{ item.product_name }}</span>
                        </div>
                        <div class="flex items-center gap-4">
                            <span class="text-gray-500">x{{ item.quantity }}</span>
                            <span class="font-mono font-bold">{{ item.price_at_moment * item.quantity }} ₴</span>
                        </div>
                    </div>
                </div>

            </div>

            <div class="p-6 bg-gray-50 border-t">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-gray-500">Метод оплати:</span>
                    <span class="font-bold uppercase text-sm" 
                          :class="selectedOrder.payment_method === 'card' ? 'text-blue-600' : 'text-green-600'">
                        {{ selectedOrder.payment_method === 'card' ? 'Банківська картка' : 'Готівка' }}
                    </span>
                </div>
                <div class="flex justify-between items-center text-3xl font-bold text-gray-900 mt-2">
                    <span>Разом:</span>
                    <span>{{ selectedOrder.total_price }} ₴</span>
                </div>
            </div>

        </div>
    </div>

  </div>
</template>