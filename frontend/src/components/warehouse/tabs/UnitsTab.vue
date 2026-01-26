<script setup>
import { ref } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

const { units, createItem } = useWarehouse()
const newUnit = ref({ name: '', symbol: '' })

const handleCreate = async () => {
    if (!newUnit.value.name || !newUnit.value.symbol) return alert("Заповніть!")
    const success = await createItem('/api/units/', newUnit.value)
    if(success) newUnit.value = { name: '', symbol: '' }
}
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
            <h3 class="font-bold mb-4 text-gray-700">📏 Створити одиницю виміру</h3>
            <div class="space-y-3">
                <input v-model="newUnit.name" placeholder="Назва (напр. Грами)" class="border p-2 rounded w-full">
                <input v-model="newUnit.symbol" placeholder="Символ (напр. г)" class="border p-2 rounded w-full">
                <button @click="handleCreate" class="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition">Зберегти</button>
            </div>
        </div>
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Назва</th><th class="p-4 text-right">Символ</th></tr></thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="u in units" :key="u.id" class="hover:bg-gray-50">
                        <td class="p-4 font-bold text-gray-700">{{ u.name }}</td>
                        <td class="p-4 text-right font-mono">{{ u.symbol }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>