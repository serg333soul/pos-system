<script setup>
import { computed } from 'vue'

const props = defineProps({ product: Object })
// emit видаляємо, бо обробка кліку йде в батьківському компоненті через @click нативного div

const productIcon = computed(() => {
  const name = props.product.name.toLowerCase()
  const cat = props.product.category?.name?.toLowerCase() || ''
  if (name.includes('кава') || name.includes('еспресо') || cat.includes('напої')) return 'fas fa-mug-hot'
  if (name.includes('чай')) return 'fas fa-leaf'
  if (name.includes('торт') || name.includes('десерт') || cat.includes('десерти')) return 'fas fa-birthday-cake'
  if (name.includes('круасан')) return 'fas fa-bread-slice'
  return 'fas fa-box'
})

const cardColor = computed(() => {
  const cat = props.product.category?.slug || ''
  if (cat === 'hot-drinks') return 'bg-orange-50 text-orange-600 border-orange-100'
  if (cat === 'desserts') return 'bg-pink-50 text-pink-600 border-pink-100'
  return 'bg-white text-gray-700 border-gray-100'
})

const hasOptions = computed(() => {
    return props.product.has_variants || (props.product.modifier_groups && props.product.modifier_groups.length > 0)
})
</script>

<template>
  <div class="relative group cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl rounded-2xl border overflow-hidden bg-white">
    <div class="h-32 flex items-center justify-center text-5xl transition-transform group-hover:scale-110" :class="cardColor">
      <i :class="productIcon"></i>
    </div>

    <div class="p-4">
      <div v-if="product.category" class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
        {{ product.category.name }}
      </div>
      
      <h3 class="font-bold text-lg text-gray-800 leading-tight mb-2">{{ product.name }}</h3>
      
      <div class="flex justify-between items-center mt-3">
        <div class="flex flex-col">
            <span v-if="product.has_variants" class="text-xs text-gray-400">від</span>
            <span class="text-xl font-bold text-gray-900">{{ product.price }} ₴</span>
        </div>
        
        <button class="w-8 h-8 rounded-full flex items-center justify-center transition shadow-lg"
            :class="hasOptions ? 'bg-purple-600 hover:bg-purple-700 text-white' : 'bg-gray-900 hover:bg-green-500 text-white'">
          <i class="fas" :class="hasOptions ? 'fa-sliders-h text-xs' : 'fa-plus text-xs'"></i>
        </button>
      </div>
    </div>
  </div>
</template>