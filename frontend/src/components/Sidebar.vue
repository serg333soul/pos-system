<script setup>
// Отримуємо поточну активну сторінку від батька
defineProps({
  currentPage: String 
})

const emit = defineEmits(['change-page'])
</script>

<template>
  <aside class="w-64 bg-gray-900 text-white flex flex-col h-screen fixed left-0 top-0 border-r border-gray-800 z-50">
    
    <div class="p-6 text-2xl font-bold text-center border-b border-gray-800 flex items-center justify-center gap-2">
      <div class="w-8 h-8 bg-gradient-to-tr from-yellow-400 to-orange-500 rounded-full"></div>
      HITS POS
    </div>

    <nav class="flex-1 py-6 space-y-1">
      
      <a href="#" 
         @click.prevent="emit('change-page', 'pos')"
         :class="currentPage === 'pos' ? 'bg-gray-800 text-yellow-400 border-l-4 border-yellow-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
         class="flex items-center px-6 py-3 font-bold transition-all">
        <i class="fas fa-cash-register w-6 text-center mr-2"></i> 
        Каса
      </a>
      
      <a href="#" 
         @click.prevent="emit('change-page', 'warehouse')"
         :class="currentPage === 'warehouse' ? 'bg-gray-800 text-blue-400 border-l-4 border-blue-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
         class="flex items-center px-6 py-3 font-bold transition-all group">
        <i class="fas fa-boxes w-6 text-center mr-2 group-hover:scale-110 transition-transform"></i> 
        Склад
      </a>
      
      <a href="#" 
         @click.prevent="emit('change-page', 'customers')"
         :class="currentPage === 'customers' ? 'bg-gray-800 text-green-400 border-l-4 border-green-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
         class="flex items-center px-6 py-3 font-bold transition-all group">
        <i class="fas fa-users w-6 text-center mr-2 group-hover:scale-110 transition-transform"></i> 
        Клієнти
      </a>

      <a href="#" 
         @click.prevent="emit('change-page', 'statistics')"
         :class="currentPage === 'statistics' ? 'bg-gray-800 text-purple-400 border-l-4 border-purple-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
         class="flex items-center px-6 py-3 font-bold transition-all group">
        <i class="fas fa-chart-line w-6 text-center mr-2 group-hover:scale-110 transition-transform"></i> 
        Статистика
      </a>
    </nav>

    <div class="p-4 border-t border-gray-800 text-xs text-gray-500 text-center">
      <p>Server: <span class="text-green-500">Online 🟢</span></p>
    </div>
  </aside>
</template>