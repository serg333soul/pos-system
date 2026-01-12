<script setup>
import { computed } from 'vue'

const props = defineProps({
  product: Object
})

const emit = defineEmits(['add-to-cart'])

// Функція для вибору іконки залежно від категорії (або назви)
const productIcon = computed(() => {
  const name = props.product.name.toLowerCase()
  const cat = props.product.category?.name?.toLowerCase() || ''

  if (name.includes('кава') || name.includes('еспресо') || cat.includes('напої')) return 'fas fa-mug-hot'
  if (name.includes('чай')) return 'fas fa-leaf'
  if (name.includes('торт') || name.includes('десерт') || cat.includes('десерти')) return 'fas fa-birthday-cake'
  if (name.includes('круасан')) return 'fas fa-bread-slice'
  
  return 'fas fa-box' // Стандартна іконка
})

// Колір залежно від категорії
const cardColor = computed(() => {
  const cat = props.product.category?.slug || ''
  if (cat === 'hot-drinks') return 'bg-orange-50 text-orange-600 border-orange-100'
  if (cat === 'desserts') return 'bg-pink-50 text-pink-600 border-pink-100'
  return 'bg-white text-gray-700 border-gray-100'
})
</script>

<template>
  <div 
    @click="emit('add-to-cart')"
    class="relative group cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl rounded-2xl border overflow-hidden bg-white"
  >
    <div class="h-32 flex items-center justify-center text-5xl transition-transform group-hover:scale-110" 
         :class="cardColor">
      <i :class="productIcon"></i>
    </div>

    <div class="p-4">
      <div v-if="product.category" class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
        {{ product.category.name }}
      </div>
      
      <h3 class="font-bold text-lg text-gray-800 leading-tight mb-2">{{ product.name }}</h3>
      
      <div class="flex justify-between items-center mt-3">
        <span class="text-xl font-bold text-gray-900">{{ product.price }} ₴</span>
        
        <button class="w-8 h-8 rounded-full bg-gray-900 text-white flex items-center justify-center hover:bg-green-500 transition shadow-lg">
          <i class="fas fa-plus text-xs"></i>
        </button>
      </div>
    </div>
  </div>
</template>