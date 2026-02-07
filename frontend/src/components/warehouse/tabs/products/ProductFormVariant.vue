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

// Підключаємо глобальні довідники (включаючи processGroups!)
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
    removeProductConsumable
} = useProducts()

// --- ЛОКАЛЬНИЙ СТАН ---
const activeTab = ref('general')
const showVariantForm = ref(false)

// Тимчасові змінні для додавання
const tempCommonIngredient = ref({ id: null, qty: 0 })
const tempCommonConsumable = ref({ consumable_id: "", quantity: 1 })
const tempProcessGroup = ref({ id: "" }) // Для процесів

// --- МЕТОДИ ДЛЯ СПІЛЬНИХ ІНГРЕДІЄНТІВ ---
const addCommonIngredient = () => {
    if (tempCommonIngredient.value.id && tempCommonIngredient.value.qty > 0) {
        if (!newProduct.value.ingredients) newProduct.value.ingredients = []
        
        const existing = newProduct.value.ingredients.find(i => i.ingredient_id === tempCommonIngredient.value.id)
        const ingObj = ingredients.value.find(i => i.id === tempCommonIngredient.value.id)

        if (existing) {
            existing.quantity += parseFloat(tempCommonIngredient.value.qty)
        } else {
            newProduct.value.ingredients.push({
                ingredient_id: tempCommonIngredient.value.id,
                quantity: parseFloat(tempCommonIngredient.value.qty),
                ingredient_name: ingObj?.name || '???'
            })
        }
        tempCommonIngredient.value = { id: null, qty: 0 }
    }
}
const removeCommonIngredient = (index) => {
    newProduct.value.ingredients.splice(index, 1)
}

// --- МЕТОДИ ДЛЯ СПІЛЬНИХ МАТЕРІАЛІВ ---
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

// --- МЕТОДИ ДЛЯ СПІЛЬНИХ ПРОЦЕСІВ ---
const addProcessGroup = () => {
    if (tempProcessGroup.value.id) {
        const pg = processGroups.value.find(p => p.id === tempProcessGroup.value.id)
        if (!newProduct.value.process_groups) newProduct.value.process_groups = []
        
        // Перевірка на дублікати
        if (!newProduct.value.process_groups.find(p => p.id === pg.id)) {
            newProduct.value.process_groups.push(pg)
        }
        tempProcessGroup.value.id = ""
    }
}
const removeProcessGroup = (index) => {
    newProduct.value.process_groups.splice(index, 1)
}

// --- УПРАВЛІННЯ ВАРІАНТАМИ ---
const openAddVariant = () => {
    cancelVariantEdit()
    showVariantForm.value = true
}
const openEditVariant = (index) => {
    editVariant(index)
    showVariantForm.value = true
}
const handleSaveVariant = () => {
    if (!variantBuilder.value.name || variantBuilder.value.price <= 0) {
        alert("Вкажіть назву та ціну варіанту")
        return
    }
    saveVariant()
    showVariantForm.value = false
}
const closeVariantForm = () => {
    cancelVariantEdit()
    showVariantForm.value = false
}

// --- ГОЛОВНЕ ЗБЕРЕЖЕННЯ ---
const handleSave = async () => {
    if (newProduct.value.variants.length === 0) {
        alert("Додайте хоча б один варіант товару")
        return
    }
    newProduct.value.has_variants = true
    const success = await saveProduct()
    if (success) {
        emit('saved')
        emit('close')
    }
}

// Скидання при відкритті
watch(() => props.isOpen, (val) => {
    if (val) {
        activeTab.value = 'general'
        showVariantForm.value = false
    }
})

// Допоміжні функції для відображення цін
const getIngredientPrice = (id) => ingredients.value.find(i => i.id === id)?.cost_per_unit || 0
const getConsumablePrice = (id) => consumables.value.find(c => c.id === id)?.cost_per_unit || 0
</script>

