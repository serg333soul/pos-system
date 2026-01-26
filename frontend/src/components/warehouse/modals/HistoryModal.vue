<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  isOpen: Boolean,
  item: Object // Очікуємо об'єкт: { id, type, name }
})

const emit = defineEmits(['close'])
const history = ref([])
const loading = ref(false)
const error = ref(null)

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('uk-UA', { 
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' 
  })
}

const fetchHistory = async () => {
  if (!props.item) return
  
  loading.value = true
  history.value = [] 
  error.value = null

  try {
    // URL формується з чистого ID, який ми передали з StockTab
    const url = `/api/history/?entity_type=${props.item.type}&entity_id=${props.item.id}`
    
    console.log("HISTORY MODAL: Requesting ->", url)
    
    const res = await fetch(url)
    
    if (res.ok) {
        history.value = await res.json()
        console.log("HISTORY MODAL: Success! Records found:", history.value.length)
    } else {
        console.error("HISTORY MODAL: Server returned status", res.status)
        error.value = "Помилка сервера"
    }
  } catch (e) {
    console.error("HISTORY MODAL: Network error", e)
    error.value = "Помилка з'єднання"
  } finally {
    loading.value = false
  }
}

// Слідкуємо за відкриттям
watch(() => props.isOpen, (val) => {
  if (val) {
    fetchHistory()
  }
}, { immediate: true })
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[80vh] animate-fade-in-up">
      
      <div class="p-4 border-b flex justify-between items-center bg-gray-50">
        <div>
           <div class="text-xs uppercase font-bold text-gray-400">Історія руху</div>
           <h3 class="font-bold text-lg text-gray-800">{{ item?.name }}</h3>
           <p class="text-xs text-gray-400">ID: {{ item?.id }} | Type: {{ item?.type }}</p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200">
            <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-0 custom-scrollbar relative min-h-[200px]">
         
         <div v-if="loading" class="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10">
            <i class="fas fa-spinner fa-spin text-3xl text-blue-500 mb-2"></i> 
            <span class="text-gray-500">Завантаження...</span>
         </div>

         <div v-else-if="error" class="p-8 text-center text-red-500">
            <i class="fas fa-exclamation-circle text-2xl mb-2"></i>
            <p>{{ error }}</p>
         </div>

         <div v-else-if="history.length === 0" class="p-8 text-center text-gray-400">
            <i class="fas fa-history text-4xl mb-3 opacity-30"></i>
            <p>Історія порожня</p>
         </div>
         
         <table v-else class="w-full text-sm text-left">
           <thead class="bg-gray-100 text-gray-500 text-xs uppercase sticky top-0">
             <tr>
               <th class="p-3">Дата</th>
               <th class="p-3">Причина</th>
               <th class="p-3 text-right">Зміна</th>
               <th class="p-3 text-right">Залишок</th>
             </tr>
           </thead>
           <tbody class="divide-y divide-gray-100">
             <tr v-for="h in history" :key="h.id" class="hover:bg-gray-50 transition-colors">
               <td class="p-3 text-gray-500 whitespace-nowrap font-mono text-xs">{{ formatDate(h.created_at) }}</td>
               
               <td class="p-3">
                 <span v-if="h.reason === 'manual_correction'" class="bg-gray-200 text-gray-600 px-2 py-1 rounded text-[10px] font-bold">Корекція</span>
                 <span v-else-if="h.reason && h.reason.includes('sale')" class="bg-green-100 text-green-700 px-2 py-1 rounded text-[10px] font-bold">Продаж</span>
                 <span v-else class="text-gray-700 font-bold text-xs">{{ h.reason }}</span>
               </td>

               <td class="p-3 text-right font-mono font-bold" :class="h.change_amount > 0 ? 'text-green-600' : 'text-red-500'">
                 {{ h.change_amount > 0 ? '+' : '' }}{{ h.change_amount }}
               </td>
               
               <td class="p-3 text-right font-mono text-gray-600">
                 {{ h.balance_after }}
               </td>
             </tr>
           </tbody>
         </table>
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