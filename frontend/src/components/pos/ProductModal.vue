<script setup>
import { ref, computed, watch } from 'vue'
import { useCart } from '@/composables/useCart'
import { useWarehouse } from '@/composables/useWarehouse'
import { useSupplies } from '@/composables/useSupplies' // 🔥 ДОДАНО: Для роботи з партіями

const props = defineProps({
  isOpen: Boolean,
  product: Object 
})

const emit = defineEmits(['close'])

const { cartItems, reservedResources, addToCart } = useCart()
const warehouse = useWarehouse()
const { fetchAvailableBatches } = useSupplies() // 🔥 ДОДАНО

const selectedVariant = ref(null)
const selectedModifiers = ref({}) 
const selectedProcesses = ref({}) 

// --- 🔥 НОВИЙ СТАН ДЛЯ ПАРТІЙ (MANUAL BATCH) ---
const isManualBatch = ref(false)
const availableBatches = ref([])
const selectedBatchId = ref(null)
const isLoadingBatches = ref(false)

// --- Ініціалізація (Reset & Defaults) ---
watch(() => props.isOpen, (isOpen) => {
  if (isOpen && props.product) {
    selectedVariant.value = null
    selectedModifiers.value = {}
    selectedProcesses.value = {} 
    
    // 🔥 Скидання ручного режиму при новому відкритті
    isManualBatch.value = false
    availableBatches.value = []
    selectedBatchId.value = null

    // Auto-select Variant (cheapest)
    if (props.product.variants && props.product.variants.length > 0) {
      const sorted = [...props.product.variants].sort((a, b) => a.price - b.price)
      selectedVariant.value = sorted[0]
    }

    // Auto-select Required Modifiers
    if (props.product.modifier_groups) {
      props.product.modifier_groups.forEach(group => {
        if (group.is_required && group.modifiers.length > 0) {
          selectedModifiers.value[group.id] = group.modifiers[0].id
        }
      })
    }

    // Auto-select First Process Option
    if (props.product.process_groups) {
        props.product.process_groups.forEach(pg => {
            if (pg.options && pg.options.length > 0) {
                selectedProcesses.value[pg.id] = pg.options[0].name
            }
        })
    }
  }
})

// --- 🔥 ЗАВАНТАЖЕННЯ ПАРТІЙ ПРИ УВІМКНЕННІ ТУМБЛЕРА ---
watch([isManualBatch, selectedVariant], async ([isManual, currentVariant]) => {
    if (!isManual || !props.product) return;

    isLoadingBatches.value = true
    selectedBatchId.value = null

    // Визначаємо, що саме ми шукаємо (варіант чи простий товар)
    let entityType = props.product.has_variants ? 'variant' : 'product'
    let entityId = props.product.has_variants ? currentVariant?.id : props.product.id

    if (entityId) {
        availableBatches.value = await fetchAvailableBatches(entityType, entityId)
    } else {
        availableBatches.value = []
    }
    
    isLoadingBatches.value = false
})


const canAddToCart = computed(() => {
  if (!props.product) return false;

  // 🔥 Якщо увімкнено ручний режим, касир ЗОБОВ'ЯЗАНИЙ вибрати партію
  if (isManualBatch.value && !selectedBatchId.value) {
      return false;
  }

  // ЛОГІКА ДЛЯ СКЛАДНИХ ТОВАРІВ
  if (props.product.has_variants) {
    if (!selectedVariant.value) return false;
    
    // Якщо ручний режим - перевіряємо чи є вибрана партія і чи вистачає там 1 шт
    if (isManualBatch.value && selectedBatchId.value) {
        const batch = availableBatches.value.find(b => b.batch_id === selectedBatchId.value)
        return batch && batch.remaining_quantity >= 1;
    }
    
    return getAvailableStock(selectedVariant.value) >= 1;
  }

  // ЛОГІКА ДЛЯ ПРОСТИХ ТОВАРІВ
  if (props.product.track_stock) {
      if (isManualBatch.value && selectedBatchId.value) {
          const batch = availableBatches.value.find(b => b.batch_id === selectedBatchId.value)
          return batch && batch.remaining_quantity >= 1;
      }
      return (props.product.stock_quantity || 0) >= 1;
  }

  return true;
})

