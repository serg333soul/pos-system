<script setup>
import { ref, onMounted, computed } from 'vue' // <--- Додав computed
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'

// Отримуємо довідники (категорії, рецепти тощо)
const { categories, recipes, ingredients, consumables } = useWarehouse()

// Отримуємо функціонал товарів
const { 
    newProduct, isEditing, 
    variantBuilder, tempProductConsumable, tempVariantConsumable, tempVariantIngredient,
    resetForm, prepareEdit, saveProduct, deleteProduct, fetchProducts, filteredProducts, productSearch,
    
    saveVariant, editVariant, cancelVariantEdit, editingVariantIndex, removeVariant, 
    
    addProductConsumable, removeProductConsumable,
    addVariantConsumable, removeVariantConsumable,
    addIngredientToVariant, removeIngredientFromVariant
} = useProducts()

const showForm = ref(false)

const getCategoryName = (id) => {
    if (!categories.value) return '-'
    const c = categories.value.find(x => x.id === id)
    return c ? c.name : '-'
}

// --- НОВА ЛОГІКА ДЛЯ ОДИНИЦЬ ВИМІРУ ---
const getIngredientUnit = (id) => {
    if (!id || !ingredients.value) return ''
    const ing = ingredients.value.find(i => i.id === id)
    return ing?.unit?.symbol || ''
}

const currentIngredientPlaceholder = computed(() => {
    const unit = getIngredientUnit(tempVariantIngredient.value.ingredient_id)
    return unit ? `К-сть (${unit})` : 'К-сть'
})
// --------------------------------------

const handleSave = async () => {
    const success = await saveProduct()
    if(success) {
        showForm.value = false
        await fetchProducts()
    }
}

const handleEdit = (product) => {
    prepareEdit(product)
    showForm.value = true
}

onMounted(async () => {
    console.log("ProductsTab mounted: fetching data...")
    await fetchProducts()
})
</script>

