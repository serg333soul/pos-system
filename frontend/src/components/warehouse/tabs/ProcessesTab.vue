<script setup>
import { ref } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

const { processGroups, fetchData, createItem, deleteItem } = useWarehouse()

const newProcessGroup = ref({ name: '' })

const handleCreateGroup = async () => {
    if(!newProcessGroup.value.name) return alert("Вкажіть назву групи (напр. Помол)")
    const success = await createItem('/api/processes/groups/', { name: newProcessGroup.value.name, options: [] })
    if(success) newProcessGroup.value.name = ''
}

const handleDeleteGroup = (id) => deleteItem(`/api/processes/groups/${id}`)

const addProcessOption = async (groupId) => {
    const name = prompt("Введіть назву опції (напр. Під еспресо):")
    if(!name) return
    await createItem(`/api/processes/options/?group_id=${groupId}`, { name: name })
}

const deleteProcessOption = (optionId) => deleteItem(`/api/processes/options/${optionId}`)
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-indigo-100 h-fit">
            <h3 class="font-bold text-lg text-indigo-800 mb-4 border-b pb-2">➕ Нова група процесів</h3>
            <p class="text-sm text-gray-500 mb-4">Наприклад: "Помол", "Ступінь просмаження", "Температура подачі".</p>
            <div class="flex gap-2">
                <input v-model="newProcessGroup.name" placeholder="Назва групи..." class="flex-1 border p-2 rounded-lg outline-none focus:ring-2 ring-indigo-200">
                <button @click="handleCreateGroup" class="bg-indigo-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-indigo-700 transition">Створити</button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
             <div v-if="processGroups.length === 0" class="p-8 text-center text-gray-400">
                 Немає створених процесів
             </div>
             
             <div v-else class="divide-y divide-gray-100">
                 <div v-for="group in processGroups" :key="group.id" class="p-6">
                     <div class="flex justify-between items-center mb-4">
                         <h4 class="font-bold text-xl text-gray-800">{{ group.name }}</h4>
                         <button @click="handleDeleteGroup(group.id)" class="text-gray-300 hover:text-red-500 transition"><i class="fas fa-trash"></i></button>
                     </div>

                     <div class="space-y-2 mb-4">
                         <div v-for="opt in group.options" :key="opt.id" class="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
                             <span class="text-gray-700 font-medium">{{ opt.name }}</span>
                             <button @click="deleteProcessOption(opt.id)" class="text-red-300 hover:text-red-500"><i class="fas fa-times"></i></button>
                         </div>
                     </div>

                     <button @click="addProcessOption(group.id)" class="w-full py-2 bg-indigo-50 text-indigo-600 font-bold rounded-lg hover:bg-indigo-100 border border-indigo-200 border-dashed">
                         + Додати варіант (напр. "Під еспресо")
                     </button>
                 </div>
             </div>
        </div>
    </div>
</template>