<script setup>
defineProps({
  orders: Array,
  loading: Boolean
})

const emit = defineEmits(['view-details'])

// Helper for date formatting inside template
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}
</script>

<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-gray-100 text-gray-500 uppercase text-xs">
          <tr>
            <th class="p-4">ID / Час</th>
            <th class="p-4">Клієнт</th> 
            <th class="p-4">Товари (Коротко)</th>
            <th class="p-4">Оплата</th>
            <th class="p-4 text-right">Сума</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="orders.length === 0" class="text-center text-gray-400">
            <td colspan="5" class="p-8">
                <span v-if="loading"><i class="fas fa-spinner fa-spin"></i> Завантаження...</span>
                <span v-else>Історія замовлень порожня</span>
            </td>
          </tr>

          <tr v-for="order in orders" :key="order.id" 
              @click="emit('view-details', order)"
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
</template>