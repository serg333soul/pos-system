<script setup>
import { ref } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'

// Використовуємо методи з нашого composable
const { categories, createItem, updateItem, deleteItem } = useWarehouse()

// Стан форми
const newCategory = ref({ name: '', slug: '', color: '#3b82f6', parent_id: '' }) 
const isEditing = ref(false)
const editingId = ref(null)

// Допоміжна функція для відображення батька
const getParentName = (parentId) => {
    if (!parentId) return '';
    const parent = categories.value.find(c => c.id === parentId);
    return parent ? parent.name : '???';
}

// Заповнення форми для редагування
const prepareEdit = (category) => {
    isEditing.value = true
    editingId.value = category.id
    newCategory.value = {
        name: category.name,
        slug: category.slug,
        color: category.color || '#3b82f6',
        parent_id: category.parent_id || ''
    }
}

// Скидання форми
const resetForm = () => {
    isEditing.value = false
    editingId.value = null
    newCategory.value = { name: '', slug: '', color: '#3b82f6', parent_id: '' }
}

// Обробка збереження (Створити АБО Оновити)
const handleSave = async () => {
    if (!newCategory.value.name) return alert("Вкажіть назву категорії!")
    
    const payload = { ...newCategory.value }
    
    // Автогенерація slug, якщо пусто
    if (!payload.slug) {
        payload.slug = payload.name.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now().toString().slice(-4)
    }
    // Очищення parent_id
    if (payload.parent_id === "") payload.parent_id = null
    
    let success = false

    if (isEditing.value) {
        // ОНОВЛЕННЯ (PUT)
        success = await updateItem(`/api/categories/${editingId.value}`, payload)
    } else {
        // СТВОРЕННЯ (POST)
        success = await createItem('/api/categories/', payload)
    }

    if(success) {
        resetForm()
    }
}

// Обробка видалення
const handleDelete = async (id) => {
    await deleteItem(`/api/categories/${id}`)
    // Якщо ми редагували саме цю категорію - скидаємо форму
    if (editingId.value === id) {
        resetForm()
    }
}
</script>

<template>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
            <div class="flex justify-between items-center mb-4">
                <h3 class="font-bold text-gray-700">
                    {{ isEditing ? '✏️ Редагування категорії' : '📂 Нова категорія' }}
                </h3>
                <button v-if="isEditing" @click="resetForm" class="text-xs text-red-500 hover:underline">Скасувати</button>
            </div>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва</label>
                    <input v-model="newCategory.name" class="border p-2 rounded w-full focus:ring-2 ring-blue-100 outline-none" placeholder="Напр. Кава">
                </div>
                
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Код (Slug)</label>
                    <input v-model="newCategory.slug" class="border p-2 rounded w-full font-mono text-sm text-gray-600" placeholder="auto-generated">
                </div>
                
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Колір</label>
                    <div class="flex items-center gap-2">
                        <input v-model="newCategory.color" type="color" class="h-10 w-16 border rounded cursor-pointer p-1 bg-white">
                        <span class="text-sm text-gray-600 font-mono">{{ newCategory.color }}</span>
                    </div>
                </div>
                
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Батьківська категорія</label>
                    <select v-model="newCategory.parent_id" class="border p-2 rounded w-full bg-white">
                        <option value="">(Немає - Коренева)</option>
                        <option v-for="c in categories" :key="c.id" :value="c.id" :disabled="c.id === editingId">
                            {{ c.name }}
                        </option>
                    </select>
                </div>
                
                <button @click="handleSave" 
                    class="w-full py-3 rounded-xl font-bold text-white shadow-lg transition transform active:scale-95"
                    :class="isEditing ? 'bg-orange-500 hover:bg-orange-600 shadow-orange-200' : 'bg-blue-600 hover:bg-blue-700 shadow-blue-200'">
                    {{ isEditing ? 'Зберегти зміни' : 'Створити категорію' }}
                </button>
            </div>
        </div>

        <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
                        <tr>
                            <th class="p-4">Колір</th>
                            <th class="p-4">Назва</th>
                            <th class="p-4">Код</th>
                            <th class="p-4">Батько</th>
                            <th class="p-4 text-center">Дії</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-if="categories.length === 0">
                            <td colspan="5" class="p-8 text-center text-gray-400">Категорій ще немає</td>
                        </tr>
                        <tr v-for="c in categories" :key="c.id" class="hover:bg-gray-50 group">
                            <td class="p-4">
                                <div class="w-8 h-8 rounded-lg shadow-sm border border-gray-200" :style="{ backgroundColor: c.color || '#fff' }"></div>
                            </td>
                            <td class="p-4 font-bold text-gray-800 text-lg">{{ c.name }}</td>
                            <td class="p-4 font-mono text-gray-500">{{ c.slug }}</td>
                            <td class="p-4">
                                <span v-if="c.parent_id" class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs font-bold">
                                    {{ getParentName(c.parent_id) }}
                                </span>
                                <span v-else class="text-gray-300 text-xs">-</span>
                            </td>
                            <td class="p-4 text-center">
                                <div class="flex justify-center gap-2">
                                    <button @click="prepareEdit(c)" class="p-2 text-blue-400 hover:text-blue-600 hover:bg-blue-50 rounded transition" title="Редагувати">
                                        <i class="fas fa-pen"></i>
                                    </button>
                                    <button @click="handleDelete(c.id)" class="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition" title="Видалити">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>