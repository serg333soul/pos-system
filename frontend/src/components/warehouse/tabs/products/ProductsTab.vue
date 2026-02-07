<script setup>
import { ref, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'

// Імпортуємо наші форми
import ProductFormSimple from './ProductFormSimple.vue'
import ProductFormVariant from './ProductFormVariant.vue'

const { fetchWarehouseData } = useWarehouse()

// --- ФУНКЦІОНАЛ ---
const { 
    newProduct, 
    prepareEdit: originalHandleEdit, 
    deleteProduct, 
    fetchProducts, 
    filteredProducts, 
    productSearch, 
    resetForm
} = useProducts()

// --- UI СТАНИ ---
const showTypeModal = ref(false)   // Маленьке вікно вибору типу
const showSimpleForm = ref(false)  // Велика форма простого товару
const showVariantForm = ref(false) // Велика форма варіантів
const isEditing = ref(false)

onMounted(async () => {
    await Promise.all([fetchWarehouseData(), fetchProducts()])
})

// --- ЛОГІКА ВІДКРИТТЯ ВІКОН ---

// 1. Натиснули "Додати товар" -> Відкриваємо вибір типу
const openCreateModal = () => {
    resetForm()
    isEditing.value = false
    showTypeModal.value = true
}

// 2. Обрали тип -> Відкриваємо відповідну форму
const selectType = (type) => {
    showTypeModal.value = false // Закриваємо вибір
    
    if (type === 'simple') {
        newProduct.value.has_variants = false
        showSimpleForm.value = true
    } else {
        newProduct.value.has_variants = true
        showVariantForm.value = true
    }
}

// 3. Натиснули "Редагувати" в таблиці
const handleEditWrapper = (product) => {
    originalHandleEdit(product)
    isEditing.value = true
    
    if (product.has_variants) {
         showVariantForm.value = true
    } else {
        showSimpleForm.value = true
    }
}

// 4. Логіка закриття (передається в компоненти)
const closeAllForms = () => {
    showSimpleForm.value = false
    showVariantForm.value = false
    resetForm()
}

// 5. Успішне збереження
const onSaved = async () => {
    await fetchProducts()
    // closeAllForms викликається автоматично через подію @close, якщо так налаштовано, 
    // або можна викликати тут, якщо компонент сам не закривається.
    // У нашому випадку компонент емітить 'saved', ми оновлюємо дані, 
    // а закриттям керує сам компонент через emit('close').
}
</script>

<template>
    <div class="h-full flex flex-col bg-white rounded-xl shadow-sm border overflow-hidden">
        
        <div class="p-6 border-b flex flex-col md:flex-row gap-4 justify-between items-center bg-gray-50">
            <h2 class="text-2xl font-bold text-gray-800">📦 Товари та Послуги</h2>
            <div class="flex gap-3 w-full md:w-auto">
                <div class="relative flex-1 md:w-64">
                    <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
                    <input v-model="productSearch" type="text" placeholder="Пошук..." class="pl-10 pr-4 py-2 border rounded-lg w-full focus:ring-2 focus:ring-blue-500 outline-none">
                </div>
                <button @click="openCreateModal" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 shadow-md transition flex items-center gap-2 font-medium">
                    <i class="fas fa-plus"></i> <span class="hidden sm:inline">Додати</span>
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-auto p-4 bg-gray-50">
            <div class="overflow-hidden rounded-xl border shadow-sm bg-white">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-gray-100 text-gray-600 uppercase text-xs font-semibold tracking-wider sticky top-0 z-10">
                        <tr>
                            <th class="p-4 border-b">Назва</th>
                            <th class="p-4 border-b">Категорія</th>
                            <th class="p-4 border-b">Ціна</th>
                            <th class="p-4 border-b">Тип</th>
                            <th class="p-4 border-b">Склад</th>
                            <th class="p-4 border-b text-center">Дії</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        <tr v-if="filteredProducts.length === 0">
                            <td colspan="6" class="p-8 text-center text-gray-400">Товарів не знайдено</td>
                        </tr>
                        <tr v-for="p in filteredProducts" :key="p.id" class="hover:bg-blue-50 transition group">
                            <td class="p-4 font-medium text-gray-800">
                                {{ p.name }}
                                <div class="text-xs text-gray-400 font-normal mt-0.5 max-w-xs truncate">{{ p.description }}</div>
                            </td>
                            <td class="p-4 text-sm">
                                <span v-if="p.category" class="bg-gray-100 text-gray-600 px-2 py-1 rounded font-medium text-xs border border-gray-200">
                                    {{ p.category.name }}
                                </span>
                                <span v-else class="text-gray-300">-</span>
                            </td>
                            <td class="p-4 font-bold text-green-600 font-mono">
                                <span v-if="!p.has_variants">{{ p.price }} ₴</span>
                                <span v-else class="text-xs text-gray-400 font-normal italic">від варіанту</span>
                            </td>
                            <td class="p-4">
                                <span v-if="p.has_variants" class="inline-flex items-center gap-1 text-[10px] bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-bold border border-purple-200">
                                    <i class="fas fa-layer-group"></i> Варіанти
                                </span>
                                <span v-else class="inline-flex items-center gap-1 text-[10px] bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-bold border border-blue-200">
                                    <i class="fas fa-box"></i> Простий
                                </span>
                            </td>
                            <td class="p-4 text-sm">
                                <div v-if="!p.has_variants">
                                    <div v-if="p.track_stock" class="font-mono font-bold" :class="p.stock_quantity > 0 ? 'text-blue-600' : 'text-red-500'">
                                        {{ p.stock_quantity }} шт
                                    </div>
                                    <div v-else class="text-gray-400 text-xs italic">Без обліку</div>
                                </div>
                                <div v-else class="text-xs text-gray-400 italic">Див. деталі</div>
                            </td>
                            <td class="p-4 text-center">
                                <div class="flex justify-center gap-2 opacity-0 group-hover:opacity-100 transition">
                                    <button @click="handleEditWrapper(p)" class="w-8 h-8 rounded flex items-center justify-center text-blue-500 hover:bg-blue-100 transition" title="Редагувати">
                                        <i class="fas fa-pen"></i>
                                    </button>
                                    <button @click="deleteProduct(p.id)" class="w-8 h-8 rounded flex items-center justify-center text-red-500 hover:bg-red-100 transition" title="Видалити">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div v-if="showTypeModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 backdrop-blur-sm animate-fade-in">
            <div class="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full text-center relative transform transition-all scale-100">
                <button @click="showTypeModal = false" class="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-xl"></i>
                </button>
                
                <h3 class="text-2xl font-bold mb-2 text-gray-800">Новий товар</h3>
                <p class="text-gray-500 mb-8 text-sm">Оберіть тип товару, який ви хочете створити</p>
                
                <div class="grid grid-cols-2 gap-4">
                    <button @click="selectType('simple')" class="p-6 border-2 border-gray-100 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition group flex flex-col items-center">
                        <div class="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition">☕</div>
                        <div class="font-bold text-gray-800">Простий</div>
                        <div class="text-[10px] text-gray-500 mt-1 leading-tight">Фіксована ціна,<br>один рецепт</div>
                    </button>

                    <button @click="selectType('variant')" class="p-6 border-2 border-gray-100 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition group flex flex-col items-center">
                        <div class="w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition">👕</div>
                        <div class="font-bold text-gray-800">З варіантами</div>
                        <div class="text-[10px] text-gray-500 mt-1 leading-tight">Різні розміри,<br>об'єми, ціни</div>
                    </button>
                </div>
            </div>
        </div>

        <ProductFormSimple 
            :isOpen="showSimpleForm"
            :isEdit="isEditing"
            @close="closeAllForms"
            @saved="onSaved"
        />

        <ProductFormVariant
            :isOpen="showVariantForm"
            :isEdit="isEditing"
            @close="closeAllForms"
            @saved="onSaved"
        />
        
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
</style>