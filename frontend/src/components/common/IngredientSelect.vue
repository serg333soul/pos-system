<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: [String, Number], // ID інгредієнта
  ingredients: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Оберіть інгредієнт...' }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const searchQuery = ref('')
const containerRef = ref(null)

const selectedName = computed(() => {
  if (!props.modelValue) return ''
  const found = props.ingredients.find(i => i.id === props.modelValue)
  return found ? found.name : ''
})

const filteredList = computed(() => {
  if (!searchQuery.value) return props.ingredients
  const lower = searchQuery.value.toLowerCase()
  return props.ingredients.filter(i => i.name.toLowerCase().includes(lower))
})

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    searchQuery.value = ''
  }
}

const selectItem = (id) => {
  emit('update:modelValue', id)
  isOpen.value = false
}

// Click outside logic
const handleClickOutside = (event) => {
  if (containerRef.value && !containerRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div class="relative w-full" ref="containerRef">
    <div 
      @click="toggleDropdown"
      class="border rounded bg-white flex items-center justify-between cursor-pointer px-2 py-1.5 min-h-[38px] transition-colors hover:border-purple-300"
      :class="isOpen ? 'border-purple-500 ring-1 ring-purple-200' : 'border-gray-200'"
    >
      <span v-if="selectedName" class="text-sm text-gray-800 font-medium truncate">{{ selectedName }}</span>
      <span v-else class="text-sm text-gray-400 truncate">{{ placeholder }}</span>
      
      <i class="fas fa-chevron-down text-xs text-gray-400 transition-transform duration-200" :class="{'rotate-180': isOpen}"></i>
    </div>

    <div v-if="isOpen" class="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-xl max-h-60 overflow-hidden flex flex-col animate-fade-in-down">
      
      <div class="p-2 border-b bg-gray-50">
        <input 
          v-model="searchQuery" 
          class="w-full text-sm border border-gray-300 rounded px-2 py-1 outline-none focus:border-purple-500"
          placeholder="Пошук..." 
          @click.stop
        >
      </div>

      <div class="overflow-y-auto custom-scrollbar flex-1">
        <div v-if="filteredList.length === 0" class="p-3 text-xs text-gray-400 text-center">
          Нічого не знайдено
        </div>
        
        <div 
          v-for="item in filteredList" 
          :key="item.id"
          @click="selectItem(item.id)"
          class="px-3 py-2 text-sm cursor-pointer hover:bg-purple-50 transition-colors flex justify-between items-center group"
          :class="item.id === modelValue ? 'bg-purple-50 text-purple-700 font-bold' : 'text-gray-700'"
        >
          <span>{{ item.name }}</span>
          <span class="text-[10px] text-gray-400 group-hover:text-purple-400 bg-gray-100 group-hover:bg-white px-1 rounded">
             {{ item.stock_quantity }} {{ item.unit?.symbol }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-down {
  animation: fadeInDown 0.2s ease-out;
}
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
/* Scrollbar styles (optional global) */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 4px; }
</style>