<template>
    <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[95vh] flex flex-col overflow-hidden animate-fade-in relative">
            
            <div class="p-5 border-b flex justify-between items-center bg-purple-50">
                <h3 class="text-xl font-bold text-purple-900 flex items-center gap-2">
                    <span class="bg-purple-200 text-purple-700 p-2 rounded-lg text-lg">👕</span>
                    {{ isEdit ? 'Редагування товару з варіантами' : 'Новий товар з варіантами' }}
                </h3>
                <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-purple-100 transition">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <div class="flex border-b bg-white px-2 overflow-x-auto">
                <button @click="activeTab = 'general'" :class="['py-3 px-4 font-medium border-b-2 transition whitespace-nowrap', activeTab === 'general' ? 'border-purple-600 text-purple-700 bg-purple-50/50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50']">
                    1. Основне
                </button>
                <button @click="activeTab = 'variants'" :class="['py-3 px-4 font-medium border-b-2 transition whitespace-nowrap', activeTab === 'variants' ? 'border-purple-600 text-purple-700 bg-purple-50/50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50']">
                    2. Варіанти <span class="ml-1 bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full text-xs border border-purple-200">{{ newProduct.variants.length }}</span>
                </button>
                <button @click="activeTab = 'common_ingredients'" :class="['py-3 px-4 font-medium border-b-2 transition whitespace-nowrap', activeTab === 'common_ingredients' ? 'border-purple-600 text-purple-700 bg-purple-50/50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50']">
                    3. Спільні інгредієнти
                </button>
                <button @click="activeTab = 'common_consumables'" :class="['py-3 px-4 font-medium border-b-2 transition whitespace-nowrap', activeTab === 'common_consumables' ? 'border-purple-600 text-purple-700 bg-purple-50/50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50']">
                    4. Спільні матеріали
                </button>
                <button @click="activeTab = 'common_processes'" :class="['py-3 px-4 font-medium border-b-2 transition whitespace-nowrap', activeTab === 'common_processes' ? 'border-purple-600 text-purple-700 bg-purple-50/50' : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50']">
                    5. Спільні процеси
                </button>
            </div>

            <div class="p-6 overflow-y-auto flex-1 bg-white">
                
                <div v-show="activeTab === 'general'" class="space-y-6 animate-fade-in">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-1">Загальна назва</label>
                            <input v-model="newProduct.name" type="text" class="w-full border rounded-lg p-2.5 focus:ring-2 focus:ring-purple-500" placeholder="Напр: Піца Маргарита">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Категорія</label>
                            <select v-model="newProduct.category_id" class="w-full border rounded-lg p-2.5 bg-white">
                                <option :value="null">Без категорії</option>
                                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Опис</label>
                        <textarea v-model="newProduct.description" rows="3" class="w-full border rounded-lg p-2.5" placeholder="Опис товару для меню..."></textarea>
                    </div>
                </div>

                <div v-show="activeTab === 'variants'" class="space-y-4 animate-fade-in">
                    <button @click="openAddVariant" class="w-full py-4 bg-white border-2 border-dashed border-purple-300 text-purple-600 rounded-xl hover:bg-purple-50 hover:border-purple-400 transition font-medium flex items-center justify-center gap-2 group">
                        <div class="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center group-hover:bg-purple-200 transition">
                            <i class="fas fa-plus"></i>
                        </div>
                        <span>Додати варіант (напр. "Маленька", "Велика")</span>
                    </button>

                    <div v-if="newProduct.variants.length > 0" class="grid grid-cols-1 gap-3">
                        <div v-for="(v, idx) in newProduct.variants" :key="idx" class="p-4 bg-white border rounded-xl shadow-sm hover:shadow-md transition flex justify-between items-center group">
                            <div class="flex items-center gap-4">
                                <div class="w-10 h-10 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-bold">
                                    {{ idx + 1 }}
                                </div>
                                <div>
                                    <h4 class="font-bold text-gray-800 text-lg">{{ v.name }}</h4>
                                    <div class="text-sm text-gray-500 flex gap-4">
                                        <span class="bg-green-100 text-green-700 px-2 py-0.5 rounded border border-green-200 font-mono font-bold">{{ v.price }} ₴</span>
                                        <span v-if="v.sku"><i class="fas fa-barcode mr-1 text-gray-400"></i> {{ v.sku }}</span>
                                    </div>
                                </div>
                            </div>
                             <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition">
                                <button @click="openEditVariant(idx)" class="px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 font-medium">
                                    <i class="fas fa-pen mr-1"></i> Ред.
                                </button>
                                <button @click="removeVariant(idx)" class="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 font-medium">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div v-else class="text-center text-gray-400 py-8 bg-gray-50 rounded-xl border border-gray-100">
                        Список варіантів порожній. Додайте хоча б один.
                    </div>
                </div>

                <div v-show="activeTab === 'common_ingredients'" class="space-y-6 animate-fade-in">
                    <div class="bg-yellow-50 p-4 rounded-xl border border-yellow-100">
                        <h4 class="font-bold text-yellow-800 mb-2 flex items-center gap-2">
                            <i class="fas fa-lemon"></i> Спільні інгредієнти
                        </h4>
                        <p class="text-xs text-yellow-700 mb-4">
                            Ці інгредієнти будуть списані при продажі <strong>будь-якого</strong> варіанту цього товару (наприклад, посипка, яка йде до всіх розмірів).
                        </p>
                        
                        <div class="flex gap-2 mb-4">
                            <IngredientSelect v-model="tempCommonIngredient.id" :ingredients="ingredients" class="flex-1" />
                            <input v-model.number="tempCommonIngredient.qty" type="number" step="0.001" placeholder="К-сть" class="w-24 border rounded-lg p-2">
                            <button @click="addCommonIngredient" class="bg-yellow-500 text-white px-4 rounded-lg hover:bg-yellow-600 font-medium"><i class="fas fa-plus"></i></button>
                        </div>

                        <div v-if="newProduct.ingredients?.length" class="bg-white rounded-lg border overflow-hidden">
                            <table class="w-full text-sm">
                                <thead class="bg-gray-50 text-gray-500 text-left text-xs uppercase">
                                    <tr>
                                        <th class="p-3 pl-4">Назва</th>
                                        <th class="p-3">К-сть</th>
                                        <th class="p-3 text-right">Вартість</th>
                                        <th class="p-3 w-10"></th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y">
                                    <tr v-for="(ing, idx) in newProduct.ingredients" :key="idx">
                                        <td class="p-3 pl-4 font-medium">{{ ing.ingredient_name }}</td>
                                        <td class="p-3">{{ ing.quantity }}</td>
                                        <td class="p-3 text-right font-mono text-gray-600">
                                            {{ (ing.quantity * getIngredientPrice(ing.ingredient_id)).toFixed(2) }} ₴
                                        </td>
                                        <td class="p-3 text-center">
                                            <button @click="removeCommonIngredient(idx)" class="text-red-400 hover:text-red-600"><i class="fas fa-times"></i></button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div v-show="activeTab === 'common_consumables'" class="space-y-6 animate-fade-in">
                     <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
                        <h4 class="font-bold text-blue-800 mb-2 flex items-center gap-2">
                            <i class="fas fa-box-open"></i> Спільні витратні матеріали
                        </h4>
                        <p class="text-xs text-blue-700 mb-4">
                            Додаються до замовлення незалежно від варіанту (наприклад, пакет, серветка, ложка).
                        </p>
                        
                        <div class="flex gap-2 mb-4">
                            <select v-model="tempCommonConsumable.consumable_id" class="flex-1 border rounded-lg p-2 bg-white">
                                <option value="">Оберіть матеріал...</option>
                                <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                            <input v-model.number="tempCommonConsumable.quantity" type="number" class="w-24 border rounded-lg p-2" placeholder="Шт">
                            <button @click="addCommonConsumable" class="bg-blue-500 text-white px-4 rounded-lg hover:bg-blue-600 font-medium"><i class="fas fa-plus"></i></button>
                        </div>

                         <div v-if="newProduct.consumables?.length" class="bg-white rounded-lg border overflow-hidden">
                            <table class="w-full text-sm">
                                <thead class="bg-gray-50 text-gray-500 text-left text-xs uppercase">
                                    <tr>
                                        <th class="p-3 pl-4">Назва</th>
                                        <th class="p-3">К-сть</th>
                                        <th class="p-3 text-right">Вартість</th>
                                        <th class="p-3 w-10"></th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y">
                                    <tr v-for="(c, idx) in newProduct.consumables" :key="idx">
                                        <td class="p-3 pl-4 font-medium">{{ c.name || c.consumable_name }}</td>
                                        <td class="p-3">{{ c.quantity }} шт</td>
                                        <td class="p-3 text-right font-mono text-gray-600">
                                            {{ (c.quantity * getConsumablePrice(c.consumable_id)).toFixed(2) }} ₴
                                        </td>
                                        <td class="p-3 text-center">
                                            <button @click="removeProductConsumable(idx)" class="text-red-400 hover:text-red-600"><i class="fas fa-times"></i></button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                     </div>
                 </div>

                <div v-show="activeTab === 'common_processes'" class="space-y-6 animate-fade-in">
                    <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                        <h4 class="font-bold text-indigo-800 mb-2 flex items-center gap-2">
                            <i class="fas fa-cogs"></i> Спільні процеси
                        </h4>
                        <p class="text-xs text-indigo-700 mb-4">
                            Групи налаштувань (модифікаторів), які будуть доступні на касі для цього товару (наприклад: "Вибір молока", "Ступінь помелу").
                        </p>

                        <div class="flex gap-2 mb-4">
                            <select v-model="tempProcessGroup.id" class="flex-1 border rounded-lg p-2 bg-white">
                                <option value="">Оберіть групу процесів...</option>
                                <option v-for="pg in processGroups" :key="pg.id" :value="pg.id">{{ pg.name }}</option>
                            </select>
                            <button @click="addProcessGroup" class="bg-indigo-500 text-white px-4 rounded-lg hover:bg-indigo-600 font-medium"><i class="fas fa-plus"></i> Додати</button>
                        </div>

                        <div v-if="newProduct.process_groups?.length" class="space-y-2">
                            <div v-for="(pg, idx) in newProduct.process_groups" :key="idx" class="p-3 bg-white border rounded-lg flex justify-between items-center shadow-sm">
                                <span class="font-medium text-gray-800">{{ pg.name }}</span>
                                <button @click="removeProcessGroup(idx)" class="text-red-400 hover:text-red-600"><i class="fas fa-times"></i></button>
                            </div>
                        </div>
                         <div v-else class="text-center text-gray-400 py-4 bg-white rounded-lg border border-dashed">
                             Процеси не обрано
                        </div>
                    </div>
                </div>

            </div>

            <div class="p-5 border-t bg-gray-50 flex justify-end gap-3">
                <button @click="$emit('close')" class="px-6 py-2.5 border border-gray-300 rounded-lg text-gray-700 hover:bg-white transition font-medium">
                    Скасувати
                </button>
                <button @click="handleSave" class="px-6 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 shadow-lg transition font-medium flex items-center gap-2" :disabled="newProduct.variants.length === 0">
                    <i class="fas fa-check"></i> {{ isEdit ? 'Зберегти товар' : 'Створити товар' }}
                </button>
            </div>

            <div v-if="showVariantForm" class="absolute inset-0 bg-white z-50 flex flex-col animate-slide-up">
                <div class="p-4 border-b bg-purple-50 flex justify-between items-center shadow-sm">
                     <h4 class="font-bold text-purple-900 flex items-center gap-2">
                        <span class="bg-purple-200 text-purple-800 w-6 h-6 rounded flex items-center justify-center text-xs font-bold">{{ editingVariantIndex !== null ? editingVariantIndex + 1 : '+' }}</span>
                        {{ editingVariantIndex !== null ? 'Редагування варіанту' : 'Новий варіант' }}
                    </h4>
                    <button @click="closeVariantForm" class="text-gray-500 hover:text-gray-700 bg-white px-3 py-1 rounded border shadow-sm text-sm font-medium">
                         <i class="fas fa-chevron-down mr-1"></i> Згорнути
                    </button>
                </div>
                
                <div class="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
                    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="md:col-span-2">
                            <label class="block text-sm font-bold text-gray-700 mb-1">Назва варіанту <span class="text-red-500">*</span></label>
                            <input v-model="variantBuilder.name" type="text" class="w-full border rounded-lg p-2" placeholder="Напр: Велика (40см)">
                        </div>
                         <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">Артикул (SKU)</label>
                            <input v-model="variantBuilder.sku" type="text" class="w-full border rounded-lg p-2">
                        </div>
                        <div class="md:col-span-3">
                             <label class="block text-sm font-bold text-purple-800 mb-1">Ціна (₴) <span class="text-red-500">*</span></label>
                            <input v-model.number="variantBuilder.price" type="number" class="w-full border-2 border-purple-200 rounded-lg p-2 font-bold text-lg focus:ring-2 focus:ring-purple-500">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                             <h5 class="font-bold mb-3 text-yellow-800 flex items-center gap-2"><i class="fas fa-lemon"></i> Унікальні інгредієнти</h5>
                            <div class="flex gap-2 mb-2">
                                <IngredientSelect v-model="tempVariantIngredient.ingredient_id" :ingredients="ingredients" class="flex-1" />
                                <input v-model.number="tempVariantIngredient.quantity" type="number" class="w-20 border rounded p-1.5 text-sm" placeholder="К-сть">
                                <button @click="addIngredientToVariant" class="bg-yellow-500 text-white px-3 rounded"><i class="fas fa-plus"></i></button>
                            </div>
                            <div class="space-y-1">
                                 <div v-for="(ing, idx) in variantBuilder.ingredients" :key="idx" class="p-2 bg-gray-50 rounded text-sm flex justify-between items-center border">
                                    <span class="font-medium">{{ ing.name || '???' }}</span>
                                    <span><span class="font-mono bg-white px-1 rounded border">{{ ing.quantity }}</span> <i @click="removeIngredientFromVariant(idx)" class="fas fa-times text-red-500 cursor-pointer ml-2 hover:text-red-700"></i></span>
                                </div>
                            </div>
                        </div>
                        <div class="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                             <h5 class="font-bold mb-3 text-blue-800 flex items-center gap-2"><i class="fas fa-box-open"></i> Унікальні матеріали</h5>
                             <div class="flex gap-2 mb-2">
                                <select v-model="tempVariantConsumable.consumable_id" class="flex-1 border rounded p-1.5 text-sm bg-white">
                                    <option value="">Оберіть...</option>
                                    <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                </select>
                                <input v-model.number="tempVariantConsumable.quantity" type="number" class="w-16 border rounded p-1.5 text-sm" placeholder="Шт">
                                <button @click="addVariantConsumable" class="bg-blue-500 text-white px-3 rounded"><i class="fas fa-plus"></i></button>
                            </div>
                             <div class="space-y-1">
                                 <div v-for="(c, idx) in variantBuilder.consumables" :key="idx" class="p-2 bg-gray-50 rounded text-sm flex justify-between items-center border">
                                    <span class="font-medium">{{ c.name || '???' }}</span>
                                    <span><span class="font-mono bg-white px-1 rounded border">{{ c.quantity }}</span> <i @click="removeVariantConsumable(idx)" class="fas fa-times text-red-500 cursor-pointer ml-2 hover:text-red-700"></i></span>
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
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
.animate-slide-up { animation: slideUp 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>