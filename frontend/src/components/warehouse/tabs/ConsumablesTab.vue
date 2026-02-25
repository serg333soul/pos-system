<script setup>
import { ref, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// 1. Беремо units з useWarehouse
const { consumables, units, createItem, deleteItem } = useWarehouse()

const categories = ref([])

// 2. Додаємо unit_id в модель форми
const newConsumable = ref({ 
    name: '', 
    unit_id: '', // Початкове значення пусте
    cost_per_unit: 0, 
    stock_quantity: 0,
    category_id: null 
})

const fetchCategories = async () => {
    try {
        const response = await fetch('/api/categories/') 
        if (response.ok) {
            categories.value = await response.json()
        }
    } catch (e) {
        console.error("Помилка завантаження категорій:", e)
    }
}

onMounted(() => {
    fetchCategories()
})

const handleCreate = async () => {
    if(!newConsumable.value.name) return
    const success = await createItem('/api/consumables/', newConsumable.value)
    if(success) {
        newConsumable.value = {
            name:'', 
            unit_id:'', 
            cost_per_unit:0, 
            stock_quantity:0, 
            category_id: null
        }
    }
}

const handleDelete = (id) => deleteItem(`/api/consumables/${id}`)
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
            <h3 class="font-bold mb-6 text-gray-700 border-b pb-2">📦 Новий матеріал</h3>
            
            <div class="space-y-5">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва</label>
                    <input v-model="newConsumable.name" placeholder="Напр. Стакан 300мл" class="border p-2 rounded-lg w-full bg-gray-50 focus:bg-white focus:ring-2 focus:ring-teal-100 outline-none transition">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Категорія</label>
                        <select v-model="newConsumable.category_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option :value="null">Без категорії</option>
                            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                                {{ cat.name }}
                            </option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Одиниця виміру</label>
                        <select v-model="newConsumable.unit_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option value="" disabled>Оберіть...</option>
                            <option v-for="u in units" :key="u.id" :value="u.id">
                                {{u.name}} ({{u.symbol}})
                            </option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ціна (₴/од)</label>
                        <input 
                            :value="0"
                            disabled
                            type="number" 
                            class="w-full bg-gray-100 border border-gray-200 text-gray-400 p-2 rounded-xl cursor-not-allowed"
                            placeholder="0.00"
                        >
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Поч. залишок</label>
                        <input 
                            :value="0"
                            disabled
                            type="number" 
                            class="w-full bg-gray-100 border border-gray-200 text-gray-400 p-2 rounded-xl cursor-not-allowed"
                            placeholder="0"
                        >
                    </div>
                    <p class="mt-2 text-[10px] text-orange-500 italic">
                        * Поля заблоковані. Ціна та залишок оновлюються автоматично після проведення "Постачання".
                    </p>
                </div>

                <button @click="handleCreate" class="bg-teal-600 hover:bg-teal-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-teal-200 transition mt-2">
                    <i class="fas fa-plus mr-2"></i> Додати
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
                    <tr>
                        <th class="p-4">Назва</th>
                        <th class="p-4 text-right">Залишок</th>
                        <th class="p-4 text-center">Дії</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="c in consumables" :key="c.id" class="hover:bg-gray-50">
                        <td class="p-4 font-bold text-gray-700">
                            {{ c.name }}
                            <div class="flex items-center gap-2 mt-1">
                                <span v-if="c.category" class="text-[10px] bg-teal-50 text-teal-600 px-2 py-0.5 rounded-full uppercase tracking-wider font-bold">
                                    {{ c.category.name }}
                                </span>
                                <span class="text-xs text-gray-400 font-normal">
                                    {{ c.cost_per_unit }} ₴/{{ c.unit?.symbol || 'од' }}
                                </span>
                            </div>
                        </td>
                        <td class="p-4 text-right font-mono text-lg" :class="c.stock_quantity > 10 ? 'text-green-600' : 'text-red-500'">
                            {{ c.stock_quantity }} 
                            <span class="text-xs text-gray-400 font-sans">{{ c.unit?.symbol || '?' }}</span>
                        </td>
                        <td class="p-4 text-center">
                            <button @click="handleDelete(c.id)" class="text-gray-400 hover:text-red-500 px-2 transition">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>