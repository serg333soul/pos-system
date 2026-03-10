<script setup>
import { ref, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// Додано updateItem
const { processGroups, fetchData, createItem, updateItem, deleteItem } = useWarehouse()

// --- СТВОРЕННЯ ГРУПИ ---
const newProcessGroup = ref({ 
    name: '',
    parent_option_id: null
})

const availableParentOptions = computed(() => {
    let options = []
    processGroups.value.forEach(group => {
        if (group.options) {
            group.options.forEach(opt => {
                options.push({
                    id: opt.id,
                    name: `${group.name} ➡️ ${opt.name}`
                })
            })
        }
    })
    return options
})

const handleCreateGroup = async () => {
    if(!newProcessGroup.value.name) return alert("Вкажіть назву групи (напр. Помол)")
    
    const payload = { 
        name: newProcessGroup.value.name, 
        options: [],
        parent_option_id: newProcessGroup.value.parent_option_id || null
    }
    
    const success = await createItem('/api/processes/groups/', payload)
    
    if(success) {
        newProcessGroup.value.name = ''
        newProcessGroup.value.parent_option_id = null
    }
}

const handleDeleteGroup = (id) => deleteItem(`/api/processes/groups/${id}`)

// --- РЕДАГУВАННЯ ГРУПИ ---
const editingGroupId = ref(null)
const editGroupData = ref({ name: '', parent_option_id: null })

const startEditGroup = (group) => {
    editingGroupId.value = group.id
    editGroupData.value = { 
        name: group.name, 
        parent_option_id: group.parent_option_id 
    }
}

const cancelEditGroup = () => {
    editingGroupId.value = null
}

const saveGroupEdit = async () => {
    if(!editGroupData.value.name) return alert("Назва групи не може бути порожньою")
    const success = await updateItem(`/api/processes/groups/${editingGroupId.value}`, editGroupData.value)
    if(success) editingGroupId.value = null
}

// --- ОПЦІЇ (ВАРІАЦІЇ) ---
const addProcessOption = async (groupId) => {
    const name = prompt("Введіть назву опції (напр. Під еспресо):")
    if(!name) return
    await createItem(`/api/processes/options/?group_id=${groupId}`, { name: name })
}

const deleteProcessOption = (optionId) => deleteItem(`/api/processes/options/${optionId}`)

// --- РЕДАГУВАННЯ ОПЦІЇ ---
const editingOptionId = ref(null)
const editOptionName = ref('')

const startEditOption = (opt) => {
    editingOptionId.value = opt.id
    editOptionName.value = opt.name
}

const cancelEditOption = () => {
    editingOptionId.value = null
}

const saveOptionEdit = async () => {
    if(!editOptionName.value) return alert("Назва опції не може бути порожньою")
    const success = await updateItem(`/api/processes/options/${editingOptionId.value}`, { name: editOptionName.value })
    if(success) editingOptionId.value = null
}


// Допоміжна функція
const getParentOptionName = (parentId) => {
    if (!parentId) return null;
    for (const group of processGroups.value) {
        if (group.options) {
            const opt = group.options.find(o => o.id === parentId);
            if (opt) return `${group.name} ➡️ ${opt.name}`;
        }
    }
    return "Невідома опція (Можливо видалена)";
}
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-indigo-100 h-fit">
            <h3 class="font-bold text-lg text-indigo-800 mb-4 border-b pb-2">➕ Нова група процесів</h3>
            <p class="text-sm text-gray-500 mb-6">Створюйте групи процесів (напр. "Помол") та налаштовуйте умови їх появи.</p>
            
            <div class="space-y-5">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Назва групи *</label>
                    <input v-model="newProcessGroup.name" placeholder="напр. Помол..." class="w-full border p-3 rounded-xl outline-none focus:ring-2 ring-indigo-200">
                </div>
                
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Умова появи (Залежність)</label>
                    <select v-model="newProcessGroup.parent_option_id" class="w-full border p-3 rounded-xl bg-gray-50 focus:bg-white outline-none">
                        <option :value="null">-- З'являється завжди (Немає залежності) --</option>
                        <option v-for="opt in availableParentOptions" :key="opt.id" :value="opt.id">
                            Тільки якщо обрано: {{ opt.name }}
                        </option>
                    </select>
                </div>

                <button @click="handleCreateGroup" class="w-full mt-2 bg-indigo-600 text-white px-4 py-3 rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200">
                    Створити групу
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
             <div v-if="processGroups.length === 0" class="p-8 text-center text-gray-400 font-medium">
                 Немає створених процесів
             </div>
             
             <div v-else class="divide-y divide-gray-100">
                 <div v-for="group in processGroups" :key="group.id" class="p-6 transition hover:bg-gray-50/50">
                     
                     <div v-if="editingGroupId === group.id" class="mb-4 bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                         <div class="space-y-3">
                             <input v-model="editGroupData.name" class="w-full border p-2 rounded-lg font-bold outline-none focus:ring-2 ring-indigo-300">
                             <select v-model="editGroupData.parent_option_id" class="w-full border p-2 rounded-lg bg-white outline-none text-sm">
                                 <option :value="null">-- З'являється завжди --</option>
                                 <option v-for="opt in availableParentOptions" :key="opt.id" :value="opt.id" :disabled="opt.id === group.parent_option_id">
                                     Залежить від: {{ opt.name }}
                                 </option>
                             </select>
                             <div class="flex gap-2">
                                 <button @click="saveGroupEdit" class="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-bold">Зберегти</button>
                                 <button @click="cancelEditGroup" class="bg-gray-300 text-gray-700 px-4 py-1.5 rounded-lg text-sm font-bold">Скасувати</button>
                             </div>
                         </div>
                     </div>

                     <div v-else class="flex justify-between items-start mb-4">
                         <div>
                             <h4 class="font-bold text-xl text-gray-800">{{ group.name }}</h4>
                             <div v-if="group.parent_option_id" class="mt-2 inline-flex items-center text-[10px] bg-purple-100 text-purple-700 px-2 py-1 rounded-md font-black uppercase tracking-wider">
                                 <i class="fas fa-link mr-1.5 opacity-70"></i> 
                                 Залежить від: {{ getParentOptionName(group.parent_option_id) }}
                             </div>
                         </div>
                         <div class="flex gap-1 ml-4">
                             <button @click="startEditGroup(group)" class="text-gray-400 hover:text-indigo-600 transition bg-white rounded-full p-2 hover:bg-indigo-50">
                                 <i class="fas fa-pen"></i>
                             </button>
                             <button @click="handleDeleteGroup(group.id)" class="text-gray-400 hover:text-red-500 transition bg-white rounded-full p-2 hover:bg-red-50">
                                 <i class="fas fa-trash"></i>
                             </button>
                         </div>
                     </div>

                     <div class="space-y-2 mb-4 mt-3">
                         <div v-for="opt in group.options" :key="opt.id">
                             
                             <div v-if="editingOptionId === opt.id" class="flex items-center gap-2 bg-yellow-50 px-3 py-2 rounded-lg border border-yellow-200 shadow-sm">
                                 <input v-model="editOptionName" @keyup.enter="saveOptionEdit" class="flex-1 border p-1 rounded outline-none focus:ring-1 ring-yellow-400 font-bold text-sm bg-white" autofocus>
                                 <button @click="saveOptionEdit" class="text-green-600 hover:text-green-700"><i class="fas fa-check"></i></button>
                                 <button @click="cancelEditOption" class="text-gray-400 hover:text-red-500 ml-1"><i class="fas fa-times"></i></button>
                             </div>

                             <div v-else class="group flex items-center justify-between bg-white px-4 py-2.5 rounded-lg border border-gray-100 shadow-sm hover:border-gray-300 transition">
                                 <span class="text-gray-700 font-bold text-sm">{{ opt.name }}</span>
                                 <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition">
                                     <button @click="startEditOption(opt)" class="text-gray-300 hover:text-indigo-500"><i class="fas fa-pen"></i></button>
                                     <button @click="deleteProcessOption(opt.id)" class="text-gray-300 hover:text-red-500"><i class="fas fa-trash"></i></button>
                                 </div>
                             </div>

                         </div>
                     </div>

                     <button @click="addProcessOption(group.id)" class="w-full py-2.5 bg-indigo-50/50 text-indigo-600 font-bold text-sm rounded-lg hover:bg-indigo-50 border border-indigo-200 border-dashed transition">
                         <i class="fas fa-plus mr-1"></i> Додати варіант
                     </button>
                 </div>
             </div>
        </div>
    </div>
</template>