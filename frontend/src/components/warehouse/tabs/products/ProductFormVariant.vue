<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'
import IngredientSelect from '@/components/common/IngredientSelect.vue'

const props = defineProps({
    isOpen: Boolean,
    isEdit: Boolean
})

const emit = defineEmits(['close', 'saved'])

const { categories, recipes, ingredients, consumables } = useWarehouse()
const { 
    newProduct, 
    saveProduct,
    removeProductConsumable, // Для спільних матеріалів
    // Методи для роботи з варіантами з useProducts
    saveVariant, editVariant, cancelVariantEdit, removeVariant,
    variantBuilder, editingVariantIndex,
    // Методи для інгредієнтів варіанту
    addIngredientToVariant, removeIngredientFromVariant,
    // Методи для матеріалів варіанту
    addVariantConsumable, removeVariantConsumable,
    tempVariantConsumable, tempVariantIngredient
} = useProducts()

const activeTab = ref('general')
const showVariantForm = ref(false) // Чи відкрита форма редагування конкретного варіанту

// Відкриття форми додавання нового варіанту
const openAddVariant = () => {
    cancelVariantEdit() // Скидаємо білдер
    showVariantForm.value = true
}

// Відкриття форми редагування існуючого варіанту
const openEditVariant = (index) => {
    editVariant(index) // Заповнюємо білдер даними варіанту
    showVariantForm.value = true
}

// Збереження варіанту (з локальної форми в список newProduct.variants)
const handleSaveVariant = () => {
    if (!variantBuilder.value.name || variantBuilder.value.price <= 0) {
        alert("Вкажіть назву та ціну варіанту")
        return
    }
    saveVariant()
    showVariantForm.value = false
}

// Закриття форми варіанту
const closeVariantForm = () => {
    cancelVariantEdit()
    showVariantForm.value = false
}

// Додавання спільних витратних матеріалів
const tempCommonConsumable = ref({ consumable_id: "", quantity: 1 })
const addCommonConsumable = () => {
     if (tempCommonConsumable.value.consumable_id) {
        const c = consumables.value.find(x => x.id === tempCommonConsumable.value.consumable_id)
        if (!newProduct.value.consumables) newProduct.value.consumables = []
        newProduct.value.consumables.push({
            consumable_id: tempCommonConsumable.value.consumable_id,
            quantity: tempCommonConsumable.value.quantity,
            name: c?.name || '???'
        })
        tempCommonConsumable.value.quantity = 1
    }
}

// Головне збереження товару
const handleSave = async () => {
    if (newProduct.value.variants.length === 0) {
        alert("Додайте хоча б один варіант товару")
        return
    }
    newProduct.value.has_variants = true // Гарантуємо тип
    const success = await saveProduct()
    if (success) {
        emit('saved')
        emit('close')
    }
}

// Скидання табів при відкритті
watch(() => props.isOpen, (val) => {
    if (val) {
        activeTab.value = 'general'
        showVariantForm.value = false
    }
})
</script>

