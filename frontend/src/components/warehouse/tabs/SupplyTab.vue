<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSupplies } from '@/composables/useSupplies'
import { useWarehouse } from '@/composables/useWarehouse'

// Додаємо emit на випадок, якщо батьківському компоненту треба знати, що постачання збережено
const emit = defineEmits(['saved'])

const warehouse = useWarehouse(); // 🔥 Отримуємо доступ до складу
const { supplies, fetchSupplies, createSupply, isLoading, suppliers, fetchSuppliers, addSupplier } = useSupplies()
const showSupplierModal = ref(false)
const newSupplier = ref({ name: '', phone: '', email: '', notes: '' })
// 1. Стан для відображення модального вікна
const showCreateModal = ref(false);
const expandedSupplyId = ref(null);

const toggleSupplyDetails = (id) => {
  // Якщо натискаємо на ту саму накладну — згортаємо, інакше — розгортаємо нову
  expandedSupplyId.value = expandedSupplyId.value === id ? null : id;
};

// 2. Функція ініціалізації форми
const resetForm = () => {
  form.value = {
    supplier_name: '',
    invoice_number: '',
    notes: '',
    items: []
  };
};

const form = ref({
  supplier_name: '',
  invoice_number: '',
  notes: '',
  items: [
    { entity_type: 'ingredient', entity_id: null, quantity: 1, cost_per_unit: 0 }
  ]
})

// Завантажуємо історію відразу при монтуванні компонента
onMounted(async () => {
  console.log("🚚 Завантаження історії постачань...");
  await fetchSupplies();
});

onMounted(() => {
  fetchSuppliers();
})

const handleSupplierChange = (e) => {
  if (e.target.value === 'new') {
    showSupplierModal.value = true;
    form.value.supplier_id = null; // Скидаємо вибір у селекті
  }
}

const saveNewSupplier = async () => {
  console.log("🚀 Спроба створення постачальника:", newSupplier.value);

  if (!newSupplier.value.name) {
    return alert("Назва постачальника обов'язкова!");
  }

  try {
    const result = await addSupplier(newSupplier.value);
    
    if (result) {
      console.log("✅ Постачальник створений:", result);
      // Автоматично вибираємо його в накладній
      form.value.supplier_id = result.id;
      // Закриваємо модалку
      showSupplierModal.value = false;
      // Очищаємо форму
      newSupplier.value = { name: '', phone: '', email: '', notes: '' };
    } else {
      alert("❌ Не вдалося створити постачальника. Перевірте консоль.");
    }
  } catch (err) {
    console.error("Критична помилка при створенні:", err);
    alert("❌ Помилка: " + err.message);
  }
}

// Допоміжна функція для форматування дати
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleString('uk-UA');
};

// 🔥 ОСНОВНА ФУНКЦІЯ ЗБЕРЕЖЕННЯ
const handleCreateSupply = async () => {
  // 1. Валідація на фронтенді
  if (form.value.items.length === 0) {
    return alert("Додайте хоча б один товар у накладну!");
  }

  // Перевірка, чи всі поля заповнені
  const isValid = form.value.items.every(item => item.entity_id && item.quantity > 0 && item.cost_per_unit > 0);
  if (!isValid) {
    return alert("Будь ласка, заповніть всі поля: назву, кількість та ціну для кожного рядка.");
  }

  try {
    // 2. Підготовка даних (Гарантуємо Integer для бекенду)
    const payload = {
      ...form.value,
      items: form.value.items.map(item => ({
        entity_type: item.entity_type,
        entity_id: parseInt(item.entity_id), // 🔥 КРИТИЧНО: перетворюємо в число
        quantity: parseFloat(item.quantity),
        cost_per_unit: parseFloat(item.cost_per_unit)
      }))
    };

    console.log("📤 Відправка постачання:", payload);

    // 3. Виклик сервісу
    const result = await createSupply(payload);
    
    if (result) {
      alert(`✅ Постачання #${result.id} успішно проведено!`);
      // Очищення форми
      form.value = { supplier_name: '', invoice_number: '', notes: '', items: [] };
      // Оновлюємо дані складу (залишки), щоб вони підтягнулися на Касу
      await warehouse.fetchWarehouseData(); 
    }
  } catch (err) {
    // 🔥 Якщо бекенд повернув помилку, ми її побачимо
    alert("❌ Помилка: " + err.message);
  }
};

