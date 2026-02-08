<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'
// import IngredientSelect from '@/components/common/IngredientSelect.vue' // Якщо є компонент, можна розкоментувати

const props = defineProps({
    isOpen: Boolean,
    isEdit: Boolean
})

const emit = defineEmits(['close', 'saved'])

// Підключаємо глобальні довідники
const { categories, recipes, ingredients, consumables, processGroups } = useWarehouse()

// Підключаємо логіку роботи з товаром
const { 
    newProduct, 
    saveProduct,
    // Методи для варіантів
    saveVariant, editVariant, cancelVariantEdit, removeVariant,
    variantBuilder, editingVariantIndex,
    // Методи для унікальних інгредієнтів варіанту
    addIngredientToVariant, removeIngredientFromVariant,
    // Методи для унікальних матеріалів варіанту
    addVariantConsumable, removeVariantConsumable,
    tempVariantConsumable, tempVariantIngredient,
    // Методи для спільних матеріалів
    removeProductConsumable, addProductConsumable, tempProductConsumable
} = useProducts()

// --- ЛОКАЛЬНИЙ СТАН ---
const activeTab = ref('general')
const showVariantForm = ref(false)

// Тимчасова змінна для Спільних Інгредієнтів (локально, щоб не ламати useProducts)
const tempCommonIngredient = ref({ ingredient_id: "", quantity: 0 })

// --- МЕТОДИ ДЛЯ СПІЛЬНИХ ІНГРЕДІЄНТІВ ---
const addCommonIngredient = () => {
    if(!tempCommonIngredient.value.ingredient_id) return
    const ing = ingredients.value.find(x => x.id === tempCommonIngredient.value.ingredient_id)
    
    // Перевіряємо, чи існує масив (на випадок збою ініціалізації)
    if (!newProduct.value.ingredients) newProduct.value.ingredients = []

    newProduct.value.ingredients.push({ 
        ingredient_id: tempCommonIngredient.value.ingredient_id,
        quantity: tempCommonIngredient.value.quantity,
        name: ing?.name || '???' 
    })
    
    // Скидаємо
    tempCommonIngredient.value = { ingredient_id: "", quantity: 0 }
}

const removeCommonIngredient = (index) => {
    newProduct.value.ingredients.splice(index, 1)
}

// --- МЕТОДИ ВАРІАНТІВ ---
const openAddVariant = () => {
    cancelVariantEdit()
    showVariantForm.value = true
}

const handleEditVariant = (idx) => {
    editVariant(idx)
    showVariantForm.value = true
}

const closeVariantForm = () => {
    cancelVariantEdit()
    showVariantForm.value = false
}

const handleSaveVariant = () => {
    saveVariant()
    showVariantForm.value = false
}

const handleSaveProduct = async () => {
    const success = await saveProduct()
    if(success) emit('saved')
}

const toggleProcessGroup = (id) => {
    const index = newProduct.value.process_group_ids.indexOf(id)
    if (index === -1) {
        newProduct.value.process_group_ids.push(id)
    } else {
        newProduct.value.process_group_ids.splice(index, 1)
    }
}
</script>

