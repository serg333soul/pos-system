<script setup>
import { ref, computed, watch } from 'vue';
import { useCart } from '@/composables/useCart';

const props = defineProps({
  group: {
    type: Object,
    required: true // Об'єкт ProductRoom з вкладеним списком products [3]
  },
  isOpen: Boolean
});

const emit = defineEmits(['close']);
const { addToCart } = useCart(); // [4]

// Стан вибору всередині "кімнати" [5]
const selectedProduct = ref(null);
const selectedProcess = ref(null);
const selectedMaterial = ref(null);
const quantity = ref(1);

// Скидання вибору при відкритті іншої кімнати
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    selectedProduct.ref = null;
    selectedProcess.value = null;
    selectedMaterial.value = null;
    quantity.value = 1;
  }
});

// Розрахунок підсумкової ціни для кнопки [6]
const totalPrice = computed(() => {
  if (!selectedProduct.value) return 0;
  let price = selectedProduct.value.price || 0;
  
  // Додаємо вартість матеріалу (якщо це передбачено бізнес-логікою)
  if (selectedMaterial.value) {
    // Матеріали часто мають собівартість, але тут ми можемо додати ціну продажу
    price += selectedMaterial.value.cost_per_unit || 0; 
  }
  
  return (price * quantity.value).toFixed(2);
});

// Перевірка, чи можна додати в кошик
const canConfirm = computed(() => {
  return selectedProduct.value !== null;
});

const handleConfirm = () => {
  if (!selectedProduct.value) return;

  // Формуємо Payload для Order Service [7]
  const payload = {
    product_id: selectedProduct.value.id,
    variant_id: null, // Кімната працює з простими товарами
    quantity: quantity.value,
    
    // Динамічна назва для чека: "Кава Delicate 250г (Мелена) + Пакет"
    name: `${selectedProduct.value.name}${selectedProcess.value ? ' (' + selectedProcess.value.name + ')' : ''}${selectedMaterial.value ? ' + ' + selectedMaterial.value.name : ''}`,
    
    price: selectedProduct.value.price, // Базова ціна товару
    
    // Передаємо матеріал як модифікатор для списання зі складу [7, 8]
    modifiers: []
  };

  if (selectedMaterial.value) {
    payload.modifiers.push({
      modifier_id: selectedMaterial.value.id,
      quantity: 1
    });
  }

  addToCart(payload); // [9]
  emit('close');
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-white w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      
      <!-- Заголовок Кімнати -->
      <div class="px-6 py-4 bg-purple-600 text-white flex justify-between items-center">
        <h2 class="text-xl font-bold">{{ group.name }}</h2>
        <button @click="emit('close')" class="text-2xl hover:rotate-90 transition-transform">×</button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6">
        <!-- 1. Вибір товару (Фасування) -->
        <section>
          <h3 class="text-sm font-bold text-gray-400 uppercase mb-3">Оберіть фасування:</h3>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <button 
              v-for="p in group.products" 
              :key="p.id"
              @click="selectedProduct = p; selectedProcess = null; selectedMaterial = null"
              class="p-4 rounded-2xl border-2 transition-all text-center relative"
              :class="selectedProduct?.id === p.id ? 'border-purple-600 bg-purple-50 text-purple-700' : 'border-gray-100 hover:border-gray-200'"
            >
              <div class="font-bold">{{ p.name }}</div>
              <div class="text-sm opacity-70">{{ p.price }} ₴</div>
            </button>
          </div>
        </section>

        <!-- 2. Процеси (якщо є у вибраного товару) [10, 11] -->
        <section v-if="selectedProduct?.process_groups?.length">
          <h3 class="text-sm font-bold text-gray-400 uppercase mb-3">Приготування (Процес):</h3>
          <div v-for="pg in selectedProduct.process_groups" :key="pg.id" class="mb-4">
            <div class="flex flex-wrap gap-2">
              <button 
                v-for="opt in pg.options" 
                :key="opt.id"
                @click="selectedProcess = opt"
                class="px-4 py-2 rounded-xl border text-sm font-medium transition-all"
                :class="selectedProcess?.id === opt.id ? 'bg-gray-800 text-white border-gray-800' : 'bg-white text-gray-600 hover:bg-gray-50'"
              >
                {{ opt.name }}
              </button>
            </div>
          </div>
        </section>

        <!-- 3. Матеріали (Пакет тощо) [12, 13] -->
        <section v-if="selectedProduct?.consumables?.length">
          <h3 class="text-sm font-bold text-gray-400 uppercase mb-3">Матеріали / Упаковка:</h3>
          <div class="flex flex-wrap gap-2">
            <button 
              v-for="c in selectedProduct.consumables" 
              :key="c.consumable_id"
              @click="selectedMaterial = (selectedMaterial?.id === c.consumable_id ? null : {id: c.consumable_id, name: c.consumable_name})"
              class="px-4 py-2 rounded-xl border text-sm font-medium transition-all"
              :class="selectedMaterial?.id === c.consumable_id ? 'bg-green-600 text-white border-green-600' : 'bg-white text-gray-600 hover:bg-gray-50'"
            >
              + {{ c.consumable_name }}
            </button>
          </div>
        </section>

        <!-- 4. Кількість -->
        <section v-if="selectedProduct" class="flex items-center justify-between bg-gray-50 p-4 rounded-2xl">
          <span class="font-bold">Кількість:</span>
          <div class="flex items-center gap-4">
            <button @click="quantity > 1 && quantity--" class="w-10 h-10 rounded-full bg-white shadow-sm border flex items-center justify-center text-xl">-</button>
            <span class="text-xl font-bold w-8 text-center">{{ quantity }}</span>
            <button @click="quantity++" class="w-10 h-10 rounded-full bg-white shadow-sm border flex items-center justify-center text-xl">+</button>
          </div>
        </section>
      </div>

      <!-- Кнопка додавання -->
      <div class="p-6 border-t bg-gray-50">
        <button 
          @click="handleConfirm"
          :disabled="!canConfirm"
          class="w-full py-4 bg-purple-600 text-white rounded-2xl font-bold text-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-200"
        >
          Додати в кошик — {{ totalPrice }} ₴
        </button>
      </div>
    </div>
  </div>
</template>