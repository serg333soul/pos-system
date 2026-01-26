<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

// --- КОНФІГУРАЦІЯ API ---
const API_URL = 'http://localhost:8001/customers/'

// --- СТАН ---
const customers = ref([])
const showModal = ref(false)
const searchQuery = ref('')
const isEditing = ref(false)
const editingId = ref(null)

// Форма
const formData = ref({
    name: '',
    phone: '',
    email: '',
    notes: ''
})

// --- API ЗАПИТИ ---

const fetchCustomers = async () => {
    try {
        const res = await axios.get(API_URL)
        console.log("Отримані клієнти:", res.data)
        customers.value = res.data
    } catch (err) {
        console.error("Помилка завантаження клієнтів:", err)
    }
}

const handleSave = async () => {
    if (!formData.value.name) return alert("Ім'я обов'язкове!")
    if (!formData.value.phone) return alert("Телефон обов'язковий!")

    try {
        if (isEditing.value) {
            await axios.put(`${API_URL}${editingId.value}`, formData.value)
        } else {
            await axios.post(API_URL, formData.value)
        }
        
        closeModal()
        await fetchCustomers()
    } catch (err) {
        console.error(err)
        alert("Помилка при збереженні. Можливо такий телефон вже існує.")
    }
}

const deleteCustomer = async (id) => {
    if(!confirm("Видалити цього клієнта з бази?")) return
    try {
        await axios.delete(`${API_URL}${id}`)
        fetchCustomers()
    } catch (err) {
        alert("Помилка видалення")
    }
}

// --- ЛОГІКА ІНТЕРФЕЙСУ ---

const openCreateModal = () => {
    isEditing.value = false
    editingId.value = null
    formData.value = { name: '', phone: '', email: '', notes: '' }
    showModal.value = true
}

const openEditModal = (customer) => {
    isEditing.value = true
    editingId.value = customer.id
    formData.value = {
        name: customer.name,
        phone: customer.phone,
        email: customer.email || '',
        notes: customer.notes || ''
    }
    showModal.value = true
}

const closeModal = () => {
    showModal.value = false
    formData.value = { name: '', phone: '', email: '', notes: '' }
}

const filteredCustomers = computed(() => {
    if (!searchQuery.value) return customers.value
    const q = searchQuery.value.toLowerCase()
    return customers.value.filter(c => 
        c.name.toLowerCase().includes(q) || 
        (c.phone && c.phone.includes(q)) ||
        (c.email && c.email.toLowerCase().includes(q))
    )
})

onMounted(fetchCustomers)
</script>

