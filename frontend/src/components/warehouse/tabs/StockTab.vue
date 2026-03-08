<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import axios from 'axios'
import HistoryModal from '../modals/HistoryModal.vue'
import { useSupplies } from '@/composables/useSupplies'
import AdjustmentModal from '@/components/warehouse/modals/AdjustmentModal.vue'

// Отримуємо дані зі сховища
const { ingredients, consumables, products, fetchWarehouseData } = useWarehouse()

const activeTab = ref('ingredients') 
const search = ref('')
const loading = ref(false)
const { fetchAvailableBatches } = useSupplies()

// --- Стан для розгортання партій ---
const expandedId = ref(null);
const activeBatches = ref([]);
const currentMethod = ref('wac');
const isBatchesLoading = ref(false);

// Стан для модалки коригування
const isAdjustModalOpen = ref(false)
const selectedItemForAdjust = ref(null)

const openAdjustModal = (item) => {
    if (!item) return; // 🛡 Захист від порожніх викликів
    const detectedType = item.costing_method !== undefined ? 'ingredient' : 'consumable'
    console.log("🛠 Відкриваю вікно для:", item?.display_name || item?.name)

    selectedItemForAdjust.value = { 
        ...item, 
        type: detectedType // Беремо існуючий або визначаємо за непрямими ознаками
    }
  
    isAdjustModalOpen.value = true;
    console.log("📍 Спроба відкрити модалку для:", selectedItemForAdjust.value.name, "Тип:", selectedItemForAdjust.value.type)

}

const toggleBatches = async (item) => {
  const uniqueId = `${item.type}-${item.id}`;
  
  // Якщо вже розгорнуто — згортаємо
  if (expandedId.value === uniqueId) {
    expandedId.value = null;
    return;
  }

  // Розгортаємо та завантажуємо
  expandedId.value = uniqueId;
  isBatchesLoading.value = true;
  activeBatches.value = [];

  try {
    const data = await fetchAvailableBatches(item.type, item.id);
    activeBatches.value = data.batches;
    currentMethod.value = data.costing_method;
  } finally {
    isBatchesLoading.value = false;
  }
};

// Функція форматування дати
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
};

// --- ЗМІННІ ДЛЯ РЕДАГУВАННЯ ---
// Зберігаємо не ID, а унікальний ключ (напр. 'product_5')
const editingItemKey = ref(null) 
const editValue = ref(0)

// --- ЗМІННІ ДЛЯ ІСТОРІЇ ---
const isHistoryOpen = ref(false)
const historyItem = ref(null)

// --- ФУНКЦІЯ ВІДКРИТТЯ ІСТОРІЇ ---
const openHistory = (item) => {
    const realId = item.original_id || item.id
    console.log(`OPEN HISTORY: ${item.display_name} (Type: ${item.type}, ID: ${realId})`)

    historyItem.value = {
        id: realId,
        type: item.type,
        name: item.display_name
    }
    isHistoryOpen.value = true
}

// --- Плоский список для таблиці ---
const filteredItems = computed(() => {
    let list = []

    // 1. СИРОВИНА
    if (activeTab.value === 'ingredients') {
        list = ingredients.value.map(i => ({ 
            ...i, 
            type: 'ingredient', 
            display_name: i.name,
            unit_symbol: i.unit?.symbol || '',
            // ГЕНЕРУЄМО УНІКАЛЬНИЙ КЛЮЧ
            unique_key: `ingredient_${i.id}` 
        }))
    } 
    // 2. МАТЕРІАЛИ
    else if (activeTab.value === 'consumables') {
        list = consumables.value.map(c => ({ 
            ...c, 
            type: 'consumable', 
            display_name: c.name,
            unit_symbol: c.unit?.symbol || '',
            unique_key: `consumable_${c.id}`
        }))
    } 
    // 3. ТОВАРИ (Розгортаємо варіанти!)
    else if (activeTab.value === 'products') {
        products.value.forEach(p => {
            if (p.has_variants && p.variants) {
                // Варіанти
                p.variants.forEach(v => {
                    list.push({
                        id: v.id, 
                        original_id: v.id,
                        type: 'product_variant',
                        display_name: `${p.name} (${v.name})`, 
                        stock_quantity: v.stock_quantity,
                        unit_symbol: 'шт',
                        product_id: p.id,
                        // Унікальний ключ для варіанту
                        unique_key: `product_variant_${v.id}`
                    })
                })
            } else {
                // Прості товари
                list.push({
                    id: p.id,
                    original_id: p.id,
                    type: 'product',
                    display_name: p.name,
                    stock_quantity: p.stock_quantity,
                    unit_symbol: 'шт',
                    // Унікальний ключ для продукту
                    unique_key: `product_${p.id}`
                })
            }
        })
    }

    if (search.value) {
        const s = search.value.toLowerCase()
        return list.filter(i => i.display_name.toLowerCase().includes(s))
    }
    return list
})

