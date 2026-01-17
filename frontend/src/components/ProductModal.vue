<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: Boolean,
  product: Object 
})

const emit = defineEmits(['close', 'add-to-cart'])

const selectedVariant = ref(null)
const selectedModifiers = ref({}) 
const selectedProcesses = ref({}) // <-- НОВЕ: Зберігаємо вибір процесів (key: group_id, value: option_name)

// --- Ініціалізація при ВІДКРИТТІ вікна ---
watch(() => props.isOpen, (isOpen) => {
  if (isOpen && props.product) {
    // 1. Скидаємо вибір
    selectedVariant.value = null
    selectedModifiers.value = {}
    selectedProcesses.value = {} // <-- Скидаємо процеси

    // 2. АВТО-ВИБІР Варіанту (перший/найдешевший)
    if (props.product.variants && props.product.variants.length > 0) {
      const sorted = [...props.product.variants].sort((a, b) => a.price - b.price)
      selectedVariant.value = sorted[0]
    }

    // 3. АВТО-ВИБІР Модифікаторів (якщо required)
    if (props.product.modifier_groups) {
      props.product.modifier_groups.forEach(group => {
        if (group.is_required && group.modifiers.length > 0) {
          selectedModifiers.value[group.id] = group.modifiers[0].id
        }
      })
    }

    // 4. НОВЕ: АВТО-ВИБІР Процесів (завжди обираємо перший варіант за замовчуванням)
    // Це пришвидшує роботу касира: "Під еспресо" стоїть за замовчуванням
    if (props.product.process_groups) {
        props.product.process_groups.forEach(pg => {
            if (pg.options && pg.options.length > 0) {
                selectedProcesses.value[pg.id] = pg.options[0].name
            }
        })
    }
  }
})

const currentPrice = computed(() => {
  if (!props.product) return 0
  let price = 0
  
  if (props.product.has_variants && selectedVariant.value) {
    price += selectedVariant.value.price
  } else {
    price += props.product.price
  }
  
  if (props.product.modifier_groups) {
    props.product.modifier_groups.forEach(group => {
      const modId = selectedModifiers.value[group.id]
      if (modId) {
        const mod = group.modifiers.find(m => m.id === modId)
        if (mod) price += mod.price_change
      }
    })
  }
  
  return price
})

const handleAddToCart = () => {
  if (props.product.has_variants && !selectedVariant.value) {
      alert("Будь ласка, оберіть розмір/варіант")
      return
  }

  const payload = {
    product: props.product,
    variant_id: selectedVariant.value ? selectedVariant.value.id : null,
    modifiers: Object.values(selectedModifiers.value).map(id => ({ modifier_id: id })),
    finalPrice: currentPrice.value,
    generatedName: generateName() 
  }
  emit('add-to-cart', payload)
  emit('close')
}

// --- ГЕНЕРАЦІЯ НАЗВИ ДЛЯ ЧЕКУ ---
const generateName = () => {
  let name = props.product.name
  
  // Додаємо варіант (L, M, 250г...)
  if (selectedVariant.value) {
    name += ` (${selectedVariant.value.name})`
  }

  // НОВЕ: Додаємо процеси (Помол: Під еспресо)
  // Ми просто додаємо їх у рядок назви, щоб бариста бачив це на чеку/екрані
  const processValues = Object.values(selectedProcesses.value)
  if (processValues.length > 0) {
      name += ` [${processValues.join(', ')}]`
  }

  return name
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="emit('close')"></div>

    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg relative overflow-hidden flex flex-col max-h-[90vh] animate-fade-in-up">
      
      <div class="p-6 bg-gray-50 border-b flex justify-between items-start">
        <div>
           <div class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">
             {{ product.category?.name || 'Товар' }}
           </div>
           <h2 class="text-3xl font-bold text-gray-800 leading-none">{{ product.name }}</h2>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 bg-white p-2 rounded-full shadow-sm hover:shadow transition">
          <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6 custom-scrollbar">
        
        <div v-if="product.has_variants && product.variants.length > 0">
          <label class="block text-sm font-bold text-gray-900 mb-3">Оберіть розмір/вагу:</label>
          <div class="grid grid-cols-3 gap-3">
            <button 
              v-for="variant in product.variants" 
              :key="variant.id"
              @click="selectedVariant = variant"
              class="py-3 px-2 rounded-xl border-2 transition-all flex flex-col items-center justify-center gap-1"
              :class="selectedVariant?.id === variant.id ? 'border-purple-600 bg-purple-50 text-purple-700' : 'border-gray-200 hover:border-gray-300 text-gray-600'"
            >
              <span class="font-bold">{{ variant.name }}</span>
              <span class="text-xs">{{ variant.price }} ₴</span>
            </button>
          </div>
        </div>

        <div v-if="product.process_groups && product.process_groups.length > 0" class="space-y-4">
            <div v-for="pg in product.process_groups" :key="pg.id" class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                <label class="block text-sm font-bold text-indigo-900 mb-2">
                    {{ pg.name }}
                </label>
                <div class="flex flex-wrap gap-2">
                    <button 
                        v-for="opt in pg.options" 
                        :key="opt.id"
                        @click="selectedProcesses[pg.id] = opt.name"
                        class="px-4 py-2 rounded-lg text-sm font-bold transition-all shadow-sm border"
                        :class="selectedProcesses[pg.id] === opt.name ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-white/80'"
                    >
                        {{ opt.name }}
                    </button>
                </div>
            </div>
        </div>

        <div v-if="product.modifier_groups && product.modifier_groups.length > 0" class="space-y-4">
          <div v-for="group in product.modifier_groups" :key="group.id" class="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <label class="block text-sm font-bold text-gray-700 mb-2">
              {{ group.name }} <span v-if="!group.is_required" class="text-gray-400 font-normal text-xs">(Опціонально)</span>
            </label>
            
            <div class="flex flex-wrap gap-2">
              <button 
                v-for="mod in group.modifiers" 
                :key="mod.id"
                @click="selectedModifiers[group.id] = mod.id"
                class="px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm border"
                :class="selectedModifiers[group.id] === mod.id ? 'bg-gray-800 text-white border-gray-800' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-100'"
              >
                {{ mod.name }}
                <span v-if="mod.price_change > 0" class="text-xs opacity-70 ml-1">+{{ mod.price_change }}</span>
              </button>
            </div>
          </div>
        </div>

      </div>

      <div class="p-6 border-t bg-gray-50 flex justify-between items-center">
        <div class="text-2xl font-bold text-gray-900">
          {{ currentPrice }} ₴
        </div>
        <button 
          @click="handleAddToCart"
          class="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-purple-700 transition shadow-lg shadow-purple-200 active:scale-95 flex items-center gap-2"
        >
          <i class="fas fa-cart-plus"></i> Додати
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.3s ease-out;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
/* Додаємо стилі для скролбару, якщо їх ще немає в глобальних */
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 20px; }
</style>