<template>
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        <div v-if="showForm" class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit xl:col-span-1">
            <div class="flex justify-between items-center mb-6">
                <h3 class="font-bold text-gray-700">
                    {{ isEditing ? '✏️ Редагування' : '📦 Новий товар' }}
                </h3>
                <button @click="showForm = false; resetForm()" class="text-xs text-red-500 hover:underline">Закрити</button>
            </div>

            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва</label>
                    <input v-model="newProduct.name" class="border p-2 rounded w-full focus:ring-2 ring-blue-100 outline-none">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Категорія</label>
                        <select v-model="newProduct.category_id" class="border p-2 rounded w-full bg-white">
                            <option :value="null">-- Без категорії --</option>
                            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ціна (базова)</label>
                        <input v-model.number="newProduct.price" type="number" class="border p-2 rounded w-full">
                    </div>
                </div>

                <div class="flex items-center gap-2 py-2">
                    <input type="checkbox" v-model="newProduct.has_variants" id="hasVar" class="w-4 h-4 text-blue-600">
                    <label for="hasVar" class="text-sm font-bold text-gray-700 select-none">Цей товар має варіанти</label>
                </div>

                <div v-if="!newProduct.has_variants" class="bg-gray-50 p-3 rounded border border-gray-200 space-y-3">
                     <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Майстер-рецепт</label>
                        <select v-model="newProduct.master_recipe_id" class="border p-2 rounded w-full bg-white text-sm">
                            <option :value="null">-- Без рецепту --</option>
                            <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Вихідна вага (г/мл)</label>
                        <input v-model.number="newProduct.output_weight" type="number" class="border p-2 rounded w-full text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Початковий залишок</label>
                        <input v-model.number="newProduct.stock_quantity" type="number" class="border p-2 rounded w-full text-sm" placeholder="0">
                    </div>
                </div>

                <div class="bg-teal-50/50 p-3 rounded border border-teal-100">
                    <label class="text-[10px] uppercase font-bold text-teal-600 mb-2 block">Загальні матеріали</label>
                    <div class="flex gap-2 mb-2">
                        <select v-model="tempProductConsumable.consumable_id" class="flex-1 border p-1 rounded text-sm bg-white">
                            <option value="">Матеріал...</option>
                            <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                        </select>
                        <button @click="addProductConsumable" class="bg-teal-500 text-white w-8 rounded hover:bg-teal-600">+</button>
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <span v-for="(pc, idx) in newProduct.consumables" :key="idx" class="bg-white border border-teal-200 text-teal-700 text-xs px-2 py-1 rounded flex items-center gap-1">
                            {{ pc.name }} <button @click="removeProductConsumable(idx)" class="text-red-500 font-bold ml-1">&times;</button>
                        </span>
                    </div>
                </div>

                <div v-if="newProduct.has_variants" class="space-y-3">
                    <div class="border-t pt-2 mt-2">
                        <div class="flex justify-between items-center mb-2">
                             <h4 class="font-bold text-sm text-purple-700">
                                 {{ editingVariantIndex !== null ? '✏️ Редагування варіанту' : 'Конструктор варіантів' }}
                             </h4>
                             <button v-if="editingVariantIndex !== null" @click="cancelVariantEdit" class="text-xs text-gray-500 underline">Скасувати</button>
                        </div>
                        
                        <div class="bg-purple-50 p-3 rounded-lg border border-purple-100 space-y-3" :class="{'ring-2 ring-purple-300': editingVariantIndex !== null}">
                            
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="text-[10px] uppercase font-bold text-gray-500">Назва</label>
                                    <input v-model="variantBuilder.name" placeholder="напр. XL" class="w-full border p-1.5 rounded text-sm">
                                </div>
                                <div>
                                    <label class="text-[10px] uppercase font-bold text-gray-500">Ціна</label>
                                    <input v-model.number="variantBuilder.price" type="number" class="w-full border p-1.5 rounded text-sm">
                                </div>
                            </div>
                            
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="text-[10px] uppercase font-bold text-gray-500">Тех. карта</label>
                                    <select v-model="variantBuilder.master_recipe_id" class="w-full border p-1.5 rounded text-sm bg-white">
                                        <option :value="null">-- Без рецепту --</option>
                                        <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="text-[10px] uppercase font-bold text-gray-500">Вага готового (г/мл)</label>
                                    <input v-model.number="variantBuilder.output_weight" type="number" class="w-full border p-1.5 rounded text-sm">
                                </div>
                            </div>
                            
                            <div>
                                <label class="text-[10px] uppercase font-bold text-gray-500">Початковий залишок (шт)</label>
                                <input v-model.number="variantBuilder.stock_quantity" type="number" class="w-full border p-1.5 rounded text-sm bg-white" placeholder="0">
                            </div>

                            <div class="bg-white/50 p-2 rounded border border-dashed border-purple-200">
                                <label class="text-[10px] uppercase font-bold text-purple-400">Матеріали варіанту</label>
                                <div class="flex gap-1 mb-1">
                                    <select v-model="tempVariantConsumable.consumable_id" class="flex-1 border p-1 rounded text-[10px] bg-white h-7">
                                        <option value="">Матеріал...</option>
                                        <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                    </select>
                                    <input v-model.number="tempVariantConsumable.quantity" type="number" class="w-10 border p-1 rounded text-[10px] h-7" placeholder="К-сть">
                                    <button @click="addVariantConsumable" class="bg-purple-500 text-white w-7 h-7 rounded hover:bg-purple-600 text-xs">+</button>
                                </div>
                                <div class="flex flex-wrap gap-1">
                                    <span v-for="(vc, idx) in variantBuilder.consumables" :key="idx" class="bg-white border text-[10px] px-1 rounded flex items-center gap-1">
                                        {{ vc.name }}: {{ vc.quantity }} <button @click="removeVariantConsumable(idx)" class="text-red-500 font-bold">&times;</button>
                                    </span>
                                </div>
                            </div>

                            <div class="bg-blue-50/50 p-2 rounded border border-dashed border-blue-200">
                                <label class="text-[10px] uppercase font-bold text-blue-500">Додаткові інгредієнти</label>
                                <div class="flex gap-1 mb-1">
                                    <select v-model="tempVariantIngredient.ingredient_id" class="flex-1 border p-1 rounded text-[10px] bg-white h-7">
                                        <option value="">Інгредієнт...</option>
                                        <option v-for="i in ingredients" :key="i.id" :value="i.id">
                                            {{ i.name }} ({{ i.unit?.symbol }})
                                        </option>
                                    </select>
                                    <input 
                                        v-model.number="tempVariantIngredient.quantity" 
                                        type="number" 
                                        class="w-16 border p-1 rounded text-[10px] h-7" 
                                        :placeholder="currentIngredientPlaceholder"
                                    >
                                    <button @click="addIngredientToVariant" class="bg-blue-500 text-white w-7 h-7 rounded hover:bg-blue-600 text-xs">+</button>
                                </div>
                                <div class="flex flex-wrap gap-1">
                                    <span v-for="(vi, idx) in variantBuilder.ingredients" :key="idx" class="bg-white border text-[10px] px-1 rounded flex items-center gap-1 text-blue-700">
                                        {{ vi.name }}: {{ vi.quantity }} {{ getIngredientUnit(vi.ingredient_id) }}
                                        <button @click="removeIngredientFromVariant(idx)" class="text-red-500 font-bold">&times;</button>
                                    </span>
                                </div>
                            </div>

                            <button @click="saveVariant" class="w-full text-xs font-bold py-2 rounded transition-colors"
                                :class="editingVariantIndex !== null ? 'bg-orange-400 text-white hover:bg-orange-500' : 'bg-purple-200 text-purple-800 hover:bg-purple-300'">
                                {{ editingVariantIndex !== null ? 'Зберегти зміни варіанту' : 'Додати цей варіант у список' }}
                            </button>
                        </div>
                    </div>
                    
                    <div v-if="newProduct.variants.length > 0" class="space-y-2">
                        <div v-for="(v, idx) in newProduct.variants" :key="idx" 
                             class="bg-white border p-2 rounded flex justify-between items-center text-sm"
                             :class="{'border-purple-400 bg-purple-50': editingVariantIndex === idx}"
                        >
                            <div>
                                <span class="font-bold">{{ v.name }}</span> - {{ v.price }} грн
                                <div class="text-xs text-gray-400">
                                    <span v-if="v.master_recipe_id" class="text-purple-600 mr-2">📜 Рецепт ID: {{ v.master_recipe_id }}</span>
                                    <span v-if="v.stock_quantity > 0" class="text-green-600 font-bold">Залишок: {{ v.stock_quantity }}</span>
                                    <span v-if="v.ingredients?.length" class="text-blue-500 ml-2">Інгр: {{ v.ingredients.length }}</span>
                                </div>
                            </div>
                            <div class="flex gap-2">
                                <button @click="editVariant(idx)" class="text-blue-500 hover:text-blue-700"><i class="fas fa-pen"></i></button>
                                <button @click="removeVariant(idx)" class="text-red-500 hover:text-red-700"><i class="fas fa-trash"></i></button>
                            </div>
                        </div>
                    </div>
                </div>

                <button @click="handleSave" class="w-full bg-green-600 text-white font-bold py-3 rounded-xl hover:bg-green-700 mt-4 shadow-lg shadow-green-100">
                    {{ isEditing ? 'Зберегти зміни' : 'Створити товар' }}
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col h-full" :class="showForm ? 'xl:col-span-2' : 'xl:col-span-3'">
            
            <div class="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <div class="flex items-center gap-4">
                    <h2 class="font-bold text-gray-700">Список товарів</h2>
                    <input v-model="productSearch" placeholder="Пошук..." class="border rounded px-2 py-1 text-sm bg-white">
                </div>
                <button v-if="!showForm" @click="showForm = true; resetForm()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold text-sm shadow-md shadow-blue-100">
                    + Новий товар
                </button>
            </div>

            <div class="overflow-auto flex-1">
                <table class="w-full text-left text-sm">
                    <thead class="bg-gray-50 text-gray-500 uppercase text-xs sticky top-0">
                        <tr>
                            <th class="p-4">Назва</th>
                            <th class="p-4">Категорія</th>
                            <th class="p-4">Ціна / Варіанти</th>
                            <th class="p-4 text-center">Дії</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-if="filteredProducts.length === 0">
                            <td colspan="4" class="p-8 text-center text-gray-400">
                                Товарів немає або завантаження...
                            </td>
                        </tr>
                        <tr v-for="p in filteredProducts" :key="p.id" class="hover:bg-gray-50 align-top group">
                            <td class="p-4 font-bold text-gray-800">{{ p.name }}</td>
                            <td class="p-4 text-gray-600">
                                <span class="bg-gray-100 px-2 py-1 rounded text-xs">{{ getCategoryName(p.category_id) }}</span>
                            </td>
                            <td class="p-4">
                                <div v-if="!p.has_variants" class="font-mono font-bold text-green-600">
                                    {{ p.price }} ₴
                                </div>
                                
                                <div v-else class="space-y-2">
                                    <div v-for="v in p.variants" :key="v.id" class="text-xs bg-gray-50 p-2 rounded border border-gray-200">
                                        <div class="flex justify-between font-bold mb-1">
                                            <span>{{ v.name }}</span>
                                            <span>{{ v.price }} ₴</span>
                                        </div>

                                        <div class="text-gray-500 flex flex-col gap-1">
                                            
                                            <div v-if="v.ingredients?.length" class="text-blue-600">
                                                <div class="flex items-start gap-1">
                                                    <i class="fas fa-flask mt-0.5"></i> 
                                                    <div class="flex flex-wrap gap-1">
                                                        <span v-for="vi in v.ingredients" :key="vi.id" class="bg-blue-50 border border-blue-100 px-1 rounded flex items-center gap-1">
                                                            {{ vi.ingredient_name || '?' }}: {{ vi.quantity }} {{ getIngredientUnit(vi.ingredient_id) }}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div v-if="v.consumables?.length" class="text-teal-600">
                                                <div class="flex items-start gap-1">
                                                    <i class="fas fa-box-open mt-0.5"></i> 
                                                    <div class="flex flex-wrap gap-1">
                                                        <span v-for="vc in v.consumables" :key="vc.id" class="bg-teal-50 border border-teal-100 px-1 rounded">
                                                            {{ vc.consumable_name || '?' }}: {{ vc.quantity }}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                        </div>
                                    </div>
                                </div>
                            </td>
                            <td class="p-4 text-center">
                                <div class="flex justify-center gap-2">
                                    <button @click="handleEdit(p)" class="text-blue-500 hover:text-blue-700 p-1.5 hover:bg-blue-50 rounded"><i class="fas fa-pen"></i></button>
                                    <button @click="deleteProduct(p.id)" class="text-red-400 hover:text-red-600 p-1.5 hover:bg-red-50 rounded"><i class="fas fa-trash"></i></button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>