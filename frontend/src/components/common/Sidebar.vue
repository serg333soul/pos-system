<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: { type: String, required: true }
})

const emit = defineEmits(['change-page'])

// Конфігурація меню. Легко розширювати.
const menuItems = [
  { 
    id: 'pos', 
    label: 'Каса', 
    icon: 'fas fa-cash-register', 
    activeClass: 'text-yellow-400 border-l-4 border-yellow-400 bg-gray-800' 
  },
  { 
    id: 'warehouse', 
    label: 'Склад', 
    icon: 'fas fa-boxes', 
    activeClass: 'text-blue-400 border-l-4 border-blue-400 bg-gray-800' 
  },
  { 
    id: 'customers', 
    label: 'Клієнти', 
    icon: 'fas fa-users', 
    activeClass: 'text-green-400 border-l-4 border-green-400 bg-gray-800' 
  },
  { 
    id: 'statistics', 
    label: 'Статистика', 
    icon: 'fas fa-chart-line', 
    activeClass: 'text-purple-400 border-l-4 border-purple-400 bg-gray-800' 
  }
]

const navigate = (pageId) => {
  emit('change-page', pageId)
}
</script>

<template>
  <aside class="w-64 bg-gray-900 text-white flex flex-col h-screen fixed left-0 top-0 border-r border-gray-800 z-50">
    
    <div class="p-6 text-2xl font-bold text-center border-b border-gray-800 flex items-center justify-center gap-2">
      <div class="w-8 h-8 bg-gradient-to-tr from-yellow-400 to-orange-500 rounded-full"></div>
      HITS POS
    </div>

    <nav class="flex-1 py-6 space-y-1">
      <a 
        v-for="item in menuItems" 
        :key="item.id"
        href="#" 
        @click.prevent="navigate(item.id)"
        class="flex items-center px-6 py-3 font-bold transition-all group"
        :class="currentPage === item.id ? item.activeClass : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
      >
        <i 
          :class="[item.icon, 'w-6 text-center mr-2 transition-transform', currentPage !== item.id && 'group-hover:scale-110']"
        ></i> 
        {{ item.label }}
      </a>
    </nav>

    <div class="p-4 border-t border-gray-800 text-xs text-gray-500 text-center">
      <p>Server: <span class="text-green-500">Online 🟢</span></p>
    </div>
  </aside>
</template>