<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'

// --- ДОВІДНИКИ ---
const { categories, recipes, ingredients, consumables } = useWarehouse()

// --- ФУНКЦІОНАЛ ТОВАРІВ ---
const { 
    newProduct, isEditing, 
    prepareEdit: originalHandleEdit, 
    saveProduct, deleteProduct, fetchProducts, filteredProducts, productSearch, resetForm,
    removeProductConsumable
} = useProducts()

// --- UI STATES ---
const showTypeModal = ref(false)
const showForm = ref(false)
const productType = ref(null)

// --- КАЛЬКУЛЯТОР СОБІВАРТОСТІ (БЕКЕНД - ЗАГАЛЬНА) ---
const serverCalculatedCost = ref(0)
let debounceTimer = null

const calculateCost = async () => {
    const payload = {
        master_recipe_id: newProduct.value.master_recipe_id,
        output_weight: newProduct.value.output_weight || 0,
        ingredients: newProduct.value.ingredients || [],
        consumables: newProduct.value.consumables || []
    }

    try {
        const res = await fetch('/api/products/calculate-cost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        if (res.ok) {
            const data = await res.json()
            serverCalculatedCost.value = data.total_cost
        }
    } catch (e) {
        console.error("Помилка розрахунку:", e)
    }
}

// --- 🔥 ВІЗУАЛІЗАЦІЯ РЕЦЕПТУ З ЦІНАМИ ---
const selectedRecipeBreakdown = computed(() => {
    if (!newProduct.value.master_recipe_id) return { items: [], totalCost: 0 }
    
    const recipe = recipes.value.find(r => r.id === newProduct.value.master_recipe_id)
    if (!recipe || !recipe.items) return { items: [], totalCost: 0 }

    const totalWeight = newProduct.value.output_weight || 0
    let currentRecipeCost = 0

    const items = recipe.items.map(item => {
        // Знаходимо інгредієнт в довіднику, щоб взяти ціну
        const ingData = ingredients.value.find(i => i.id === item.ingredient_id)
        const ingName = ingData?.name || 'Невідомий інгредієнт'
        const unitSymbol = ingData?.unit?.symbol || ''
        const costPerUnit = ingData?.cost_per_unit || 0
        
        let calculatedQty = 0
        let metaInfo = ''

        if (item.is_percentage) {
            calculatedQty = (item.quantity / 100) * totalWeight
            metaInfo = `${item.quantity}%`
        } else {
            calculatedQty = item.quantity
            metaInfo = 'фікс.'
        }
        
        // Рахуємо вартість цієї позиції
        const itemCost = calculatedQty * costPerUnit
        currentRecipeCost += itemCost

        return {
            name: ingName,
            meta: metaInfo,
            qty: calculatedQty.toFixed(1),
            unit: unitSymbol,
            cost: itemCost.toFixed(2) // Ціна за цю кількість
        }
    })

    return {
        items,
        totalCost: currentRecipeCost.toFixed(2)
    }
})

// --- ЛОГІКА РЕДАГУВАННЯ ---
const handleEditWrapper = async (product) => {
    console.log("✏️ Починаємо редагування:", product.name)
    
    if (typeof originalHandleEdit === 'function') {
        originalHandleEdit(product)
    } else {
        console.error("❌ Помилка: prepareEdit не знайдена!")
        return
    }

    productType.value = product.has_variants ? 'variant' : 'simple'

    if (!newProduct.value.ingredients) newProduct.value.ingredients = []
    if (!newProduct.value.consumables) newProduct.value.consumables = []

    showForm.value = true
    await calculateCost()
}

// --- HELPER ДЛЯ ВІДОБРАЖЕННЯ ЦІНИ В СПИСКАХ ---
const getLinkCost = (id, qty, sourceList) => {
    if (!id || !sourceList) return '0.00'
    const list = sourceList.value || sourceList
    if (!Array.isArray(list)) return '0.00'
    const item = list.find(x => x.id === id)
    if (!item) return '0.00'
    return (item.cost_per_unit * qty).toFixed(2)
}

// --- ЛОГІКА ПРОСТИХ ІНГРЕДІЄНТІВ ---
const tempSimpleIngredient = ref({ id: null, qty: 0 })

