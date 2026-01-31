<script setup>
// 👇 ДОДАНО: onMounted (це було пропущено)
import { ref, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// Використовуємо глобальні дані
const { ingredients, units, createItem, deleteItem } = useWarehouse()

// Локальний стан для категорій
const categories = ref([])

const newIngredient = ref({ 
    name: '', 
    unit_id: '', 
    cost_per_unit: 0, 
    stock_quantity: 0, 
    category_id: null 
})

// Функція завантаження категорій з бекенду
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

// Завантажуємо категорії при відкритті вкладки
onMounted(() => {
    fetchCategories()
})

const handleCreate = async () => {
    console.log("Спроба створити:", newIngredient.value);
    if(!newIngredient.value.name) return
    const success = await createItem('/api/ingredients/', newIngredient.value)
    if(success) {
        newIngredient.value = {
            name:'',
            unit_id:'',
            cost_per_unit:0,
            stock_quantity:0,
            category_id: null
        }
    }
}

const handleDelete = (id) => deleteItem(`/api/ingredients/${id}`)
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
            <h3 class="font-bold mb-6 text-gray-700 border-b pb-2">🌱 Новий інгредієнт</h3>
            
            <div class="space-y-5">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва інгредієнта</label>
                    <input v-model="newIngredient.name" placeholder="Напр. Кава в зернах" class="border p-2 rounded-lg w-full bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Категорія</label>
                        <select v-model="newIngredient.category_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option :value="null">Без категорії</option>
                            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                                {{ cat.name }}
                            </option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Одиниця виміру</label>
                        <select v-model="newIngredient.unit_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option value="" disabled>Оберіть...</option>
                            <option v-for="u in units" :key="u.id" :value="u.id">
                                {{u.name}} ({{u.symbol}})
                            </option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Собівартість (₴/од)</label>
                        <input v-model="newIngredient.cost_per_unit" type="number" step="0.01" placeholder="0.00" class="border p-2 rounded-lg w-full">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Поч. залишок</label>
                        <input v-model="newIngredient.stock_quantity" type="number" step="0.01" placeholder="0" class="border p-2 rounded-lg w-full">
                    </div>
                </div>

                <button @click="handleCreate" class="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition mt-2">
                    <i class="fas fa-plus mr-2"></i> Додати в базу
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
                    <tr v-for="i in ingredients" :key="i.id" class="hover:bg-gray-50">
                        <td class="p-4 font-bold text-gray-700">
                            {{ i.name }}
                            <div class="flex items-center gap-2 mt-1">
                                <span v-if="i.category" class="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full uppercase tracking-wider font-bold">
                                    {{ i.category.name }}
                                </span>
                                <span class="text-xs text-gray-400 font-normal">
                                    {{ i.cost_per_unit }} ₴/{{ i.unit?.symbol }}
                                </span>
                            </div>
                        </td>
                        <td class="p-4 text-right font-mono text-lg" :class="i.stock_quantity > 0 ? 'text-green-600' : 'text-red-500'">
                            {{ i.stock_quantity }} <span class="text-xs text-gray-400 font-sans">{{ i.unit?.symbol }}</span>
                        </td>
                        <td class="p-4 text-center">
                            <button @click="handleDelete(i.id)" class="text-gray-400 hover:text-red-500 px-2 transition">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>