<template>
    <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden animate-fade-in relative">
            
            <div class="p-6 border-b flex justify-between items-center bg-purple-50">
                <h3 class="text-xl font-bold text-purple-800">
                    <i class="fas fa-layer-group mr-2"></i>
                    {{ isEdit ? 'Редагування товару з варіантами' : 'Новий товар з варіантами' }}
                </h3>
                <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-xl"></i>
                </button>
            </div>

            <div class="flex border-b bg-white px-6">
                <button @click="activeTab = 'general'" :class="['py-3 px-4 font-medium border-b-2 transition', activeTab === 'general' ? 'border-purple-500 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700']">
                    Основне
                </button>
                <button @click="activeTab = 'variants'" :class="['py-3 px-4 font-medium border-b-2 transition', activeTab === 'variants' ? 'border-purple-500 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700']">
                    Варіанти <span class="ml-1 bg-purple-100 text-purple-600 px-2 rounded-full text-xs">{{ newProduct.variants.length }}</span>
                </button>
                 <button @click="activeTab = 'common'" :class="['py-3 px-4 font-medium border-b-2 transition', activeTab === 'common' ? 'border-purple-500 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700']">
                    Спільні матеріали
                </button>
            </div>

            <div class="p-6 overflow-y-auto flex-1 space-y-6 bg-gray-50">
                
                <div v-if="activeTab === 'general'" class="bg-white p-6 rounded-lg shadow-sm space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Загальна назва</label>
                            <input v-model="newProduct.name" type="text" class="w-full border rounded-lg p-2 focus:ring-2 focus:ring-purple-500" placeholder="Напр: Піца Маргарита">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Категорія</label>
                            <select v-model="newProduct.category_id" class="w-full border rounded-lg p-2">
                                <option :value="null">Без категорії</option>
                                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Опис (необов'язково)</label>
                        <textarea v-model="newProduct.description" rows="3" class="w-full border rounded-lg p-2"></textarea>
                    </div>
                </div>

                <div v-if="activeTab === 'variants'" class="space-y-4">
                    <button @click="openAddVariant" class="w-full py-3 bg-white border-2 border-dashed border-purple-300 text-purple-600 rounded-lg hover:bg-purple-50 transition font-medium flex items-center justify-center gap-2">
                        <i class="fas fa-plus-circle"></i> Додати варіант (напр. "Маленька", "Велика")
                    </button>

                    <div v-if="newProduct.variants.length > 0" class="bg-white rounded-lg shadow-sm border divide-y overflow-hidden">
                        <div v-for="(v, idx) in newProduct.variants" :key="idx" class="p-4 flex justify-between items-center hover:bg-gray-50">
                            <div>
                                <h4 class="font-bold text-gray-800">{{ v.name }}</h4>
                                <div class="text-sm text-gray-500 flex gap-4 mt-1">
                                    <span><i class="fas fa-tag mr-1"></i> {{ v.price }} ₴</span>
                                    <span v-if="v.sku"><i class="fas fa-barcode mr-1"></i> {{ v.sku }}</span>
                                </div>
                            </div>
                             <div class="flex gap-2">
                                <button @click="openEditVariant(idx)" class="px-3 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition text-sm">
                                    <i class="fas fa-pen mr-1"></i> Ред.
                                </button>
                                <button @click="removeVariant(idx)" class="px-3 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100 transition text-sm">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div v-else class="text-center text-gray-400 py-8">
                        Список варіантів порожній
                    </div>
                </div>

                <div v-if="activeTab === 'common'" class="bg-white p-6 rounded-lg shadow-sm space-y-6">
                     <div class="border p-4 rounded-lg bg-blue-50">
                        <h4 class="font-bold text-gray-800 mb-2 flex items-center gap-2">
                            <i class="fas fa-box-open text-blue-600"></i> Спільні витратні матеріали
                        </h4>
                        <p class="text-xs text-gray-500 mb-3">Додаються до замовлення незалежно від обраного варіанту (напр. пакет, серветка).</p>
                        
                        <div class="flex gap-2 items-end mb-3">
                            <div class="flex-1">
                                <select v-model="tempCommonConsumable.consumable_id" class="w-full border rounded p-2">
                                    <option value="">Оберіть матеріал...</option>
                                    <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                </select>
                            </div>
                            <div class="w-20">
                                <input v-model.number="tempCommonConsumable.quantity" type="number" class="w-full border rounded p-2">
                            </div>
                            <button @click="addCommonConsumable" class="bg-blue-500 text-white p-2 rounded hover:bg-blue-600">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div v-if="newProduct.consumables?.length" class="bg-white rounded border divide-y">
                            <div v-for="(c, idx) in newProduct.consumables" :key="idx" class="p-2 flex justify-between items-center text-sm">
                                <span>{{ c.name || c.consumable_name }}</span>
                                <div class="flex items-center gap-2">
                                    <span class="font-bold">{{ c.quantity }} шт</span>
                                    <button @click="removeProductConsumable(idx)" class="text-red-500 hover:text-red-700">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                     </div>
                 </div>
            </div>

            <div class="p-6 border-t bg-white flex justify-end gap-3">
                <button @click="$emit('close')" class="px-6 py-2 border rounded-lg text-gray-600 hover:bg-gray-100">
                    Скасувати
                </button>
                <button @click="handleSave" class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium shadow-lg transition" :disabled="newProduct.variants.length === 0">
                    {{ isEdit ? 'Зберегти товар' : 'Створити товар' }}
                </button>
            </div>

            <div v-if="showVariantForm" class="absolute inset-0 bg-white z-50 flex flex-col animate-slide-up">
                <div class="p-4 border-b bg-purple-50 flex justify-between items-center">
                     <h4 class="font-bold text-purple-800">
                        {{ editingVariantIndex !== null ? 'Редагування варіанту' : 'Новий варіант' }}
                    </h4>
                    <button @click="closeVariantForm" class="text-gray-500 hover:text-gray-700">
                         <i class="fas fa-chevron-down"></i> Згорнути
                    </button>
                </div>
                
                <div class="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
                    <div class="bg-white p-4 rounded-lg shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="md:col-span-2">
                            <label class="block text-sm font-medium mb-1">Назва варіанту <span class="text-red-500">*</span></label>
                            <input v-model="variantBuilder.name" type="text" class="w-full border rounded p-2" placeholder="Напр: Велика (40см)">
                        </div>
                         <div>
                            <label class="block text-sm font-medium mb-1">Артикул (SKU)</label>
                            <input v-model="variantBuilder.sku" type="text" class="w-full border rounded p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-1 text-purple-800">Ціна (₴) <span class="text-red-500">*</span></label>
                            <input v-model.number="variantBuilder.price" type="number" class="w-full border rounded p-2 font-bold">
                        </div>
                         <div>
                             <label class="block text-sm font-medium mb-1">Поточний залишок</label>
                             <input v-model.number="variantBuilder.stock_quantity" type="number" class="w-full border rounded p-2">
                        </div>
                    </div>

                    <div class="bg-white p-4 rounded-lg shadow-sm border-l-4 border-orange-400 grid grid-cols-1 md:grid-cols-2 gap-4">
                         <div>
                            <label class="block text-sm font-medium mb-1">Технічна карта</label>
                            <select v-model="variantBuilder.master_recipe_id" class="w-full border rounded p-2">
                                <option :value="null">-- Без рецепту --</option>
                                <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                            </select>
                        </div>
                         <div>
                            <label class="block text-sm font-medium mb-1">Вага виходу (для рецепту)</label>
                            <input v-model.number="variantBuilder.output_weight" type="number" class="w-full border rounded p-2">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-yellow-50 p-4 rounded-lg border">
                            <h5 class="font-bold mb-2 text-yellow-800">Унікальні інгредієнти</h5>
                            <div class="flex gap-2 mb-2">
                                <IngredientSelect v-model="tempVariantIngredient.ingredient_id" class="flex-1" />
                                <input v-model.number="tempVariantIngredient.quantity" type="number" class="w-20 border rounded p-1" placeholder="К-сть">
                                <button @click="addIngredientToVariant" class="bg-yellow-500 text-white px-2 rounded"><i class="fas fa-plus"></i></button>
                            </div>
                            <div class="bg-white rounded border divide-y max-h-40 overflow-y-auto">
                                 <div v-for="(ing, idx) in variantBuilder.ingredients" :key="idx" class="p-2 text-sm flex justify-between">
                                    <span>{{ ing.name || '???' }}</span>
                                    <span>{{ ing.quantity }} <i @click="removeIngredientFromVariant(idx)" class="fas fa-times text-red-500 cursor-pointer ml-2"></i></span>
                                </div>
                            </div>
                        </div>
                        <div class="bg-blue-50 p-4 rounded-lg border">
                            <h5 class="font-bold mb-2 text-blue-800">Унікальні матеріали (тара)</h5>
                             <div class="flex gap-2 mb-2">
                                <select v-model="tempVariantConsumable.consumable_id" class="flex-1 border rounded p-1 text-sm">
                                    <option value="">Оберіть...</option>
                                    <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                </select>
                                <input v-model.number="tempVariantConsumable.quantity" type="number" class="w-16 border rounded p-1" placeholder="Шт">
                                <button @click="addVariantConsumable" class="bg-blue-500 text-white px-2 rounded"><i class="fas fa-plus"></i></button>
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

                <div class="p-4 border-t bg-white flex justify-end gap-3">
                    <button @click="closeVariantForm" class="px-4 py-2 border rounded text-gray-600">Скасувати</button>
                    <button @click="handleSaveVariant" class="px-4 py-2 bg-purple-600 text-white rounded font-medium">
                        <i class="fas fa-check mr-1"></i> Зберегти варіант
                    </button>
                </div>
            </div>

        </div>
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
.animate-slide-up { animation: slideUp 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>