const addSimpleIngredient = () => {
    if (tempSimpleIngredient.value.id && tempSimpleIngredient.value.qty > 0) {
        if (!newProduct.value.ingredients) newProduct.value.ingredients = []
        
        const existing = newProduct.value.ingredients.find(i => i.ingredient_id === tempSimpleIngredient.value.id)
        if (existing) {
            existing.quantity += tempSimpleIngredient.value.qty
        } else {
            newProduct.value.ingredients.push({
                ingredient_id: tempSimpleIngredient.value.id,
                quantity: tempSimpleIngredient.value.qty
            })
        }
        tempSimpleIngredient.value = { id: null, qty: 0 }
    }
}

const removeSimpleIngredient = (index) => {
    newProduct.value.ingredients.splice(index, 1)
}

// --- ЛОГІКА ВИТРАТНИХ МАТЕРІАЛІВ ---
const tempSimpleConsumable = ref({ id: null, qty: 1 })

const addSimpleConsumable = () => {
    if (tempSimpleConsumable.value.id && tempSimpleConsumable.value.qty > 0) {
        if (!newProduct.value.consumables) newProduct.value.consumables = []
        
        const existing = newProduct.value.consumables.find(c => c.consumable_id === tempSimpleConsumable.value.id)
        if (existing) {
            existing.quantity += tempSimpleConsumable.value.qty
        } else {
            newProduct.value.consumables.push({
                consumable_id: tempSimpleConsumable.value.id,
                quantity: tempSimpleConsumable.value.qty
            })
        }
        tempSimpleConsumable.value = { id: null, qty: 1 }
    }
}

const removeSimpleConsumable = (index) => {
    newProduct.value.consumables.splice(index, 1)
}

// --- СЛІДКУВАННЯ ЗА ЗМІНАМИ ---
watch(
    () => [
        newProduct.value.master_recipe_id, 
        newProduct.value.output_weight, 
        newProduct.value.ingredients, 
        newProduct.value.consumables
    ], 
    () => {
        clearTimeout(debounceTimer)
        debounceTimer = setTimeout(calculateCost, 500)
    },
    { deep: true }
)

// --- УПРАВЛІННЯ ФОРМАМИ ---
const startCreate = () => {
    resetForm()
    productType.value = null
    showTypeModal.value = true
}

const selectType = (type) => {
    productType.value = type
    if (type === 'simple') {
        newProduct.value.has_variants = false
        newProduct.value.ingredients = [] 
        newProduct.value.consumables = []
    } else {
        newProduct.value.has_variants = true
    }
    showTypeModal.value = false
    showForm.value = true
}

const handleSave = async () => {
    await saveProduct()
    showForm.value = false
}

const closeForm = () => {
    showForm.value = false
    resetForm()
}

const getCategoryName = (id) => categories.value.find(c => c.id === id)?.name || '-'

onMounted(() => {
    fetchProducts()
})
</script>

