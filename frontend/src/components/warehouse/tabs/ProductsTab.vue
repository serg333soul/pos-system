<script setup>
import { ref, onMounted, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'

// Отримуємо довідники
const { categories, recipes, ingredients, consumables } = useWarehouse()

// Отримуємо функціонал товарів
const { 
    newProduct, isEditing, 
    variantBuilder, tempProductConsumable, tempVariantConsumable, tempVariantIngredient,
    resetForm, prepareEdit, saveProduct, deleteProduct, fetchProducts, filteredProducts, productSearch,
    
    // Імпортуємо методи варіантів
    saveVariant, editVariant, cancelVariantEdit, editingVariantIndex, removeVariant, 
    
    addProductConsumable, removeProductConsumable,
    addVariantConsumable, removeVariantConsumable,
    addIngredientToVariant, removeIngredientFromVariant
} = useProducts()

const showForm = ref(false)
const processGroups = ref([]) 

// 👇 Функція завантаження груп процесів
const fetchProcessGroups = async () => {
    try {
        const response = await fetch('/api/processes/groups/')
        if (response.ok) {
            processGroups.value = await response.json()
        }
    } catch (e) {
        console.error("Помилка завантаження процесів:", e)
    }
}

const getCategoryName = (id) => {
    if (!categories.value) return '-'
    const c = categories.value.find(x => x.id === id)
    return c ? c.name : '-'
}

const getIngredientUnit = (id) => {
    if (!id || !ingredients.value) return ''
    const ing = ingredients.value.find(i => i.id === id)
    return ing?.unit?.symbol || ''
}

const currentIngredientPlaceholder = computed(() => {
    const unit = getIngredientUnit(tempVariantIngredient.value.ingredient_id)
    return unit ? `Кількість (${unit})` : 'Кількість'
})

// === 🔥 ТУТ БУЛА МАТЕМАТИКА (ВИДАЛЕНО) ===
// Тепер ми довіряємо бекенду. Frontend просто відображає дані.

onMounted(() => {
    fetchProducts()
    fetchProcessGroups()
})

// 👇 ЖОРСТКА ВАЛІДАЦІЯ ВАРІАНТУ ПЕРЕД ЗБЕРЕЖЕННЯМ
const handleVariantSave = async () => {
    if (!variantBuilder.value.name) {
        alert("⚠️ Помилка: Вкажіть назву варіанту!")
        return
    }
    if (!variantBuilder.value.price || variantBuilder.value.price <= 0) {
        alert("⚠️ Помилка: Вкажіть ціну продажу!")
        return
    }
    if (!variantBuilder.value.sku) {
        alert("⛔️ СТОП: Поле SKU (Артикул) обов'язкове!\n\nЯкщо вам ліньки вигадувати код, натисніть на кнопку 'Чарівна паличка' 🪄 біля поля.")
        return
    }
    await saveVariant()
}

// Обгортка для збереження головного товару
const handleSave = async () => {
    if (!newProduct.value.process_group_ids) {
        newProduct.value.process_group_ids = []
    }
    if (newProduct.value.has_variants && newProduct.value.variants.length === 0) {
        alert("⚠️ Ви увімкнули режим варіантів, але не додали жодного варіанту.")
        return
    }

    const success = await saveProduct()
    if (success) {
        showForm.value = false
    }
}

const handleEdit = (product) => {
    prepareEdit(product)
    
    if (product.process_groups) {
        newProduct.value.process_group_ids = product.process_groups.map(pg => pg.id)
    } else {
        newProduct.value.process_group_ids = []
    }
    
    showForm.value = true
}

const handleCancel = () => {
    resetForm()
    showForm.value = false
}
</script>

<template>
    <div class="h-full flex flex-col">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-2xl font-bold text-gray-800">📦 Товари та Меню</h2>
            <button @click="showForm = true; resetForm()" v-if="!showForm" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-xl font-bold shadow-lg shadow-purple-200 transition flex items-center gap-2">
                <i class="fas fa-plus"></i> Додати товар
            </button>
        </div>

        <div v-if="showForm" class="bg-white p-6 rounded-2xl shadow-lg border border-purple-100 mb-8 animate-fade-in-down">
            <div class="flex justify-between items-center mb-6 border-b pb-4">
                <h3 class="font-bold text-xl text-gray-700">
                    {{ isEditing ? '✏️ Редагування товару' : '✨ Новий товар' }}
                </h3>
                <button @click="handleCancel" class="text-gray-400 hover:text-gray-600"><i class="fas fa-times text-xl"></i></button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="space-y-6">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва товару</label>
                        <input v-model="newProduct.name" class="w-full border p-3 rounded-lg focus:ring-2 focus:ring-purple-200 outline-none" placeholder="Напр. Ефіопія (Фільтр)">
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ціна (₴)</label>
                            <input type="number" v-model="newProduct.price" class="w-full border p-3 rounded-lg focus:ring-2 focus:ring-purple-200 outline-none">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Категорія</label>
                            <select v-model="newProduct.category_id" class="w-full border p-3 rounded-lg bg-white h-[50px]">
                                <option :value="null">Без категорії</option>
                                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Опис</label>
                        <textarea v-model="newProduct.description" rows="3" class="w-full border p-3 rounded-lg focus:ring-2 focus:ring-purple-200 outline-none"></textarea>
                    </div>

                    <div class="bg-orange-50 p-4 rounded-xl border border-orange-100">
                        <label class="block text-xs font-bold text-orange-600 uppercase mb-2">📜 Базовий рецепт (Техкарта)</label>
                        <select v-model="newProduct.master_recipe_id" class="w-full border p-2 rounded-lg bg-white mb-2">
                            <option :value="null">-- Без рецепту --</option>
                            <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                        </select>
                        <div class="flex items-center gap-2">
                            <input type="checkbox" v-model="newProduct.track_stock" class="w-4 h-4 text-orange-600">
                            <span class="text-sm text-gray-700">Вести складський облік цього товару</span>
                        </div>
                    </div>
                </div>

                <div class="space-y-6">
                    
                    <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                        <label class="block text-xs font-bold text-indigo-600 uppercase mb-2">
                            <i class="fas fa-cogs mr-1"></i> Додаткові процеси (опції для бариста)
                        </label>
                        <div v-if="processGroups.length === 0" class="text-sm text-gray-400 italic">
                            Процеси не створені. Перейдіть на вкладку "Процеси".
                        </div>
                        <div v-else class="grid grid-cols-2 gap-2">
                            <div v-for="pg in processGroups" :key="pg.id" class="flex items-center gap-2 bg-white p-2 rounded border border-indigo-100">
                                <input 
                                    type="checkbox" 
                                    :value="pg.id" 
                                    v-model="newProduct.process_group_ids"
                                    class="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                                >
                                <span class="text-sm text-gray-700">{{ pg.name }}</span>
                            </div>
                        </div>
                    </div>

                    <div class="bg-teal-50 p-4 rounded-xl border border-teal-100">
                        <label class="block text-xs font-bold text-teal-600 uppercase mb-2">🥡 Витратні матеріали (на 1 порцію)</label>
                        <div class="flex gap-2 mb-2">
                            <select v-model="tempProductConsumable.consumable_id" class="flex-1 border p-2 rounded-lg text-sm bg-white">
                                <option :value="null">Оберіть матеріал...</option>
                                <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                            </select>
                            <input v-model="tempProductConsumable.quantity" type="number" placeholder="Кіл-ть" class="w-20 border p-2 rounded-lg text-sm bg-white">
                            <button @click="addProductConsumable" class="bg-teal-600 text-white px-3 rounded-lg"><i class="fas fa-plus"></i></button>
                        </div>
                        
                        <div class="space-y-1">
                            <div v-for="(pc, idx) in newProduct.consumables" :key="idx" class="flex justify-between items-center bg-white p-2 rounded border border-teal-100 text-sm">
                                <span>{{ consumables.find(c => c.id === pc.consumable_id)?.name }} — {{ pc.quantity }} шт</span>
                                <button @click="removeProductConsumable(idx)" class="text-red-400 hover:text-red-600"><i class="fas fa-times"></i></button>
                            </div>
                        </div>
                    </div>

                    <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
                        <div class="flex justify-between items-center mb-2">
                            <label class="block text-xs font-bold text-gray-600 uppercase">🧬 Варіанти (Об'єм / Вид)</label>
                            <div class="flex items-center gap-2">
                                <input type="checkbox" v-model="newProduct.has_variants" class="w-4 h-4 text-purple-600">
                                <span class="text-xs text-gray-500">Є варіанти?</span>
                            </div>
                        </div>

                        <div v-if="newProduct.has_variants" class="space-y-4">
                            <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm" :class="editingVariantIndex !== -1 ? 'ring-2 ring-purple-200' : ''">
                                
                                <div class="grid grid-cols-2 gap-3 mb-3">
                                    <div>
                                        <label class="block text-[10px] font-bold text-gray-500 uppercase mb-1">Назва варіанту</label>
                                        <input v-model="variantBuilder.name" placeholder="напр. Пачка 250г" class="border p-2 rounded text-sm w-full bg-gray-50 focus:bg-white focus:ring-2 focus:ring-purple-100 outline-none">
                                    </div>
                                    <div>
                                        <label class="block text-[10px] font-bold text-gray-500 uppercase mb-1">Ціна продажу (₴)</label>
                                        <input v-model="variantBuilder.price" type="number" placeholder="0.00" class="border p-2 rounded text-sm w-full bg-gray-50 focus:bg-white focus:ring-2 focus:ring-purple-100 outline-none">
                                    </div>
                                </div>
                                
                                <div class="bg-yellow-50 p-3 rounded border border-yellow-100 mb-3">
                                    <div class="grid grid-cols-2 gap-3">
                                        <div>
                                            <label class="block text-[10px] font-bold text-gray-800 uppercase mb-1">
                                                Артикул / SKU <span class="text-red-500">*</span>
                                            </label>
                                            <div class="flex gap-1">
                                                <input 
                                                    v-model="variantBuilder.sku" 
                                                    placeholder="CODE-123" 
                                                    class="border p-2 rounded text-sm w-full bg-white border-yellow-300 focus:ring-2 focus:ring-yellow-200 outline-none"
                                                >
                                                <button 
                                                    @click="variantBuilder.sku = 'SKU-' + Math.floor(10000 + Math.random() * 90000)" 
                                                    class="bg-white px-2 rounded border border-yellow-300 hover:bg-yellow-100 text-yellow-600 transition"
                                                    title="Згенерувати код автоматично 🪄"
                                                >
                                                    <i class="fas fa-magic"></i>
                                                </button>
                                            </div>
                                        </div>
                                        <div>
                                            <label class="block text-[10px] font-bold text-gray-800 uppercase mb-1">⚖️ Вага вмісту (г/мл)</label>
                                            <input v-model.number="variantBuilder.output_weight" type="number" placeholder="напр. 250" class="border p-2 rounded text-sm w-full border-yellow-300 bg-white">
                                            <p class="text-[9px] text-gray-500 mt-0.5 leading-tight">Скільки грам списувати з рецепту</p>
                                        </div>
                                    </div>
                                </div>

                                <div class="mb-3">
                                    <label class="block text-[10px] font-bold text-gray-500 uppercase mb-1">📦 Початковий залишок (шт)</label>
                                    <input v-model.number="variantBuilder.stock_quantity" type="number" class="border p-2 rounded text-sm w-full bg-white" placeholder="0">
                                </div>
                                
                                <div class="mb-3">
                                    <select v-model="variantBuilder.master_recipe_id" class="w-full border p-2 rounded text-sm bg-gray-50">
                                        <option :value="null">-- Майстер-рецепт (для масштабування) --</option>
                                        <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                                    </select>
                                </div>

                                <div v-if="editingVariantIndex === null" class="mb-3 p-2 bg-gray-50 rounded border border-gray-100 text-xs text-center text-gray-400 italic">
                                    <i class="fas fa-calculator mr-1"></i> Собівартість буде розрахована сервером після збереження
                                </div>
                                <div v-else class="mb-3 p-2 bg-purple-50 rounded border border-purple-100 text-xs shadow-sm">
                                     <div class="flex justify-between items-center mb-1">
                                        <span class="text-gray-500">Собівартість:</span>
                                        <span class="font-bold text-gray-700 font-mono">{{ variantBuilder.cost_price }} ₴</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-gray-400">Маржа:</span>
                                        <span class="font-bold font-mono" :class="variantBuilder.margin > 0 ? 'text-green-600' : 'text-red-500'">
                                            {{ variantBuilder.margin }} ₴
                                        </span>
                                    </div>
                                </div>
                                
                                <div class="mb-2 border-t pt-2">
                                    <div class="text-xs font-bold text-orange-400 mb-1 uppercase">Інгредієнти варіанту</div>
                                    <div class="flex gap-1 mb-1">
                                        <select v-model="tempVariantIngredient.ingredient_id" class="flex-1 border p-1 rounded text-xs h-8 bg-white">
                                            <option :value="null">Інгредієнт...</option>
                                            <option v-for="i in ingredients" :key="i.id" :value="i.id">{{ i.name }}</option>
                                        </select>
                                        <input v-model="tempVariantIngredient.quantity" type="number" :placeholder="currentIngredientPlaceholder" class="w-20 border p-1 rounded text-xs h-8">
                                        <button @click="addIngredientToVariant" class="bg-orange-200 px-3 rounded hover:bg-orange-300"><i class="fas fa-plus text-xs"></i></button>
                                    </div>
                                    <div class="flex flex-wrap gap-1">
                                        <span v-for="(vi, idx) in variantBuilder.ingredients" :key="idx" class="text-xs bg-orange-50 text-orange-700 px-2 py-1 rounded border border-orange-100 flex items-center gap-1">
                                            {{ ingredients.find(i => i.id === vi.ingredient_id)?.name }}: {{ vi.quantity }}
                                            <button @click="removeIngredientFromVariant(idx)" class="ml-1 text-red-500 font-bold">×</button>
                                        </span>
                                    </div>
                                </div>

                                <div class="mb-2 border-t pt-2">
                                    <div class="text-xs font-bold text-teal-400 mb-1 uppercase">Матеріали варіанту</div>
                                    <div class="flex gap-1 mb-1">
                                        <select v-model="tempVariantConsumable.consumable_id" class="flex-1 border p-1 rounded text-xs h-8 bg-white">
                                            <option :value="null">Матеріал...</option>
                                            <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                        </select>
                                        <input v-model="tempVariantConsumable.quantity" type="number" placeholder="Кіл-ть" class="w-20 border p-1 rounded text-xs h-8">
                                        <button @click="addVariantConsumable" class="bg-teal-200 px-3 rounded hover:bg-teal-300"><i class="fas fa-plus text-xs"></i></button>
                                    </div>
                                    <div class="flex flex-wrap gap-1">
                                        <span v-for="(vc, idx) in variantBuilder.consumables" :key="idx" class="text-xs bg-teal-50 text-teal-700 px-2 py-1 rounded border border-teal-100 flex items-center gap-1">
                                            {{ consumables.find(c => c.id === vc.consumable_id)?.name }}: {{ vc.quantity }}
                                            <button @click="removeVariantConsumable(idx)" class="ml-1 text-red-500 font-bold">×</button>
                                        </span>
                                    </div>
                                </div>

                                <div class="flex gap-2 mt-4">
                                    <button @click="handleVariantSave" class="flex-1 bg-gray-800 text-white py-2 rounded-lg text-sm hover:bg-gray-900 font-bold">
                                        {{ editingVariantIndex === -1 ? 'Додати варіант' : 'Оновити варіант' }}
                                    </button>
                                    <button v-if="editingVariantIndex !== -1" @click="cancelVariantEdit" class="px-3 bg-gray-200 rounded-lg text-gray-600">Скасувати</button>
                                </div>
                            </div>

                            <div class="space-y-2">
                                <div v-for="(v, idx) in newProduct.variants" :key="idx" class="bg-white p-2 rounded border border-gray-100 shadow-sm hover:border-purple-300 transition group">
                                    <div class="flex justify-between items-center">
                                        <div>
                                            <div class="font-bold text-sm">{{ v.name }} - {{ v.price }}₴</div>
                                            <div class="text-xs text-gray-400 flex gap-2">
                                                <span class="bg-yellow-50 px-1 border border-yellow-100 rounded text-yellow-700 font-mono">{{ v.sku }}</span>
                                                <span v-if="v.margin !== undefined" :class="v.margin > 0 ? 'text-green-500' : 'text-red-500'">
                                                    (Приб: {{ v.margin }}₴)
                                                </span>
                                            </div>
                                            
                                        </div>
                                        <div class="flex gap-1 opacity-50 group-hover:opacity-100">
                                            <button @click="editVariant(idx)" class="p-1 text-blue-500"><i class="fas fa-pen"></i></button>
                                            <button @click="removeVariant(idx)" class="p-1 text-red-500"><i class="fas fa-trash"></i></button>
                                        </div>
                                    </div>
                                    
                                    <div v-if="v.ingredients.length || v.consumables.length" class="mt-2 pt-1 border-t border-gray-100 flex flex-col gap-1">
                                        <div v-if="v.ingredients.length" class="flex items-start gap-1">
                                            <i class="fas fa-flask text-orange-400 text-[10px] mt-0.5"></i> 
                                            <div class="flex flex-wrap gap-1">
                                                <span v-for="vi in v.ingredients" :key="vi.id" class="text-[10px] bg-gray-50 px-1 rounded text-gray-600">
                                                    {{ ingredients.find(i => i.id === vi.ingredient_id)?.name }}: {{ vi.quantity }}
                                                </span>
                                            </div>
                                        </div>
                                        <div v-if="v.consumables.length" class="flex items-start gap-1">
                                            <i class="fas fa-box-open text-teal-500 text-[10px] mt-0.5"></i> 
                                            <div class="flex flex-wrap gap-1">
                                                <span v-for="vc in v.consumables" :key="vc.id" class="text-[10px] bg-gray-50 px-1 rounded text-gray-600">
                                                    {{ consumables.find(c => c.id === vc.consumable_id)?.name }}: {{ vc.quantity }}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-8 border-t pt-6 flex justify-end gap-4">
                <button @click="handleCancel" class="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 transition">Скасувати</button>
                <button @click="handleSave" class="px-8 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 shadow-lg shadow-purple-200 transition transform hover:-translate-y-0.5">
                    {{ isEditing ? 'Зберегти зміни' : 'Створити товар' }}
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 flex flex-col min-h-0">
            <div class="p-4 border-b flex gap-4 bg-gray-50 rounded-t-2xl">
                <div class="relative flex-1">
                    <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
                    <input v-model="productSearch" placeholder="Пошук товару..." class="w-full pl-10 pr-4 py-2 rounded-lg border focus:ring-2 focus:ring-purple-200 outline-none">
                </div>
            </div>

            <div class="overflow-auto flex-1">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-500 uppercase text-xs sticky top-0">
                        <tr>
                            <th class="p-4">Назва</th>
                            <th class="p-4">Категорія</th>
                            <th class="p-4">Рецепт / Процеси</th>
                            <th class="p-4">Варіанти / Комплект</th>
                            <th class="p-4 text-center">Дії</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="p in filteredProducts" :key="p.id" class="hover:bg-gray-50 transition">
                            <td class="p-4">
                                <div class="font-bold text-gray-800 text-base">{{ p.name }}</div>
                                <div class="text-gray-500 font-mono">{{ p.price }} ₴</div>
                                
                                <div v-if="!p.has_variants && p.margin !== undefined" class="text-xs mt-1">
                                     <span :class="p.margin > 0 ? 'text-green-600' : 'text-red-500'">
                                        Прибуток: {{ p.margin }} ₴
                                     </span>
                                </div>
                                
                                <div v-if="p.description" class="text-xs text-gray-400 mt-1 line-clamp-1">{{ p.description }}</div>
                            </td>
                            <td class="p-4">
                                <span class="bg-purple-50 text-purple-700 px-2 py-1 rounded-lg text-xs font-bold">
                                    {{ getCategoryName(p.category_id) }}
                                </span>
                            </td>
                            <td class="p-4">
                                <div class="space-y-1">
                                    <div v-if="p.master_recipe" class="flex items-center gap-1 text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded w-fit">
                                        <i class="fas fa-scroll"></i> {{ p.master_recipe.name }}
                                    </div>
                                    <div v-if="p.process_groups && p.process_groups.length" class="flex flex-wrap gap-1">
                                        <span v-for="pg in p.process_groups" :key="pg.id" class="text-[10px] bg-indigo-50 text-indigo-600 border border-indigo-100 px-1.5 py-0.5 rounded uppercase font-bold">
                                            {{ pg.name }}
                                        </span>
                                    </div>
                                </div>
                            </td>
                            <td class="p-4">
                                <div class="space-y-2">
                                    <div v-if="p.has_variants && p.variants.length">
                                        <div v-for="v in p.variants" :key="v.id" class="text-xs bg-gray-100 p-1.5 rounded mb-1 border border-gray-200">
                                            <div class="font-bold flex justify-between">
                                                <span>{{ v.name }}</span>
                                                <span>{{ v.price }}₴</span>
                                            </div>
                                            <div v-if="v.ingredients.length || v.consumables.length" class="mt-1 pt-1 border-t border-gray-200 flex flex-col gap-1">
                                                <div v-if="v.ingredients.length" class="flex items-start gap-1">
                                                    <i class="fas fa-flask text-orange-400 text-[10px] mt-0.5"></i> 
                                                    <div class="flex flex-wrap gap-1">
                                                        <span v-for="vi in v.ingredients" :key="vi.id" class="bg-white border px-1 rounded">
                                                            {{ vi.ingredient_name || '?' }}: {{ vi.quantity }}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div v-if="v.consumables.length" class="flex items-start gap-1">
                                                    <i class="fas fa-box-open text-teal-500 text-[10px] mt-0.5"></i> 
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