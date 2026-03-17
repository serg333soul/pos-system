<script setup>
import { onMounted, defineAsyncComponent, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// --- НОВИЙ ІМПОРТ ---
const StockTab = defineAsyncComponent(() => import('./tabs/StockTab.vue'))
const ProductsTab = defineAsyncComponent(() => import('./tabs/products/ProductsTab.vue'))
const IngredientsTab = defineAsyncComponent(() => import('./tabs/IngredientsTab.vue'))
const RecipesTab = defineAsyncComponent(() => import('./tabs/RecipesTab.vue'))
const ProcessesTab = defineAsyncComponent(() => import('./tabs/ProcessesTab.vue'))
const ConsumablesTab = defineAsyncComponent(() => import('./tabs/ConsumablesTab.vue'))
const UnitsTab = defineAsyncComponent(() => import('./tabs/UnitsTab.vue'))
const CategoriesTab = defineAsyncComponent(() => import('./tabs/CategoriesTab.vue'))
const RoomsTab = defineAsyncComponent(() => import('./tabs/RoomsTab.vue')) // Додано для вкладки кімнат
const SupplyTab = defineAsyncComponent(() => import('./tabs/SupplyTab.vue'))

const props = defineProps({
  currentTab: { type: String, required: true }
})

const { fetchData, loading } = useWarehouse()

// --- ДОДАЄМО В ОБ'ЄКТ ---
const tabs = {
    stock: StockTab, // <-- Нова вкладка
    products: ProductsTab,
    recipes: RecipesTab,
    ingredients: IngredientsTab,
    processes: ProcessesTab,
    consumables: ConsumablesTab,
    units: UnitsTab,
    categories: CategoriesTab,
    rooms: RoomsTab, // <-- Додано для вкладки кімнат
    supplies: SupplyTab // <-- Додано для вкладки постачання

}

// Об'єкт для заголовків, щоб не писати їх в App.vue
const tabTitles = {
  supplies: '🚚 Постачання',
  stock: '📋 Залишки на складі',
  products: '📦 Товари',
  recipes: '📖 Рецепти та техкарти',
  ingredients: '🌶️ Інгредієнти',
  processes: '⚙️ Процеси приготування',
  consumables: '🥤 Витратні матеріали',
  units: '📏 Одиниці виміру',
  categories: '🏷️ Категорії',
  rooms: '🚪 Кімнати та групи',
}

onMounted(() => {
    fetchData()
})
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    <header class="flex justify-between items-center mb-8">
      <h2 class="text-3xl font-bold text-gray-800">{{ tabTitles[props.currentTab] || '📦 Управління складом' }}</h2>
      <button @click="fetchData" class="text-blue-600 hover:bg-blue-100 p-3 rounded-full transition-colors">
        <i class="fas fa-sync-alt" :class="{'fa-spin': loading}"></i>
      </button>
    </header>

    <component :is="tabs[props.currentTab]" />
    
  </div>
</template>