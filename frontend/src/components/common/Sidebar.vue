<script setup>
import { ref } from 'vue'

const props = defineProps({
  currentPage: { type: String, required: true },
  activeSubPage: { type: String, default: '' } // Новий prop для активної під-сторінки
})

const emit = defineEmits(['change-page', 'change-sub-page'])

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
    activeClass: 'text-blue-400 border-l-4 border-blue-400 bg-gray-800',
    // Додаємо під-меню для складу
    children: [
      { id: 'supplies', label: 'Постачання', icon: 'fas fa-truck-loading' },
      { id: 'stock', label: 'Залишки', icon: 'fas fa-clipboard-check' },
      { id: 'products', label: 'Товари', icon: 'fas fa-cube' },
      { id: 'recipes', label: 'Рецепти', icon: 'fas fa-book-open' },
      { id: 'ingredients', label: 'Інгредієнти', icon: 'fas fa-pepper-hot' },
      { id: 'processes', label: 'Процеси', icon: 'fas fa-cogs' },
      { id: 'consumables', label: 'Матеріали', icon: 'fas fa-box-open' },
      { id: 'units', label: 'Одиниці', icon: 'fas fa-ruler-vertical' },
      { id: 'categories', label: 'Категорії', icon: 'fas fa-tags' },
      { id: 'rooms', label: 'Кімнати', icon: 'fas fa-door-open' },
    ]
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
  },
  { 
    id: 'finance', 
    label: 'Фінанси', 
    icon: 'fas fa-wallet', 
    activeClass: 'text-indigo-400 border-l-4 border-indigo-400 bg-gray-800' 
  }
]

const navigate = (pageId) => {
  // Якщо ми натискаємо на вже активний розділ (наприклад, Склад), 
  // то повертаємо користувача на "Касу", що закриє підменю.
  if (props.currentPage === pageId && pageId !== 'pos') {
    emit('change-page', 'pos')
  } else {
    emit('change-page', pageId)
  }
}

// Нова функція для навігації по під-меню
const navigateSub = (mainPageId, subPageId) => {
  emit('change-page', mainPageId) // Переконуємось, що головна сторінка активна
  emit('change-sub-page', subPageId) // Змінюємо активну вкладку
}
</script>

<template>
  <aside class="w-64 bg-gray-900 text-white flex flex-col h-screen fixed left-0 top-0 border-r border-gray-800 z-50">
    
    <div class="p-6 text-2xl font-bold text-center border-b border-gray-800 flex items-center justify-center gap-2">
      <div class="w-8 h-8 bg-gradient-to-tr from-yellow-400 to-orange-500 rounded-full"></div>
      HITS POS
    </div>

    <nav class="flex-1 py-6 space-y-1">
      <template v-for="item in menuItems" :key="item.id">
        <a 
          href="#" 
          @click.prevent="navigate(item.id)"
          class="flex items-center justify-between px-6 py-3 font-bold transition-all group"
          :class="currentPage === item.id ? item.activeClass : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <div class="flex items-center">
            <i 
              :class="[item.icon, 'w-6 text-center mr-3 transition-transform', currentPage !== item.id && 'group-hover:scale-110']"
            ></i> 
            {{ item.label }}
          </div>
          <i v-if="item.children" class="fas fa-chevron-down text-xs transition-transform" :class="{'rotate-180': currentPage === item.id}"></i>
        </a>
        <!-- Розгорнуте під-меню -->
        <div v-if="item.children && currentPage === item.id" class="pl-10 pr-4 py-2 space-y-1 bg-gray-800/50">
          <a 
            v-for="child in item.children" 
            :key="child.id"
            href="#"
            @click.prevent="navigateSub(item.id, child.id)"
            class="flex items-center px-4 py-2 text-sm rounded-lg transition-all"
            :class="activeSubPage === child.id ? 'bg-blue-500/20 text-blue-300 font-bold' : 'text-gray-400 hover:bg-gray-700 hover:text-white'"
          >
            <i :class="[child.icon, 'w-5 text-center mr-2 opacity-70']"></i> {{ child.label }}
          </a>
        </div>
      </template>
    </nav>

    <div class="p-4 border-t border-gray-800 text-xs text-gray-500 text-center">
      <p>Server: <span class="text-green-500">Online 🟢</span></p>
    </div>
  </aside>
</template>