<script setup>
import { onMounted } from 'vue'
import { useStatistics } from '@/composables/useStatistics'
import SalesTable from './SalesTable.vue'

// 🔥 ВАЖЛИВО: Ми НЕ створюємо нові ref, а дістаємо їх із useStatistics
const { 
  orders, 
  loading, 
  totalPages, 
  currentPage, 
  pageSize, 
  fetchOrders, 
  openDetails 
} = useStatistics()

// Helper for date formatting (duplicate need for modal, can be util)
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

// Примусовий виклик при завантаженні для перестраховки
onMounted(() => {
  console.log("📍 Компонент Statistics монтується");
  fetchOrders();
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

    <div class="flex justify-between items-center bg-white p-4 rounded-2xl shadow-sm mb-4 border border-gray-100">
        <div class="flex items-center gap-3">
            <span class="text-xs text-gray-500 font-bold">Показувати по:</span>
            <select 
            v-model.number="pageSize" 
            class="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-lg p-1.5 focus:ring-blue-500 outline-none"
            >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            </select>
        </div>

        <div class="flex items-center gap-2">
            <button 
            @click="currentPage--" 
            :disabled="currentPage === 1"
            class="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
            ⬅️
            </button>
            
            <span class="text-xs font-bold text-gray-600">
            Сторінка {{ currentPage }} з {{ totalPages }}
            </span>

            <button 
            @click="currentPage++" 
            :disabled="currentPage === totalPages"
            class="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
            >
            ➡️
            </button>
        </div>
    </div>

    <SalesTable :orders="orders" :loading="loading" @view-details="openDetails" />

    <div v-if="showDetailModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg relative overflow-hidden flex flex-col max-h-[90vh] animate-fade-in-up">
            
            <div class="p-6 bg-gray-50 border-b flex justify-between items-start">
                <div>
                    <h3 class="text-2xl font-bold text-gray-800">Чек #{{ selectedOrder.id }}</h3>
                    <p class="text-gray-500 text-sm">{{ formatDate(selectedOrder.created_at) }}</p>
                </div>
                <button @click="closeDetails" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-2xl"></i>
                </button>
            </div>

            <div class="p-6 overflow-y-auto custom-scrollbar">
                
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
                            <span v-if="item.details" class="text-xs text-gray-400">({{ item.details }})</span>
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

<style scoped>
.animate-fade-in-up { animation: fadeInUp 0.3s ease-out; }
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>