// --- ЛОГІКА РЕДАГУВАННЯ ЗАЛИШКІВ ---
const startEdit = (item) => {
    // Використовуємо унікальний ключ замість простого ID
    editingItemKey.value = item.unique_key
    editValue.value = item.stock_quantity
}

const saveEdit = async (item) => {
    if (editValue.value < 0) return alert("Не може бути мінусовим")
    
    loading.value = true
    try {
        let url = ''
        let payload = {}
        let method = 'put'
        
        const realId = item.original_id || item.id

        if (item.type === 'ingredient') {
            url = `/api/ingredients/${realId}`
            payload = { ...item, stock_quantity: editValue.value }
        } 
        else if (item.type === 'consumable') {
            url = `/api/consumables/${realId}`
            payload = { ...item, stock_quantity: editValue.value }
        }
        else if (item.type === 'product') {
            url = `/api/products/${realId}/stock?qty=${editValue.value}`
            method = 'patch'
            payload = {} 
        }
        else if (item.type === 'product_variant') {
            url = `/api/products/variants/${realId}/stock?qty=${editValue.value}`
            method = 'patch'
            payload = {}
        }

        if (method === 'put') {
            await axios.put(url, payload)
        } else {
            await axios.patch(url)
        }

        item.stock_quantity = editValue.value
        await fetchWarehouseData()
        editingItemKey.value = null // Закриваємо редагування за ключем
    } catch (e) {
        console.error(e)
        alert("Помилка оновлення залишку")
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    fetchWarehouseData()
})
</script>

