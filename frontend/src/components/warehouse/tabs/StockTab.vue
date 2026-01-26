<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import axios from 'axios'
import HistoryModal from '../modals/HistoryModal.vue'

// Отримуємо дані зі сховища
const { ingredients, consumables, products, fetchWarehouseData } = useWarehouse()

const activeTab = ref('ingredients') 
const search = ref('')
const loading = ref(false)

// Змінні для редагування
const editingItem = ref(null)
const editValue = ref(0)

// --- ЗМІННІ ДЛЯ ІСТОРІЇ ---
const isHistoryOpen = ref(false)
const historyItem = ref(null)

// --- ФУНКЦІЯ ВІДКРИТТЯ ІСТОРІЇ ---
const openHistory = (item) => {
    // 1. Визначаємо правильний ID
    // Якщо це список, ми зберегли справжній ID в original_id
    const realId = item.original_id || item.id

    console.log(`OPEN HISTORY: ${item.display_name} (Type: ${item.type}, ID: ${realId})`)

    // 2. Формуємо об'єкт для модалки
    historyItem.value = {
        id: realId,               // Модалка отримає вже чистий ID
        type: item.type,          // 'ingredient', 'consumable', 'product', 'product_variant'
        name: item.display_name   // Назва для заголовка
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
            unit_symbol: i.unit?.symbol || '' 
        }))
    } 
    // 2. МАТЕРІАЛИ
    else if (activeTab.value === 'consumables') {
        list = consumables.value.map(c => ({ 
            ...c, 
            type: 'consumable', 
            display_name: c.name,
            unit_symbol: c.unit?.symbol || ''
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
                        original_id: v.id,       // <--- ВАЖЛИВО: ID варіанту
                        type: 'product_variant', // <--- ВАЖЛИВО: Тип
                        display_name: `${p.name} (${v.name})`, 
                        stock_quantity: v.stock_quantity,
                        unit_symbol: 'шт',
                        product_id: p.id 
                    })
                })
            } else {
                // Прості товари
                list.push({
                    id: p.id,
                    original_id: p.id,       // <--- ВАЖЛИВО: ID товару
                    type: 'product',         // <--- ВАЖЛИВО: Тип
                    display_name: p.name,
                    stock_quantity: p.stock_quantity,
                    unit_symbol: 'шт'
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
    editingItem.value = item.id 
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
        editingItem.value = null
        // alert("Збережено!") // Можна розкоментувати
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
                    
                    <tr v-for="item in filteredItems" :key="item.type + item.id" class="hover:bg-gray-50 group">
                        
                        <td class="p-4 font-bold text-gray-700">
                            {{ item.display_name }}
                        </td>

                        <td class="p-4 text-center">
                            <span v-if="item.type === 'ingredient'" class="bg-green-100 text-green-700 px-2 py-1 rounded text-[10px] font-bold">Сировина</span>
                            <span v-else-if="item.type === 'consumable'" class="bg-teal-100 text-teal-700 px-2 py-1 rounded text-[10px] font-bold">Матеріал</span>
                            <span v-else-if="item.type === 'product'" class="bg-purple-100 text-purple-700 px-2 py-1 rounded text-[10px] font-bold">Товар</span>
                            <span v-else-if="item.type === 'product_variant'" class="bg-indigo-100 text-indigo-700 px-2 py-1 rounded text-[10px] font-bold">Варіант</span>
                        </td>

                        <td class="p-4 text-right font-mono font-bold">
                            <div v-if="editingItem === item.id" class="flex items-center justify-end gap-2">
                                <input 
                                    v-model.number="editValue" 
                                    type="number" 
                                    class="w-20 border rounded p-1 text-right focus:ring-2 ring-blue-500 outline-none"
                                >
                                <span class="text-xs text-gray-400">{{ item.unit_symbol }}</span>
                            </div>
                            <span v-else :class="{'text-red-500 bg-red-50 px-2 py-1 rounded': item.stock_quantity <= 0, 'text-gray-700': item.stock_quantity > 0}">
                                {{ item.stock_quantity }} {{ item.unit_symbol }}
                            </span>
                        </td>

                        <td class="p-4 text-center">
                            <div v-if="editingItem === item.id" class="flex justify-center gap-1">
                                <button @click="saveEdit(item)" class="bg-green-500 text-white w-7 h-7 rounded hover:bg-green-600 flex items-center justify-center">
                                    <i class="fas fa-check text-xs"></i>
                                </button>
                                <button @click="editingItem = null" class="bg-gray-300 text-gray-700 w-7 h-7 rounded hover:bg-gray-400 flex items-center justify-center">
                                    <i class="fas fa-times text-xs"></i>
                                </button>
                            </div>
                            
                            <div v-else class="flex justify-center gap-2">
                                <button @click="openHistory(item)" class="text-purple-400 hover:text-purple-600 p-2 rounded hover:bg-purple-50 transition-colors" title="Історія руху">
                                    <i class="fas fa-history"></i>
                                </button>
                                <button @click="startEdit(item)" class="text-blue-400 hover:text-blue-600 p-2 rounded hover:bg-blue-50 transition-colors" title="Корегувати залишок">
                                    <i class="fas fa-pen"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
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
</template>