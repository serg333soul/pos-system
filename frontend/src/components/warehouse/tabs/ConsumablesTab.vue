<script setup>
import { ref } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

const { consumables, units, createItem, deleteItem } = useWarehouse()

const newConsumable = ref({ name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 })

const handleCreate = async () => {
    if(!newConsumable.value.name) return
    const success = await createItem('/api/consumables/', newConsumable.value)
    if(success) newConsumable.value={name:'',unit_id:'',cost_per_unit:0,stock_quantity:0}
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
                    <input v-model="newConsumable.name" placeholder="Напр. Стакан 300мл" class="border p-2 rounded-lg w-full">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Одиниця</label>
                        <select v-model="newConsumable.unit_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option value="" disabled>Оберіть...</option>
                            <option v-for="u in units" :key="u.id" :value="u.id">{{u.name}} ({{u.symbol}})</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ціна (₴/од)</label>
                        <input v-model="newConsumable.cost_per_unit" type="number" class="border p-2 rounded-lg w-full">
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Залишок</label>
                    <input v-model="newConsumable.stock_quantity" type="number" class="border p-2 rounded-lg w-full">
                </div>
                <button @click="handleCreate" class="bg-teal-600 hover:bg-teal-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-teal-200 transition mt-2">Додати</button>
            </div>
        </div>
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
                    <tr><th class="p-4">Назва</th><th class="p-4 text-right">Залишок</th><th class="p-4 text-center">Дії</th></tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="c in consumables" :key="c.id" class="hover:bg-gray-50">
                        <td class="p-4 font-bold text-gray-700">{{ c.name }}
                            <div class="text-xs text-gray-400 font-normal">{{ c.cost_per_unit }} ₴/{{ c.unit?.symbol }}</div>
                        </td>
                        <td class="p-4 text-right font-mono text-lg" :class="c.stock_quantity > 10 ? 'text-green-600' : 'text-red-500'">
                            {{ c.stock_quantity }} <span class="text-xs text-gray-400 font-sans">{{ c.unit?.symbol }}</span>
                        </td>
                        <td class="p-4 text-center">
                            <button @click="handleDelete(c.id)" class="text-gray-400 hover:text-red-500 px-2"><i class="fas fa-trash"></i></button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>