<template>
    <div class="h-full flex flex-col bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div class="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center gap-4">
            <div class="flex p-1 bg-white rounded-xl border border-gray-200 shadow-sm">
                <button 
                    v-for="tab in ['ingredients', 'consumables', 'products']" 
                    :key="tab"
                    @click="activeTab = tab"
                    class="px-4 py-2 text-xs font-bold rounded-lg transition-all"
                    :class="activeTab === tab ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500 hover:bg-gray-50'"
                >
                    {{ tab === 'ingredients' ? '🥦 Сировина' : (tab === 'consumables' ? '📦 Матеріали' : '🍹 Товари') }}
                </button>
            </div>

            <input 
                v-model="search" 
                placeholder="Пошук..." 
                class="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-500 w-64"
            >
        </div>

        <div class="flex-1 overflow-auto">
            <table class="w-full text-left text-sm">
                <thead class="bg-gray-50 text-gray-500 uppercase text-xs sticky top-0 z-10">
                    <tr>
                        <th class="p-4">Назва</th>
                        <th class="p-4 text-center">Тип</th>
                        <th class="p-4 text-right">Залишок</th>
                        <th class="p-4 text-center">Дії</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-if="filteredItems.length === 0">
                        <td colspan="4" class="p-8 text-center text-gray-400">
                            Нічого не знайдено...
                        </td>
                    </tr>
                    
                    <tbody class="divide-y divide-gray-100">
                    <template v-for="item in filteredItems" :key="item.type + '-' + item.id">
                        <!-- ОСНОВНИЙ РЯДОК -->
                        <tr 
                        @click="toggleBatches(item)"
                        class="hover:bg-blue-50/50 transition-colors cursor-pointer group"
                        :class="{ 'bg-blue-50/30': expandedId === (item.type + '-' + item.id) }"
                        >
                        <td class="p-4">
                            <div class="flex items-center gap-3">
                            <span class="text-[10px] text-gray-400 transition-transform" 
                                    :class="{ 'rotate-90 text-blue-500': expandedId === (item.type + '-' + item.id) }">
                                ▶
                            </span>
                            <span class="font-bold text-gray-700">{{ item.display_name }}</span>
                            </div>
                        </td>
                        <td class="p-4 text-xs text-gray-400 capitalize">
                            {{ item.type === 'ingredient' ? 'Сировина' : (item.type === 'consumable' ? 'Матеріал' : 'Товар') }}
                        </td>
                        <td class="p-4 text-right">
                            <span class="font-black text-gray-800">{{ item.stock_quantity }}</span>
                            <span class="ml-1 text-gray-400 text-xs">{{ item.unit_symbol }}</span>
                        </td>
                        <td class="p-4 text-right">
                            <button @click.stop="openHistory(item)" class="text-blue-500 hover:underline text-xs font-bold">
                            Історія
                            </button>
                        </td>

                        <td class="p-4 text-center flex justify-center gap-2">
                            <button @click.stop="openAdjustModal(item)" class="text-blue-400 hover:text-blue-600 px-2 transition" title="Коригування залишку">
                                <i class="fas fa-balance-scale"></i>
                            </button>
                            
                        </td>

                        </tr>

                        <!-- РОЗГОРНУТИЙ РЯДОК (ПАРТІЇ) -->
                        <tr v-if="expandedId === (item.type + '-' + item.id)">
                        <td colspan="4" class="p-0 bg-gray-50/50">
                            <div class="p-5 border-l-4 border-blue-500 ml-4 my-2">
                            <div class="flex justify-between items-center mb-3">
                                <h4 class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                                Активні партії закупівлі
                                </h4>
                                <span :class="currentMethod === 'fifo' ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'" 
                                    class="text-[9px] px-2 py-0.5 rounded-full font-bold uppercase">
                                Метод: {{ currentMethod }}
                                </span>
                            </div>

                            <div v-if="isBatchesLoading" class="text-xs text-gray-400 italic">Завантаження даних...</div>
                            
                            <div v-else-if="activeBatches.length > 0" class="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
                                <table class="w-full text-[11px]">
                                <thead class="bg-gray-100 text-gray-500">
                                    <tr>
                                    <th class="p-2 text-left">Дата поставки</th>
                                    <th class="p-2 text-left">Накладна</th>
                                    <th class="p-2 text-center">Залишок</th>
                                    <th class="p-2 text-right">Ціна вх.</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-50">
                                    <tr v-for="(batch, idx) in activeBatches" :key="batch.id" 
                                        :class="{ 'bg-red-50/50': currentMethod === 'fifo' && idx === 0 }">
                                    <td class="p-2 text-gray-600">{{ formatDate(batch.supply_date) }}</td>
                                    <td class="p-2 font-medium text-blue-600">#{{ batch.invoice_number }}</td>
                                    <td class="p-2 text-center">
                                        <!-- 🔥 ПІДСВІЧУВАННЯ FIFO: червоний колір для найстарішої партії -->
                                        <span :class="{ 'text-red-600 font-black': currentMethod === 'fifo' && idx === 0 }">
                                        {{ batch.remaining_quantity }}
                                        </span>
                                    </td>
                                    <td class="p-2 text-right text-gray-400">{{ batch.cost_per_unit.toFixed(2) }} ₴</td>
                                    </tr>
                                </tbody>
                                </table>
                            </div>
                            
                            <div v-else class="text-xs text-gray-400 italic">Немає активних партій. Товар списано повністю.</div>
                            </div>
                        </td>
                        </tr>
                    </template>
                    </tbody>
                </tbody>
            </table>
        </div>

        <HistoryModal 
            v-if="isHistoryOpen" 
            :is-open="isHistoryOpen" 
            :item="historyItem" 
            @close="isHistoryOpen = false" 
        />
        
    </div>
    <AdjustmentModal 
            v-if="isAdjustModalOpen && selectedItemForAdjust" 
            :is-open="isAdjustModalOpen"
            :item="selectedItemForAdjust"
            :entity-type="selectedItemForAdjust?.type" 
            @close="isAdjustModalOpen = false"
            @saved="fetchWarehouseData" 
    />
</template>