<template>
    <div class="h-full flex flex-col">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-2xl font-bold text-gray-800">📦 Товари</h2>
            <div class="flex gap-4">
                <input v-model="productSearch" placeholder="Пошук..." class="border rounded-lg px-4 py-2 w-64 shadow-sm focus:ring-2 focus:ring-blue-500 outline-none">
                <button @click="startCreate" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 shadow-md transition font-medium flex items-center gap-2">
                    <i class="fas fa-plus"></i> Додати товар
                </button>
            </div>
        </div>

        <div v-if="showTypeModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
            <div class="bg-white p-8 rounded-2xl shadow-2xl w-full max-w-lg text-center animate-fade-in">
                <h3 class="text-2xl font-bold mb-6 text-gray-800">Який товар створюємо?</h3>
                <div class="grid grid-cols-2 gap-6">
                    <button @click="selectType('simple')" class="flex flex-col items-center justify-center p-6 border-2 border-gray-100 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition group">
                        <div class="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition">☕</div>
                        <div class="font-bold text-lg text-gray-800">Простий товар</div>
                        <div class="text-sm text-gray-500 mt-2">Одна ціна, один рецепт</div>
                    </button>

                    <button @click="selectType('variant')" class="flex flex-col items-center justify-center p-6 border-2 border-gray-100 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition group">
                        <div class="w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition">🎨</div>
                        <div class="font-bold text-lg text-gray-800">З варіантами</div>
                        <div class="text-sm text-gray-500 mt-2">Різні об'єми або види</div>
                    </button>
                </div>
                <button @click="showTypeModal = false" class="mt-8 text-gray-400 hover:text-gray-600">Скасувати</button>
            </div>
        </div>

        <div v-if="showForm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div class="bg-white p-8 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto relative">
                
                <div class="flex justify-between items-center mb-6 border-b pb-4">
                    <h3 class="text-2xl font-bold text-gray-800">
                        {{ isEditing ? 'Редагувати' : 'Створити' }} 
                        <span :class="productType === 'simple' ? 'text-blue-600' : 'text-purple-600'">
                            {{ productType === 'simple' ? 'Простий товар' : 'Товар з варіантами' }}
                        </span>
                    </h3>
                    <button @click="closeForm" class="text-gray-400 hover:text-gray-600 text-2xl">×</button>
                </div>

                <div v-if="productType === 'simple'" class="space-y-6">
                    
                    <div class="grid grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Назва товару <span class="text-red-500">*</span></label>
                            <input v-model="newProduct.name" class="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500" placeholder="Напр. Американо">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Категорія <span class="text-red-500">*</span></label>
                            <select v-model="newProduct.category_id" class="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500">
                                <option :value="null">Оберіть категорію</option>
                                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Ціна продажу (грн) <span class="text-red-500">*</span></label>
                            <input v-model.number="newProduct.price" type="number" step="0.01" class="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 font-bold text-lg">
                        </div>
                        <div>
                             <label class="block text-sm font-medium text-gray-700 mb-1">Розрахункова собівартість (Auto)</label>
                             <div class="w-full p-2 bg-gray-50 border rounded text-gray-500 font-mono font-bold flex items-center justify-between">
                                 <span>≈ {{ serverCalculatedCost.toFixed(2) }} грн</span>
                                 <span class="text-xs font-normal text-gray-400">оновлено сервером</span>
                             </div>
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Опис</label>
                        <textarea v-model="newProduct.description" class="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500" rows="2"></textarea>
                    </div>

                    <div class="border-t my-4"></div>

                    <div class="bg-orange-50 p-4 rounded-xl border border-orange-100">
                        <h4 class="font-bold text-orange-800 mb-3 flex items-center gap-2">
                            <i class="fas fa-book-open"></i> Технологічна карта (Рецепт)
                        </h4>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-orange-700 mb-1">Оберіть рецепт</label>
                                <select v-model="newProduct.master_recipe_id" class="w-full border p-2 rounded focus:ring-2 focus:ring-orange-500 bg-white">
                                    <option :value="null">Без рецепту</option>
                                    <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                                </select>
                            </div>

                            <div v-if="newProduct.master_recipe_id">
                                <label class="block text-xs font-bold text-orange-700 mb-1">Вага виходу (грам)</label>
                                <input v-model.number="newProduct.output_weight" type="number" step="0.1" 
                                       placeholder="Напр. 18"
                                       class="w-full border p-2 rounded focus:ring-2 focus:ring-orange-500 bg-white font-bold">
                                <p class="text-[10px] text-orange-600 mt-1">Загальна вага продукту для розрахунку пропорцій</p>
                            </div>
                        </div>

                        <div v-if="newProduct.master_recipe_id && selectedRecipeBreakdown.items.length" class="mt-4 bg-white rounded-lg border border-orange-200 overflow-hidden">
                             <table class="w-full text-sm text-left">
                                 <thead class="bg-orange-100 text-orange-800 text-xs uppercase">
                                     <tr>
                                         <th class="p-2">Інгредієнт</th>
                                         <th class="p-2 text-center">Пропорція</th>
                                         <th class="p-2 text-right">Витрата</th>
                                         <th class="p-2 text-right">Вартість</th>
                                     </tr>
                                 </thead>
                                 <tbody class="divide-y divide-orange-50">
                                     <tr v-for="(item, idx) in selectedRecipeBreakdown.items" :key="idx">
                                         <td class="p-2 font-medium text-gray-700">{{ item.name }}</td>
                                         <td class="p-2 text-center text-gray-500 text-xs">{{ item.meta }}</td>
                                         <td class="p-2 text-right font-bold text-orange-700">
                                             {{ item.qty }} {{ item.unit }}
                                         </td>
                                         <td class="p-2 text-right text-xs font-mono text-gray-500">
                                             {{ item.cost }} грн
                                         </td>
                                     </tr>
                                     <tr class="bg-orange-50 font-bold border-t border-orange-200">
                                         <td colspan="3" class="p-2 text-right text-orange-800">Разом по рецепту:</td>
                                         <td class="p-2 text-right text-orange-800">{{ selectedRecipeBreakdown.totalCost }} грн</td>
                                     </tr>
                                 </tbody>
                             </table>
                        </div>
                    </div>

                    <div class="bg-green-50 p-4 rounded-xl border border-green-100">
                        <h4 class="font-bold text-green-800 mb-3 flex items-center gap-2">
                            <i class="fas fa-carrot"></i> Додаткові інгредієнти
                        </h4>
                        <div class="flex gap-2 mb-2">
                             <select v-model="tempSimpleIngredient.id" class="flex-1 border p-2 rounded text-sm bg-white">
                                <option :value="null">Додати інгредієнт...</option>
                                <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">
                                    {{ ing.name }} ({{ ing.cost_per_unit }} грн/{{ ing.unit?.symbol }})
                                </option>
                            </select>
                            <input v-model.number="tempSimpleIngredient.qty" type="number" placeholder="К-сть" class="w-24 border p-2 rounded text-sm">
                            <button @click="addSimpleIngredient" class="bg-green-600 text-white px-3 rounded hover:bg-green-700 font-bold">+</button>
                        </div>
                        
                        <div v-if="newProduct.ingredients && newProduct.ingredients.length" class="space-y-1 mt-2">
                             <div v-for="(link, idx) in newProduct.ingredients" :key="idx" class="flex justify-between items-center bg-white p-2 rounded border border-green-200 text-sm">
                                 <span>
                                     {{ ingredients.find(i => i.id === link.ingredient_id)?.name }} — 
                                     <b>{{ link.quantity }} {{ ingredients.find(i => i.id === link.ingredient_id)?.unit?.symbol }}</b>
                                     <span class="text-xs text-green-600 font-bold ml-2">
                                        ({{ getLinkCost(link.ingredient_id, link.quantity, ingredients) }} грн)
                                     </span>
                                 </span>
                                 <button @click="removeSimpleIngredient(idx)" class="text-red-500 hover:text-red-700">×</button>
                             </div>
                        </div>
                    </div>

                    <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
                         <h4 class="font-bold text-blue-800 mb-3 flex items-center gap-2">
                            <i class="fas fa-box-open"></i> Витратні матеріали
                        </h4>
                         <div class="flex gap-2 mb-2">
                             <select v-model="tempSimpleConsumable.id" class="flex-1 border p-2 rounded text-sm bg-white">
                                <option :value="null">Додати матеріал...</option>
                                <option v-for="c in consumables" :key="c.id" :value="c.id">
                                    {{ c.name }} ({{ c.cost_per_unit }} грн)
                                </option>
                            </select>
                            <input v-model.number="tempSimpleConsumable.qty" type="number" placeholder="К-сть" class="w-24 border p-2 rounded text-sm">
                            <button @click="addSimpleConsumable" class="bg-blue-600 text-white px-3 rounded hover:bg-blue-700 font-bold">+</button>
                        </div>

                        <div v-if="newProduct.consumables && newProduct.consumables.length" class="space-y-1 mt-2">
                             <div v-for="(link, idx) in newProduct.consumables" :key="idx" class="flex justify-between items-center bg-white p-2 rounded border border-blue-200 text-sm">
                                 <span>
                                     {{ consumables.find(c => c.id === link.consumable_id)?.name }} — 
                                     <b>{{ link.quantity }} шт.</b>
                                     <span class="text-xs text-blue-600 font-bold ml-2">
                                        ({{ getLinkCost(link.consumable_id, link.quantity, consumables) }} грн)
                                     </span>
                                 </span>
                                 <button @click="removeSimpleConsumable(idx)" class="text-red-500 hover:text-red-700">×</button>
                             </div>
                        </div>
                    </div>

                    <div class="flex items-center gap-2 mt-4 pt-4 border-t">
                        <input type="checkbox" v-model="newProduct.track_stock" id="trackStock" class="w-5 h-5 text-blue-600 rounded">
                        <label for="trackStock" class="text-gray-700 font-medium">Вести облік залишків цього товару</label>
                    </div>
                    <div v-if="newProduct.track_stock" class="ml-7 mt-2">
                         <label class="text-sm text-gray-600">Початковий залишок:</label>
                         <input v-model.number="newProduct.stock_quantity" type="number" class="border p-1 rounded w-32 ml-2">
                    </div>
                </div>

                <div v-else-if="productType === 'variant'">
                    <div class="p-10 text-center text-gray-500 bg-gray-50 rounded-xl border-2 border-dashed">
                        <h3 class="text-xl font-bold mb-2">🚧 Форма для варіантів</h3>
                        <p>Натисніть "Зберегти" на простому товарі, щоб протестувати. Варіанти додамо наступним кроком.</p>
                        <button @click="productType = 'simple'" class="mt-4 text-blue-500 underline">Повернутись до простого</button>
                    </div>
                </div>

                <div class="flex justify-end gap-3 mt-8 pt-4 border-t">
                    <button @click="closeForm" class="px-6 py-2 rounded-lg border hover:bg-gray-50 text-gray-700">Скасувати</button>
                    <button @click="handleSave" class="px-6 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 shadow-lg font-bold">
                        {{ isEditing ? 'Зберегти зміни' : 'Створити товар' }}
                    </button>
                </div>

            </div>
        </div>

        <div class="flex-1 bg-white rounded-xl shadow overflow-hidden flex flex-col">
             <div class="overflow-y-auto flex-1">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-gray-100 sticky top-0 z-10 text-xs uppercase text-gray-500 font-bold">
                        <tr>
                            <th class="p-4 border-b">Назва</th>
                            <th class="p-4 border-b">Категорія</th>
                            <th class="p-4 border-b">Ціна</th>
                            <th class="p-4 border-b">Склад</th>
                            <th class="p-4 border-b text-center">Дії</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="p in filteredProducts" :key="p.id" class="hover:bg-blue-50 transition group">
                            <td class="p-4">
                                <div class="font-bold text-gray-800 text-lg">{{ p.name }}</div>
                                <div class="text-xs text-gray-400 mt-1">{{ p.description }}</div>
                                <div v-if="p.has_variants" class="mt-1">
                                    <span class="bg-purple-100 text-purple-700 text-[10px] px-2 py-0.5 rounded-full font-bold">Варіанти: {{ p.variants.length }}</span>
                                </div>
                                <div v-if="!p.has_variants && p.ingredients?.length" class="mt-1 flex flex-wrap gap-1">
                                    <span v-for="ing in p.ingredients" :key="ing.ingredient_id" class="bg-green-50 text-green-700 text-[10px] px-1 rounded border border-green-100">
                                        {{ ing.ingredient_name }}: {{ ing.quantity }}
                                    </span>
                                </div>
                            </td>
                            <td class="p-4">
                                <span class="px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-600 border">
                                    {{ getCategoryName(p.category_id) }}
                                </span>
                            </td>
                            <td class="p-4">
                                <div v-if="!p.has_variants" class="font-mono font-bold text-green-700">{{ p.price }} ₴</div>
                                <div v-else class="text-xs text-gray-500 italic">Див. варіанти</div>
                            </td>
                            <td class="p-4">
                                <div v-if="!p.has_variants">
                                    <div v-if="p.track_stock" class="font-mono font-bold" :class="p.stock_quantity > 0 ? 'text-blue-600' : 'text-red-500'">
                                        {{ p.stock_quantity }} шт
                                    </div>
                                    <div v-else class="text-gray-400 text-xs">Не обліковується</div>
                                </div>
                            </td>
                            <td class="p-4 text-center">
                                <div class="flex justify-center gap-2 opacity-0 group-hover:opacity-100 transition">
                                    <button @click="handleEditWrapper(p)" class="text-blue-500 hover:bg-blue-100 p-2 rounded"><i class="fas fa-pen"></i></button>
                                    <button @click="deleteProduct(p.id)" class="text-red-500 hover:bg-red-100 p-2 rounded"><i class="fas fa-trash"></i></button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
             </div>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
</style>