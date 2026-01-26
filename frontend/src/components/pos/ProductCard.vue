<script setup>
import { computed } from 'vue'

const props = defineProps({ 
  product: { type: Object, required: true } 
})

// Явно вказуємо, що компонент реагує на клік, хоча це native event
const emit = defineEmits(['click'])

// Логіка іконок (View Logic)
const productIcon = computed(() => {
  const name = props.product.name?.toLowerCase() || ''
  const cat = props.product.category?.name?.toLowerCase() || ''
  
  if (name.includes('кава') || name.includes('еспресо') || cat.includes('напої')) return 'fas fa-mug-hot'
  if (name.includes('чай')) return 'fas fa-leaf'
  if (name.includes('торт') || name.includes('десерт') || cat.includes('десерти')) return 'fas fa-birthday-cake'
  if (name.includes('круасан')) return 'fas fa-bread-slice'
  
  return 'fas fa-box'
})

// Логіка кольорів (View Logic)
const cardColor = computed(() => {
  const slug = props.product.category?.slug || ''
  const colors = {
    'hot-drinks': 'bg-orange-50 text-orange-600 border-orange-100',
    'desserts': 'bg-pink-50 text-pink-600 border-pink-100'
  }
  return colors[slug] || 'bg-white text-gray-700 border-gray-100'
})

const hasOptions = computed(() => {
  return props.product.has_variants || (props.product.modifier_groups && props.product.modifier_groups.length > 0)
})

// Логіка ціни: показуємо мінімальну, якщо є варіанти
const displayPrice = computed(() => {
  if (props.product.has_variants && props.product.variants?.length > 0) {
    const prices = props.product.variants.map(v => v.price)
    return Math.min(...prices)
  }
  return props.product.price
})
</script>

<template>
  <div 
    @click="emit('click', product)"
    class="relative group cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl rounded-2xl border overflow-hidden bg-white"
  >
    <div class="h-32 flex items-center justify-center text-5xl transition-transform group-hover:scale-110" :class="cardColor">
      <i :class="productIcon"></i>
    </div>

    <div class="p-4">
      <div v-if="product.category" class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
        {{ product.category.name }}
      </div>
      
      <h3 class="font-bold text-lg text-gray-800 leading-tight mb-2 line-clamp-2 min-h-[3.5rem]">
        {{ product.name }}
      </h3>
      
      <div class="flex justify-between items-center mt-3">
        <div class="flex flex-col">
            <span v-if="product.has_variants" class="text-xs text-gray-400">від</span>
            <span class="text-xl font-bold text-gray-900">{{ displayPrice }} ₴</span>
        </div>
        
        <button class="w-8 h-8 rounded-full flex items-center justify-center transition shadow-lg"
            :class="hasOptions ? 'bg-purple-600 hover:bg-purple-700 text-white' : 'bg-gray-900 hover:bg-green-500 text-white'">
          <i class="fas" :class="hasOptions ? 'fa-sliders-h text-xs' : 'fa-plus text-xs'"></i>
        </button>
      </div>
    </div>
  </div>
</template>