const addItem = () => {
  form.value.items.push({ entity_type: 'ingredient', entity_id: null, quantity: 1, cost_per_unit: 0 })
}

const removeItem = (index) => {
  form.value.items.splice(index, 1)
}

// Допоміжна функція для отримання списку залежно від обраного типу
const getListForType = (type) => {
  if (type === 'ingredient') return warehouse.ingredients.value;
  if (type === 'consumable') return warehouse.consumables.value;
  
  return [];
};

const totalCost = computed(() => {
  return form.value.items.reduce((sum, item) => {
    return sum + (item.quantity * item.cost_per_unit)
  }, 0)
})

const submitSupply = async () => {
  // Базова валідація
  const hasInvalidItems = form.value.items.some(i => !i.entity_id || i.quantity <= 0)
  if (hasInvalidItems) {
    alert("Перевірте рядки: ID сутності не може бути порожнім, а кількість має бути > 0")
    return
  }

  isSubmitting.value = true
  try {
    await createSupply(form.value)
    alert("✅ Постачання успішно збережено!")
    
    // 🔥 ВИПРАВЛЕННЯ: Замість router.push() ми просто очищаємо форму для нової накладної
    form.value = {
      supplier_name: '',
      invoice_number: '',
      notes: '',
      items: [
        { entity_type: 'ingredient', entity_id: null, quantity: 1, cost_per_unit: 0 }
      ]
    }
    
    // Сповіщаємо батьківський компонент (якщо він захоче оновити загальну статистику)
    emit('saved')
    
  } catch (error) {
    alert("Помилка збереження. Перевірте консоль.")
  } finally {
    isSubmitting.value = false
  }
}
</script>
<template>
  <div class="p-6">
    <!-- Заголовок та кнопка створення -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-800">Історія постачань</h2>
        <p class="text-sm text-gray-500">Усі проведені прихідні накладні</p>
      </div>
      
      <button 
        @click="showCreateModal = true"
        class="bg-green-600 hover:bg-green-700 text-white px-6 py-2.5 rounded-xl font-bold shadow-lg shadow-green-100 transition flex items-center gap-2"
      >
        <span class="text-xl">+</span> Нове постачання
      </button>
    </div>

    <!-- ТАБЛИЦЯ ІСТОРІЇ -->
    <div class="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
      <table class="w-full text-left border-collapse">
        <thead class="bg-gray-50 text-gray-400 text-[10px] uppercase font-bold">
          <tr>
            <th class="p-4">ID / Дата</th>
            <th class="p-4">Постачальник</th>
            <th class="p-4">№ Накладної</th>
            <th class="p-4">Позицій</th>
            <th class="p-4 text-right">Сума</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <template v-for="s in supplies" :key="s.id">
            <!-- Основний рядок (додаємо клік та вказівник курсору) -->
            <tr 
              @click="toggleSupplyDetails(s.id)"
              class="hover:bg-gray-50/50 transition-colors cursor-pointer group"
              :class="{ 'bg-blue-50/30': expandedSupplyId === s.id }"
            >
              <td class="p-4">
                <div class="flex items-center gap-2">
                  <!-- Іконка стрілочки для візуалізації -->
                  <span class="text-[10px] transition-transform" :class="{ 'rotate-90': expandedSupplyId === s.id }">▶</span>
                  <div>
                    <div class="font-bold text-gray-700">#{{ s.id }}</div>
                    <div class="text-[10px] text-gray-400">{{ formatDate(s.created_at) }}</div>
                  </div>
                </div>
              </td>
              <td class="p-4 font-medium">{{ s.supplier?.name || s.supplier_name || '---' }}</td>
              <td class="p-4">
                <span class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs font-bold">
                  {{ s.invoice_number || 'б/н' }}
                </span>
              </td>
              <td class="p-4 text-gray-500">{{ s.items?.length || 0 }} од.</td>
              <td class="p-4 text-right font-bold text-green-600">{{ s.total_cost.toFixed(2) }} ₴</td>
            </tr>

            <!-- РОЗГОРНУТА ІНФОРМАЦІЯ (Вміст постачання) -->
            <tr v-if="expandedSupplyId === s.id" class="bg-gray-50/50">
              <td colspan="5" class="p-0">
                <div class="p-6 border-l-4 border-blue-400 ml-4 my-2">
                  <h4 class="text-xs font-black text-gray-400 uppercase mb-3 tracking-wider">Склад накладної:</h4>
                  
                  <div class="bg-white rounded-xl border border-gray-100 overflow-hidden shadow-sm">
                    <table class="w-full text-xs">
                      <thead class="bg-gray-100/50 text-gray-500 font-bold">
                        <tr>
                          <th class="p-2 text-left">Тип</th>
                          <th class="p-2 text-left">Найменування</th>
                          <th class="p-2 text-center">Кількість</th>
                          <th class="p-2 text-right">Ціна за од.</th>
                          <th class="p-2 text-right">Сума</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-gray-50">
                        <tr v-for="item in s.items" :key="item.id" class="hover:bg-gray-50/30">
                          <td class="p-2 italic text-gray-400">
                            {{ item.entity_name === 'ingredient' ? '🥦 Сировина' : (item.entity_name === 'consumable' ? '📦 Матеріал' : '🍹 Товар') }}
                          </td>
                          <td class="p-2 font-bold text-gray-700">{{ item.entity_name }}</td>
                          <td class="p-2 text-center">{{ item.quantity }}</td>
                          <td class="p-2 text-right text-gray-500">{{ item.cost_per_unit.toFixed(2) }} ₴</td>
                          <td class="p-2 text-right font-bold text-gray-800">
                            {{ (item.quantity * item.cost_per_unit).toFixed(2) }} ₴
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  
                  <!-- Нотатки накладної, якщо є -->
                  <div v-if="s.notes" class="mt-3 text-xs text-gray-500 italic">
                    <strong>Коментар:</strong> {{ s.notes }}
                  </div>
                </div>
              </td>
            </tr>
          </template>
          
          <tr v-if="supplies.length === 0 && !isLoading">
            <td colspan="5" class="p-12 text-center text-gray-400 italic">
              Історія постачань порожня. Натисніть "Нове постачання", щоб додати перший прихід.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div v-if="showCreateModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div class="bg-white rounded-3xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl transition-all scale-100">
        
        <!-- Header -->
        <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <div>
            <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
              🚚 Прихідна накладна
            </h3>
            <p class="text-xs text-gray-500">Заповніть дані про постачальника та перелік товарів</p>
          </div>
          <button @click="showCreateModal = false" class="text-gray-400 hover:text-gray-600 p-2 text-2xl">&times;</button>
        </div>

        <!-- Body (Scrollable) -->
        <div class="flex-1 overflow-y-auto p-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <!-- Поля накладної -->
            <div>
              <div>
              <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Постачальник</label>
              <select 
                v-model="form.supplier_id" 
                @change="handleSupplierChange"
                class="w-full border p-3 rounded-xl focus:ring-2 ring-green-100 outline-none"
              >
                <option :value="null">-- Оберіть постачальника --</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                <option value="new" class="text-green-600 font-bold">+ Створити нового постачальника</option>
              </select>
            </div>
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-400 uppercase mb-1">№ Накладної</label>
              <input v-model="form.invoice_number" type="text" placeholder="INV-2024-001" class="w-full border p-3 rounded-xl focus:ring-2 ring-green-100 outline-none">
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Коментар</label>
              <input v-model="form.notes" type="text" placeholder="Додаткова інформація..." class="w-full border p-3 rounded-xl focus:ring-2 ring-green-100 outline-none">
            </div>
          </div>

          <!-- Таблиця товарів у накладній -->
          <div class="border rounded-2xl overflow-hidden mb-4">
            <table class="w-full text-sm">
              <thead class="bg-gray-100 font-bold text-gray-600">
                <tr>
                  <th class="p-3 text-left">Тип</th>
                  <th class="p-3 text-left">Сутність (Інгредієнт/Товар)</th>
                  <th class="p-3 text-left w-32">Кількість</th>
                  <th class="p-3 text-left w-40">Ціна за од. (₴)</th>
                  <th class="p-3 text-right w-40">Сума</th>
                  <th class="p-3"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="(item, index) in form.items" :key="index" class="hover:bg-gray-50/30">
                  <td class="p-3">
                    <select v-model="item.entity_type" @change="item.entity_id = null" class="w-full border p-2 rounded-xl bg-white">
                      <option value="ingredient">🥦 Сировина</option>
                      <option value="consumable">📦 Матеріали</option>
                      <option value="variant">🍹 Товар/Варіант</option>
                    </select>
                  </td>
                  <td class="p-3">
                    <!-- Наш динамічний селектор зі списків Warehouse -->
                    <select v-model="item.entity_id" :disabled="!item.entity_type" class="w-full border p-2 rounded-xl bg-white disabled:bg-gray-50">
                      <option :value="null">-- Оберіть зі списку --</option>
                      <option v-for="obj in getListForType(item.entity_type)" :key="obj.id" :value="obj.id">
                        {{ obj.name || obj.display_name }} {{ obj.sku ? `(${obj.sku})` : '' }}
                      </option>
                    </select>
                  </td>
                  <td class="p-3">
                    <input v-model.number="item.quantity" type="number" step="0.001" class="w-full border p-2 rounded-xl text-center">
                  </td>
                  <td class="p-3">
                    <input v-model.number="item.cost_per_unit" type="number" step="0.01" class="w-full border p-2 rounded-xl text-right">
                  </td>
                  <td class="p-3 text-right font-bold text-gray-700">
                    {{ (item.quantity * item.cost_per_unit).toFixed(2) }} ₴
                  </td>
                  <td class="p-3 text-center">
                    <button @click="removeItem(index)" class="text-red-400 hover:text-red-600 p-2">&times;</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <button @click="addItem" class="text-green-600 font-bold text-sm hover:underline flex items-center gap-2 mb-4">
            + Додати рядок
          </button>
        </div>

        <!-- Footer -->
        <div class="p-6 border-t border-gray-100 flex justify-between items-center bg-gray-50/50">
          <div class="text-lg">
            <span class="text-gray-400">Разом:</span>
            <span class="ml-2 font-black text-2xl text-gray-800">{{ totalCost.toFixed(2) }} ₴</span>
          </div>
          <div class="flex gap-4">
            <button @click="showCreateModal = false" class="px-6 py-3 text-gray-500 font-bold hover:bg-gray-100 rounded-xl transition">
              Скасувати
            </button>
            <button 
              @click="handleCreateSupply"
              :disabled="isLoading || form.items.length === 0"
              class="px-8 py-3 bg-green-600 text-white rounded-xl font-bold shadow-lg shadow-green-100 hover:bg-green-700 disabled:opacity-50 transition"
            >
              {{ isLoading ? 'Збереження...' : '✅ Провести постачання' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- МОДАЛЬНЕ ВІКНО: СТВОРЕННЯ ПОСТАЧАЛЬНИКА -->
    <Teleport to="body">
      <div v-if="showSupplierModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
        <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden transform transition-all scale-100">
          
          <!-- Header -->
          <div class="p-6 border-b border-gray-100 bg-blue-50/50">
            <h3 class="text-xl font-bold text-gray-800">🏢 Новий постачальник</h3>
            <p class="text-xs text-gray-500">Додайте контактні дані для бази</p>
          </div>

          <!-- Form Body -->
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Назва / Компанія *</label>
              <input 
                v-model="newSupplier.name" 
                type="text" 
                placeholder="Напр: ПрАТ 'Молочний Світ'" 
                class="w-full border p-3 rounded-xl focus:ring-2 ring-blue-100 outline-none transition"
              >
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Телефон</label>
                <input 
                  v-model="newSupplier.phone" 
                  type="tel" 
                  placeholder="+380..." 
                  class="w-full border p-3 rounded-xl focus:ring-2 ring-blue-100 outline-none"
                >
              </div>
              <div>
                <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Email</label>
                <input 
                  v-model="newSupplier.email" 
                  type="email" 
                  placeholder="office@example.com" 
                  class="w-full border p-3 rounded-xl focus:ring-2 ring-blue-100 outline-none"
                >
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Коментар / Нотатки</label>
              <textarea 
                v-model="newSupplier.notes" 
                rows="3" 
                placeholder="Графік доставки, умови оплати тощо..." 
                class="w-full border p-3 rounded-xl focus:ring-2 ring-blue-100 outline-none resize-none"
              ></textarea>
            </div>
          </div>

          <!-- Footer Buttons -->
          <div class="p-6 border-t border-gray-100 flex gap-3 bg-gray-50/30">
            <button 
              @click="showSupplierModal = false" 
              class="flex-1 py-3 text-gray-500 font-bold hover:bg-gray-100 rounded-xl transition"
            >
              Скасувати
            </button>
            <button 
              @click="saveNewSupplier"
              class="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-100 hover:bg-blue-700 active:scale-95 transition"
            >
              Створити
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>