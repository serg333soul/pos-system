<script setup>
import { ref, onMounted, defineAsyncComponent } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// --- НОВИЙ ІМПОРТ ---
const StockTab = defineAsyncComponent(() => import('./tabs/StockTab.vue'))

const ProductsTab = defineAsyncComponent(() => import('./tabs/ProductsTab.vue'))
const IngredientsTab = defineAsyncComponent(() => import('./tabs/IngredientsTab.vue'))
const RecipesTab = defineAsyncComponent(() => import('./tabs/RecipesTab.vue'))
const ProcessesTab = defineAsyncComponent(() => import('./tabs/ProcessesTab.vue'))
const ConsumablesTab = defineAsyncComponent(() => import('./tabs/ConsumablesTab.vue'))
const UnitsTab = defineAsyncComponent(() => import('./tabs/UnitsTab.vue'))
const CategoriesTab = defineAsyncComponent(() => import('./tabs/CategoriesTab.vue'))

// Змінимо дефолтну вкладку на 'stock'
const activeTab = ref('stock')
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
    categories: CategoriesTab
}

onMounted(() => {
    fetchData()
})
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    <div class="flex justify-between items-center mb-8">
      <h2 class="text-3xl font-bold text-gray-800">📦 Управління складом</h2>
      <button @click="fetchData" class="text-blue-600 hover:bg-blue-50 p-2 rounded-full">
        <i class="fas fa-sync-alt" :class="{'fa-spin': loading}"></i>
      </button>
    </div>

    <div class="flex space-x-1 bg-gray-200 p-1 rounded-xl w-fit mb-8 overflow-x-auto">
      <button @click="activeTab='stock'" :class="activeTab==='stock'?'bg-white text-green-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-clipboard-check mr-2"></i>Залишки</button>
      
      <button @click="activeTab='recipes'" :class="activeTab==='recipes'?'bg-white text-orange-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-book-open mr-2"></i>Рецепти</button>
      <button @click="activeTab='products'" :class="activeTab==='products'?'bg-white text-purple-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Товари</button>
      <button @click="activeTab='processes'" :class="activeTab==='processes'?'bg-white text-indigo-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-tasks mr-2"></i>Процеси</button>
      
      <button @click="activeTab='ingredients'" :class="activeTab==='ingredients'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Інгрідієнти</button>
      <button @click="activeTab='consumables'" :class="activeTab==='consumables'?'bg-white text-teal-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-box-open mr-2"></i>Витратні матеріали</button>
      
      <button @click="activeTab='units'" :class="activeTab==='units'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Одиниці</button>
      <button @click="activeTab='categories'" :class="activeTab==='categories'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Категорії</button>
    </div>

    <component :is="tabs[activeTab]" />
    
  </div>
</template>