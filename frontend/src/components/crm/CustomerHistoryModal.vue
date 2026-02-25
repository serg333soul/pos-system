<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9] flex items-center justify-center p-4">
    <div class="bg-white rounded-3xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-blue-50/30">
        <div>
          <h3 class="text-xl font-bold text-gray-800"> 📖 Історія покупок</h3>
          <p class="text-sm text-gray-500">{{ customer?.name }}</p>
        </div>
        <button @click="$emit('close')" class="p-2 hover:bg-white rounded-full transition text-gray-400 hover:text-gray-600">×</button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto p-6">

        <!-- 🔥 НОВИЙ БЛОК СТАТИСТИКИ -->
        <div v-if="!loading && orders.length > 0" class="grid grid-cols-3 gap-4 mb-8">
          <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Візитів</p>
            <p class="text-2xl font-black text-gray-800">{{ customerStats.count }}</p>
          </div>
          
          <div class="bg-blue-50 p-4 rounded-2xl border border-blue-100">
            <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">Середній чек</p>
            <p class="text-2xl font-black text-blue-700">{{ customerStats.average.toFixed(2) }} ₴</p>
          </div>
          
          <div class="bg-green-50 p-4 rounded-2xl border border-green-100">
            <p class="text-[10px] font-black text-green-400 uppercase tracking-widest mb-1">Всього витрачено</p>
            <p class="text-2xl font-black text-green-700">{{ customerStats.total.toFixed(2) }} ₴</p>
          </div>
        </div>

        <div v-if="loading" class="text-center py-10 text-gray-400 italic">Завантаження історії...</div>
        
        <div v-else-if="orders.length === 0" class="text-center py-10">
          <div class="text-4xl mb-3">🏷️</div>
          <p class="text-gray-400">Цей клієнт ще не робив покупок.</p>
        </div>

        <table v-else class="w-full text-left">
          <thead class="text-[10px] font-black text-gray-400 uppercase tracking-widest border-b">
            <tr>
              <th class="pb-3">Дата / Чек</th>
              <th class="pb-3">Оплата</th>
              <th class="pb-3 text-right">Сума</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <template v-for="order in orders" :key="order.id">
              <!-- Рядок чека -->
              <tr @click="toggleDetails(order.id)" class="hover:bg-blue-50/50 cursor-pointer transition-colors group">
                <td class="py-4">
                  <div class="flex items-center gap-2 text-sm">
                    <span class="text-[10px] transition-transform" :class="{ 'rotate-90': expandedId === order.id }">▶</span>
                    <span class="font-bold text-gray-700">#{{ order.id }}</span>
                    <span class="text-gray-400 text-xs">{{ formatDate(order.created_at) }}</span>
                  </div>
                </td>
                <td class="py-4">
                  <span :class="order.payment_method === 'card' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'" 
                        class="px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                    {{ order.payment_method === 'card' ? 'Картка' : 'Готівка' }}
                  </span>
                </td>
                <td class="py-4 text-right font-black text-gray-800">{{ order.total_price.toFixed(2) }} ₴</td>
              </tr>

              <!-- Розгорнуті деталі чека -->
              <tr v-if="expandedId === order.id">
                <td colspan="3" class="p-0 bg-gray-50/50">
                  <div class="p-4 border-l-4 border-blue-400 ml-4 my-2">
                    <div v-for="item in order.items" :key="item.id" class="flex justify-between text-xs py-1 border-b border-dashed border-gray-200 last:border-0">
                      <span class="text-gray-600">{{ item.product_name }} <span v-if="item.details" class="text-[10px] text-gray-400">({{ item.details }})</span></span>
                      <span class="font-medium text-gray-800">{{ item.quantity }} x {{ item.price_at_moment }} ₴</span>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps(['isOpen', 'customer', 'orders', 'loading']);
const emit = defineEmits(['close']);

const expandedId = ref(null);

// 🔥 НОВА ЛОГІКА: Розрахунок статистики клієнта
const customerStats = computed(() => {
  if (!props.orders || props.orders.length === 0) {
    return { total: 0, count: 0, average: 0 };
  }
  
  const total = props.orders.reduce((sum, order) => sum + order.total_price, 0);
  const count = props.orders.length;
  
  return {
    total: total,
    count: count,
    average: total / count
  };
});

const toggleDetails = (id) => {
  expandedId.value = expandedId.value === id ? null : id;
};

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('uk-UA', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};
</script>