<template>
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4 overflow-y-auto">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col animate-fade-in relative">
            
            <div class="px-8 py-5 border-b flex justify-between items-center bg-gray-50 rounded-t-2xl">
                <div>
                    <h2 class="text-2xl font-bold text-gray-800">
                        {{ isEdit ? 'Редагування товару' : 'Новий товар' }} (з варіантами)
                    </h2>
                    <p class="text-sm text-gray-500 mt-1">Налаштуйте загальні параметри та варіанти</p>
                </div>
                <button @click="emit('close')" class="w-10 h-10 rounded-full bg-white hover:bg-gray-100 flex items-center justify-center transition shadow-sm border text-gray-500">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <div class="flex flex-1 overflow-hidden">
                
                <div class="w-64 bg-gray-50 border-r flex flex-col p-4 space-y-2">
                    <button 
                        v-for="tab in [
                            { id: 'general', label: 'Основне', icon: 'fas fa-info-circle' },
                            { id: 'variants', label: 'Варіанти & Ціни', icon: 'fas fa-layer-group' },
                            { id: 'ingredients', label: 'Спільні інгредієнти', icon: 'fas fa-carrot' },
                            { id: 'consumables', label: 'Спільні матеріали', icon: 'fas fa-box-open' },
                        ]" 
                        :key="tab.id"
                        @click="activeTab = tab.id"
                        class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 text-left"
                        :class="activeTab === tab.id ? 'bg-white shadow-md text-purple-700 font-bold' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'"
                    >
                        <i :class="tab.icon" class="text-lg w-6 text-center"></i>
                        {{ tab.label }}
                    </button>
                </div>

                <div class="flex-1 overflow-y-auto p-8 relative">
                    
                    <div v-if="activeTab === 'general'" class="max-w-2xl mx-auto space-y-6 animate-slide-up">
                        
                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-2">Назва товару <span class="text-red-500">*</span></label>
                            <input 
                                v-model="newProduct.name" 
                                type="text" 
                                placeholder="Наприклад: Кава Лате" 
                                class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition text-lg"
                            >
                        </div>

                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-2">Категорія <span class="text-red-500">*</span></label>
                            <div class="relative">
                                <select 
                                    v-model="newProduct.category_id" 
                                    class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-purple-500 outline-none appearance-none bg-white cursor-pointer"
                                >
                                    <option :value="null" disabled>Оберіть категорію...</option>
                                    <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                                        {{ cat.name }}
                                    </option>
                                </select>
                                <i class="fas fa-chevron-down absolute right-4 top-3.5 text-gray-400 pointer-events-none"></i>
                            </div>
                        </div>

                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-3">Групи процесів (де готується)</label>
                            <div class="grid grid-cols-2 gap-3">
                                <div 
                                    v-for="group in processGroups" 
                                    :key="group.id"
                                    @click="toggleProcessGroup(group.id)"
                                    class="border rounded-xl p-3 cursor-pointer flex items-center justify-between transition-all select-none"
                                    :class="newProduct.process_group_ids.includes(group.id) ? 'bg-purple-50 border-purple-500 shadow-sm' : 'hover:border-gray-400 bg-white'"
                                >
                                    <span class="text-sm font-medium" :class="newProduct.process_group_ids.includes(group.id) ? 'text-purple-700' : 'text-gray-700'">
                                        {{ group.name }}
                                    </span>
                                    <div 
                                        class="w-5 h-5 rounded-full border flex items-center justify-center transition-colors"
                                        :class="newProduct.process_group_ids.includes(group.id) ? 'bg-purple-600 border-purple-600' : 'border-gray-300'"
                                    >
                                        <i v-if="newProduct.process_group_ids.includes(group.id)" class="fas fa-check text-white text-xs"></i>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-xl flex items-start gap-3">
                            <input 
                                id="manual-track-stock"
                                type="checkbox" 
                                v-model="newProduct.track_stock"
                                class="mt-1 w-5 h-5 text-purple-600 rounded border-gray-300 focus:ring-purple-500 cursor-pointer"
                            >
                            <div>
                                <label for="manual-track-stock" class="block font-bold text-gray-800 cursor-pointer select-none">
                                    Вести загальний облік залишків (Track Stock)
                                </label>
                                <p class="text-xs text-gray-600 mt-1">
                                    Увімкніть це, якщо хочете бути впевнені, що списання працюватиме глобально.
                                    (Зазвичай для товарів з варіантами це вимкнено, але ви можете увімкнути вручну).
                                </p>
                            </div>
                        </div>
                    </div>

                    <div v-if="activeTab === 'variants'" class="space-y-6 animate-slide-up">
                        <div class="flex justify-between items-center mb-4">
                            <h3 class="font-bold text-gray-800 text-lg">Список варіантів</h3>
                            <button @click="openAddVariant" class="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-gray-800 transition shadow-lg flex items-center gap-2">
                                <i class="fas fa-plus"></i> Додати варіант
                            </button>
                        </div>

                        <div v-if="newProduct.variants.length === 0" class="text-center py-12 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                            <i class="fas fa-layer-group text-4xl text-gray-300 mb-3"></i>
                            <p class="text-gray-500">Варіантів ще немає. Додайте перший!</p>
                        </div>

                        <div v-else class="grid gap-3">
                            <div 
                                v-for="(variant, idx) in newProduct.variants" 
                                :key="idx"
                                class="bg-white border rounded-xl p-4 flex justify-between items-center hover:shadow-md transition group"
                            >
                                <div>
                                    <h4 class="font-bold text-gray-800">{{ variant.name }}</h4>
                                    <div class="flex items-center gap-3 text-sm text-gray-500 mt-1">
                                        <span class="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-bold">{{ variant.price }} ₴</span>
                                        <span v-if="variant.sku" class="bg-gray-100 px-2 py-0.5 rounded text-xs">SKU: {{ variant.sku }}</span>
                                        <span v-if="variant.stock_quantity" class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">Залишок: {{ variant.stock_quantity }}</span>
                                    </div>
                                </div>
                                <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button @click="handleEditVariant(idx)" class="w-8 h-8 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 flex items-center justify-center">
                                        <i class="fas fa-pencil-alt text-sm"></i>
                                    </button>
                                    <button @click="removeVariant(idx)" class="w-8 h-8 rounded bg-red-50 text-red-500 hover:bg-red-100 flex items-center justify-center">
                                        <i class="fas fa-trash text-sm"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-if="activeTab === 'ingredients'" class="max-w-3xl mx-auto animate-slide-up">
                        <div class="bg-orange-50 border border-orange-100 rounded-xl p-4 mb-6">
                            <div class="flex gap-3">
                                <i class="fas fa-info-circle text-orange-500 mt-0.5"></i>
                                <p class="text-sm text-orange-700">
                                    Інгредієнти, які додаються до <strong>кожного</strong> варіанту (наприклад: вода для кави, якщо вона однакова для всіх об'ємів, або база).
                                </p>
                            </div>
                        </div>

                        <div class="flex gap-2 items-end mb-4 bg-white p-4 rounded-xl border shadow-sm">
                            <div class="flex-1">
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Оберіть інгредієнт</label>
                                <select v-model="tempCommonIngredient.ingredient_id" class="w-full p-2 border rounded-lg text-sm bg-gray-50">
                                    <option value="" disabled>Оберіть зі списку...</option>
                                    <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">
                                        {{ ing.name }} ({{ ing.stock_quantity }} {{ ing.unit?.symbol }})
                                    </option>
                                </select>
                            </div>
                            <div class="w-24">
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Кількість</label>
                                <input type="number" v-model="tempCommonIngredient.quantity" class="w-full p-2 border rounded-lg text-sm text-center" step="0.1">
                            </div>
                            <button @click="addCommonIngredient" class="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-bold text-sm h-[38px]">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>

                        <div class="space-y-2">
                            <div v-for="(item, index) in newProduct.ingredients" :key="index" class="flex justify-between items-center p-3 bg-white border rounded-lg hover:bg-gray-50">
                                <div class="flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">
                                        {{ index + 1 }}
                                    </div>
                                    <span class="font-medium text-gray-800">{{ item.name }}</span>
                                </div>
                                <div class="flex items-center gap-4">
                                    <span class="bg-gray-100 px-2 py-1 rounded text-sm font-mono">{{ item.quantity }} од.</span>
                                    <button @click="removeCommonIngredient(index)" class="text-gray-400 hover:text-red-500 transition">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            <div v-if="!newProduct.ingredients || newProduct.ingredients.length === 0" class="text-center py-8 text-gray-400 text-sm italic">
                                Немає спільних інгредієнтів
                            </div>
                        </div>
                    </div>

                    <div v-if="activeTab === 'consumables'" class="max-w-3xl mx-auto animate-slide-up">
                        <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
                            <div class="flex gap-3">
                                <i class="fas fa-info-circle text-blue-500 mt-0.5"></i>
                                <p class="text-sm text-blue-700">
                                    Тут додаються матеріали, які списуються <strong>при продажу будь-якого варіанту</strong> 
                                    (наприклад: серветка, трубочка, пакет).
                                </p>
                            </div>
                        </div>

                        <div class="flex gap-2 items-end mb-4 bg-white p-4 rounded-xl border shadow-sm">
                            <div class="flex-1">
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Оберіть матеріал</label>
                                <select v-model="tempProductConsumable.consumable_id" class="w-full p-2 border rounded-lg text-sm bg-gray-50">
                                    <option value="" disabled>Оберіть зі списку...</option>
                                    <option v-for="c in consumables" :key="c.id" :value="c.id">
                                        {{ c.name }} ({{ c.stock_quantity }} {{ c.unit?.symbol }})
                                    </option>
                                </select>
                            </div>
                            <div class="w-24">
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Кількість</label>
                                <input type="number" v-model="tempProductConsumable.quantity" class="w-full p-2 border rounded-lg text-sm text-center" min="1">
                            </div>
                            <button @click="addProductConsumable" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-bold text-sm h-[38px]">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>

                        <div class="space-y-2">
                            <div v-for="(item, index) in newProduct.consumables" :key="index" class="flex justify-between items-center p-3 bg-white border rounded-lg hover:bg-gray-50">
                                <div class="flex items-center gap-3">
                                    <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                                        {{ index + 1 }}
                                    </div>
                                    <span class="font-medium text-gray-800">{{ item.name }}</span>
                                </div>
                                <div class="flex items-center gap-4">
                                    <span class="bg-gray-100 px-2 py-1 rounded text-sm font-mono">x {{ item.quantity }}</span>
                                    <button @click="removeProductConsumable(index)" class="text-gray-400 hover:text-red-500 transition">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            <div v-if="newProduct.consumables.length === 0" class="text-center py-8 text-gray-400 text-sm italic">
                                Немає спільних матеріалів
                            </div>
                        </div>
                    </div>

                </div>
            </div>

            <div class="px-8 py-5 border-t bg-gray-50 rounded-b-2xl flex justify-between items-center">
                <button @click="emit('close')" class="text-gray-500 hover:text-gray-800 font-medium px-4 py-2 rounded-lg hover:bg-gray-200 transition">
                    Скасувати
                </button>
                <button 
                    @click="handleSaveProduct" 
                    class="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 hover:shadow-xl active:scale-95 transition flex items-center gap-2"
                >
                    <i class="fas fa-save"></i> Зберегти товар
                </button>
            </div>

            <div v-if="showVariantForm" class="absolute inset-0 z-50 bg-black bg-opacity-20 backdrop-blur-sm flex items-center justify-center p-4">
                <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[85vh] animate-slide-up border border-gray-200">
                    <div class="p-4 border-b flex justify-between items-center bg-purple-50 rounded-t-xl">
                        <h3 class="font-bold text-purple-900 flex items-center gap-2">
                            <i class="fas fa-cubes"></i> {{ editingVariantIndex !== null ? 'Редагувати варіант' : 'Новий варіант' }}
                        </h3>
                        <button @click="closeVariantForm" class="text-gray-400 hover:text-gray-600"><i class="fas fa-times"></i></button>
                    </div>
                    
                    <div class="p-6 overflow-y-auto space-y-5">
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Назва варіанту <span class="text-red-500">*</span></label>
                                <input v-model="variantBuilder.name" type="text" placeholder="S / M / L" class="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">SKU (Артикул)</label>
                                <input v-model="variantBuilder.sku" type="text" placeholder="CODE-123" class="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none">
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Ціна (₴) <span class="text-red-500">*</span></label>
                                <input v-model.number="variantBuilder.price" type="number" class="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Поточний залишок</label>
                                <input v-model.number="variantBuilder.stock_quantity" type="number" class="w-full p-2.5 border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none bg-yellow-50">
                            </div>
                        </div>

                        <div class="pt-4 border-t">
                             <label class="block text-sm font-bold text-gray-800 mb-2">Технологічна карта (Рецепт)</label>
                             <select v-model="variantBuilder.master_recipe_id" class="w-full p-2.5 border rounded-lg bg-gray-50 mb-3">
                                <option :value="null">Без рецепту</option>
                                <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                            </select>
                            
                            <div v-if="variantBuilder.master_recipe_id" class="mb-3">
                                <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Вага виходу (г/мл)</label>
                                <input v-model.number="variantBuilder.output_weight" type="number" class="w-full p-2 border rounded-lg">
                                <p class="text-xs text-gray-400 mt-1">Потрібно для розрахунку % інгредієнтів</p>
                            </div>
                        </div>

                        <div class="pt-4 border-t">
                            <label class="block text-sm font-bold text-gray-800 mb-2">Унікальні матеріали варіанту</label>
                            <div class="bg-gray-50 p-3 rounded-lg">
                                <div class="flex gap-2 mb-2">
                                     <select v-model="tempVariantConsumable.consumable_id" class="flex-1 p-2 border rounded text-sm">
                                        <option value="" disabled>Оберіть матеріал...</option>
                                        <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                    </select>
                                    <input type="number" v-model="tempVariantConsumable.quantity" class="w-20 p-2 border rounded text-sm text-center" min="1">
                                    <button @click="addVariantConsumable" class="px-3 bg-purple-600 text-white rounded"><i class="fas fa-plus"></i></button>
                                </div>
                                 <div class="bg-white rounded border divide-y max-h-40 overflow-y-auto">
                                     <div v-for="(c, idx) in variantBuilder.consumables" :key="idx" class="p-2 text-sm flex justify-between">
                                        <span>{{ c.name || '???' }}</span>
                                        <span>{{ c.quantity }} шт <i @click="removeVariantConsumable(idx)" class="fas fa-times text-red-500 cursor-pointer ml-2"></i></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="p-4 border-t bg-white flex justify-end gap-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
                        <button @click="closeVariantForm" class="px-5 py-2 border rounded-lg text-gray-600 hover:bg-gray-50">Скасувати</button>
                        <button @click="handleSaveVariant" class="px-5 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 shadow-md">
                            <i class="fas fa-check mr-1"></i> Зберегти варіант
                        </button>
                    </div>
                </div>

            </div>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
.animate-slide-up { animation: slideUp 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
@keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>