const getAvailableStock = (variant) => {
    if (!variant || !props.product) return 0;

    if (props.product.track_stock) {
        const inCart = cartItems.value
            .filter(i => i.variant_id === variant.id)
            .reduce((sum, i) => sum + i.quantity, 0);
        return Math.max(0, (variant.stock_quantity || 0) - inCart);
    }

    let maxPossible = Infinity;

    if (variant.master_recipe_id) {
        const recipe = warehouse.recipes.value.find(r => r.id === variant.master_recipe_id);
        recipe?.items?.forEach(rItem => {
            const inStore = warehouse.ingredients.value.find(i => i.id === rItem.ingredient_id);
            if (inStore) {
                const reserved = reservedResources.value.ingredients[rItem.ingredient_id] || 0;
                const available = Math.max(0, inStore.stock_quantity - reserved);
                
                let qtyPerOne = rItem.quantity;
                if (rItem.is_percentage) {
                    qtyPerOne = (rItem.quantity / 100) * (variant.output_weight || 0);
                }
                
                if (qtyPerOne > 0) {
                    const possible = Math.floor(available / qtyPerOne);
                    if (possible < maxPossible) maxPossible = possible;
                }
            }
        });
    }
    
    return maxPossible === Infinity ? 0 : maxPossible;
}

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

const handleConfirm = () => {
  if (props.product.has_variants && !selectedVariant.value) {
    alert("Оберіть варіант товару");
    return;
  }

  const payload = {
    product_id: props.product.id,
    quantity: 1,
    modifiers: Object.values(selectedModifiers.value).map(id => ({ modifier_id: id })),
    
    variant_id: props.product.has_variants ? selectedVariant.value.id : null,
    name: props.product.has_variants 
            ? `${props.product.name} (${selectedVariant.value.name})` 
            : props.product.name,
    price: props.product.has_variants 
            ? selectedVariant.value.price 
            : props.product.price,
            
    // 🔥 ДОДАНО: Передаємо ID партії в кошик, якщо увімкнено ручний режим
    batch_id: (isManualBatch.value && selectedBatchId.value) ? selectedBatchId.value : null
  };

  addToCart(payload); 
  emit('close');
}

// Допоміжна функція форматування дати
const formatDate = (dateStr) => {
    if (!dateStr) return 'Невідома дата'
    const d = new Date(dateStr)
    return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth()+1).toString().padStart(2, '0')}.${d.getFullYear()}`
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
              <div 
                  v-for="variant in product.variants" 
                  :key="variant.id"
                  @click="getAvailableStock(variant) > 0 ? selectedVariant = variant : null"
                  class="py-3 px-2 rounded-xl border-2 transition-all flex flex-col items-center justify-center gap-1 relative overflow-hidden"
                  :class="[
                      selectedVariant?.id === variant.id ? 'border-purple-600 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600',
                      getAvailableStock(variant) < 1 
                          ? 'opacity-40 cursor-not-allowed grayscale pointer-events-none' 
                          : 'hover:border-gray-300 cursor-pointer'
                  ]"
              >
                  <span class="font-bold text-center leading-tight">{{ variant.name }}</span>
                  <span class="text-sm font-medium">{{ variant.price }} ₴</span>
    
                  <div 
                      class="text-[10px] px-1.5 py-0.5 rounded-full mt-1 font-bold"
                      :class="getAvailableStock(variant) > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                  >
                      {{ getAvailableStock(variant) > 0 ? `Доступно: ${getAvailableStock(variant)}` : 'Вичерпано' }}
                  </div>
              </div>
          </div>
        </div>

        <div v-if="product.track_stock || (product.has_variants && selectedVariant && !selectedVariant.master_recipe_id)" 
             class="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <div class="flex items-center justify-between mb-2">
                <div>
                    <label class="block text-sm font-bold text-blue-900">Спеціальне списання</label>
                    <p class="text-xs text-blue-700 mt-0.5">Вимкнено = Автоматичний облік (FIFO/WAC)</p>
                </div>
                
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="isManualBatch" class="sr-only peer">
                  <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
            </div>

            <div v-if="isManualBatch" class="mt-4 animate-fade-in-up">
                <div v-if="isLoadingBatches" class="text-sm text-blue-600 text-center py-2">
                    <i class="fas fa-spinner fa-spin mr-2"></i> Завантаження партій...
                </div>
                <div v-else-if="availableBatches.length === 0" class="text-sm text-red-600 p-2 bg-red-50 rounded border border-red-100">
                    Активних партій з залишком не знайдено. Потрібно створити постачання.
                </div>
                <div v-else>
                    <label class="block text-xs font-bold text-blue-800 uppercase mb-1">Оберіть партію складу:</label>
                    <select v-model="selectedBatchId" class="w-full border-blue-200 bg-white p-2.5 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500">
                        <option :value="null" disabled>-- Виберіть партію --</option>
                        <option v-for="batch in availableBatches" :key="batch.batch_id" :value="batch.batch_id">
                            📦 {{ formatDate(batch.supply_date) }} | Залишок: {{ batch.remaining_quantity }} | Вхідна: {{ batch.cost_per_unit }}₴
                        </option>
                    </select>
                </div>
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
            @click="handleConfirm"
            :disabled="!canAddToCart"
            class="flex-1 bg-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed ml-4"
        >
            Додати в кошик
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-up { animation: fadeInUp 0.3s ease-out; }
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>