<template>
    <div class="h-full w-full bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden md:ml-64 transition-all duration-300" style="width: calc(100% - 16rem);">
        
        <div class="p-6 border-b border-gray-100 flex flex-col md:flex-row justify-between items-center gap-4 bg-gray-50/50">
            <div>
                <h2 class="text-xl font-bold text-gray-800">Клієнти</h2>
                <p class="text-xs text-gray-500">База контактів CRM</p>
            </div>

            <div class="flex w-full md:w-auto gap-3">
                <div class="relative flex-1 md:w-64">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                        <i class="fas fa-search"></i>
                    </span>
                    <input 
                        v-model="searchQuery" 
                        type="text" 
                        placeholder="Пошук (ім'я, тел, email)..." 
                        class="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none text-sm transition bg-white"
                    >
                </div>

                <button 
                    @click="openCreateModal" 
                    class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-xl font-bold shadow-lg shadow-blue-100 transition transform active:scale-95 flex items-center gap-2 whitespace-nowrap text-sm"
                >
                    <i class="fas fa-user-plus"></i>
                    <span>Додати</span>
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-auto">
            <table class="w-full text-left text-sm text-gray-600">
                <thead class="bg-gray-50 text-xs uppercase font-bold text-gray-500 sticky top-0 z-10 shadow-sm">
                    <tr>
                        <th class="p-4 border-b">Клієнт</th>
                        <th class="p-4 border-b">Телефон</th>
                        <th class="p-4 border-b">Email</th>
                        <th class="p-4 border-b">Нотатки</th>
                        <th class="p-4 border-b text-center">Дії</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-if="filteredCustomers.length === 0">
                        <td colspan="5" class="p-8 text-center text-gray-400">
                            <div class="flex flex-col items-center gap-2">
                                <i class="fas fa-users-slash text-2xl"></i>
                                <span>Клієнтів не знайдено</span>
                            </div>
                        </td>
                    </tr>
                    <tr v-for="c in filteredCustomers" :key="c.id" class="hover:bg-blue-50/30 transition group">
                        
                        <td class="p-4 font-medium text-gray-900">
                            <div class="flex items-center gap-3">
                                <div class="w-9 h-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-xs border border-blue-200 shadow-sm shrink-0">
                                    {{ c.name ? c.name.charAt(0).toUpperCase() : '?' }}
                                </div>
                                <div class="flex flex-col">
                                    <span v-if="c.name">{{ c.name }}</span>
                                    <span v-else class="text-red-500 text-xs font-bold">MISSING NAME (ID: {{ c.id }})</span>
                                </div>
                            </div>
                        </td>
                        
                        <td class="p-4">
                             <span class="font-mono text-xs text-gray-700 bg-gray-50/50 px-2 py-1 rounded border border-gray-100">
                                {{ c.phone || '---' }}
                             </span>
                        </td>
                        
                        <td class="p-4 text-blue-500">
                            {{ c.email || '-' }}
                        </td>
                        
                        <td class="p-4 text-xs italic text-gray-400 max-w-xs truncate">
                            {{ c.notes || '-' }}
                        </td>
                        
                        <td class="p-4 text-center">
                            <div class="flex justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                    @click="openEditModal(c)" 
                                    class="text-blue-400 hover:text-blue-600 p-2 rounded hover:bg-blue-50 transition"
                                    title="Редагувати"
                                >
                                    <i class="fas fa-pen"></i>
                                </button>
                                <button 
                                    @click="deleteCustomer(c.id)" 
                                    class="text-gray-300 hover:text-red-500 p-2 rounded hover:bg-red-50 transition"
                                    title="Видалити"
                                >
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="showModal" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div class="bg-white w-full max-w-md rounded-2xl shadow-2xl p-6 transform transition-all scale-100">
                <div class="flex justify-between items-center mb-6 border-b pb-4 border-gray-100">
                    <h2 class="text-xl font-bold text-gray-800">
                        {{ isEditing ? 'Редагувати клієнта' : 'Новий клієнт' }}
                    </h2>
                    <button @click="closeModal" class="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100">
                        &times;
                    </button>
                </div>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Ім'я <span class="text-red-500">*</span></label>
                        <input v-model="formData.name" class="w-full border-gray-200 border p-3 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none bg-gray-50 focus:bg-white transition" placeholder="ПІБ">
                    </div>
                    
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Телефон <span class="text-red-500">*</span></label>
                        <input v-model="formData.phone" class="w-full border-gray-200 border p-3 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none bg-gray-50 focus:bg-white transition" placeholder="+380...">
                    </div>
                    
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Email</label>
                        <input v-model="formData.email" class="w-full border-gray-200 border p-3 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none bg-gray-50 focus:bg-white transition" placeholder="client@mail.com">
                    </div>
                    
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Нотатки</label>
                        <textarea v-model="formData.notes" class="w-full border-gray-200 border p-3 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none bg-gray-50 focus:bg-white transition h-24 resize-none" placeholder="Уподобання, день народження..."></textarea>
                    </div>
                </div>

                <div class="flex gap-3 mt-8 pt-4 border-t border-gray-50">
                    <button @click="closeModal" class="flex-1 py-3 text-gray-500 font-bold hover:bg-gray-100 rounded-xl transition">Скасувати</button>
                    <button @click="handleSave" class="flex-1 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-200 transition transform active:scale-95">
                        {{ isEditing ? 'Зберегти зміни' : 'Створити' }}
                    </button>
                </div>
            </div>
        </div>

    </div>
</template>