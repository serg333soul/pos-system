<script setup>
import { ref, watch, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useProducts } from '@/composables/useProducts'
import IngredientSelect from '@/components/common/IngredientSelect.vue'

const props = defineProps({
    isOpen: Boolean,
    isEdit: Boolean
})

const emit = defineEmits(['close', 'saved'])

// Підключаємо логіку
const { categories, recipes, ingredients, consumables } = useWarehouse()
const { 
    newProduct, 
    saveProduct, 
    removeProductConsumable
} = useProducts()

// Локальні змінні
const tempSimpleIngredient = ref({ id: null, qty: 0 })
const tempProductConsumable = ref({ consumable_id: "", quantity: 1 })
const serverCalculatedCost = ref(0)

// --- ОБЧИСЛЮВАНІ ВЛАСТИВОСТІ ---
const selectedRecipe = computed(() => {
    if (!newProduct.value.master_recipe_id) return null
    return recipes.value.find(r => r.id === newProduct.value.master_recipe_id)
})

const getIngredientPrice = (id) => {
    const ing = ingredients.value.find(i => i.id === id)
    return ing ? ing.cost_per_unit : 0
}

const getConsumablePrice = (id) => {
    const cons = consumables.value.find(c => c.id === id)
    return cons ? cons.cost_per_unit : 0
}

// --- КАЛЬКУЛЯТОР ---
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
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        if(res.ok) {
            const data = await res.json()
            serverCalculatedCost.value = data.total_cost
        }
    } catch (e) { console.error("Cost calc error:", e) }
}

watch(() => [
    newProduct.value.master_recipe_id, 
    newProduct.value.output_weight,
    newProduct.value.ingredients, 
    newProduct.value.consumables
], () => {
    if (props.isOpen) calculateCost()
}, { deep: true })

// --- МЕТОДИ ---
const addSimpleIngredient = () => {
    if (tempSimpleIngredient.value.id && tempSimpleIngredient.value.qty > 0) {
        if (!newProduct.value.ingredients) newProduct.value.ingredients = []
        
        const existing = newProduct.value.ingredients.find(i => i.ingredient_id === tempSimpleIngredient.value.id)
        const ingObj = ingredients.value.find(i => i.id === tempSimpleIngredient.value.id)

        if (existing) {
            existing.quantity += parseFloat(tempSimpleIngredient.value.qty)
        } else {
            newProduct.value.ingredients.push({
                ingredient_id: tempSimpleIngredient.value.id,
                quantity: parseFloat(tempSimpleIngredient.value.qty),
                ingredient_name: ingObj?.name || '???'
            })
        }
        tempSimpleIngredient.value = { id: null, qty: 0 }
    }
}

const removeSimpleIngredient = (index) => {
    newProduct.value.ingredients.splice(index, 1)
}

const handleAddConsumable = () => {
    if (tempProductConsumable.value.consumable_id) {
        const c = consumables.value.find(x => x.id === tempProductConsumable.value.consumable_id)
        if (!newProduct.value.consumables) newProduct.value.consumables = []
        
        newProduct.value.consumables.push({
            consumable_id: tempProductConsumable.value.consumable_id,
            quantity: tempProductConsumable.value.quantity,
            name: c?.name || '???'
        })
        tempProductConsumable.value.quantity = 1
    }
}

const handleSave = async () => {
    newProduct.value.has_variants = false
    const success = await saveProduct()
    if (success) {
        emit('saved')
        emit('close')
    }
}
</script>

<template>
    <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden animate-fade-in">
            
            <div class="p-5 border-b flex justify-between items-center bg-gray-50">
                <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <span class="bg-blue-100 text-blue-600 p-2 rounded-lg text-lg">☕</span>
                    {{ isEdit ? 'Редагування товару' : 'Новий товар' }}
                </h3>
                <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200 transition">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <div class="p-6 overflow-y-auto flex-1 space-y-6 bg-white">
                
                <div class="bg-gray-50 p-4 rounded-lg border border-gray-100">
                    <h4 class="font-bold text-gray-700 mb-3 uppercase text-xs tracking-wider">Основна інформація</h4>
                    <div class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-bold text-gray-700 mb-1">Назва товару <span class="text-red-500">*</span></label>
                                <input v-model="newProduct.name" type="text" class="w-full border rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500" placeholder="Назва товару">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-600 mb-1">Категорія</label>
                                <select v-model="newProduct.category_id" class="w-full border rounded-lg p-2.5 bg-white">
                                    <option :value="null">-- Без категорії --</option>
                                    <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                                </select>
                            </div>
                            <div class="mb-4">
                              <label class="block text-sm font-bold text-gray-600 mb-1">Прикріпити до кімнати (опціонально)</label>
                              <select v-model="newProduct.room_id" class="w-full border p-2 rounded-xl bg-white">
                                <option :value="null">-- Без кімнати (окремий товар) --</option>
                                <option v-for="room in warehouse.productRooms.value" :key="room.id" :value="room.id">
                                  {{ room.name }}
                                </option>
                              </select>
                            </div>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">Опис</label>
                            <input v-model="newProduct.description" type="text" class="w-full border rounded-lg p-2.5" placeholder="Додаткова інформація...">
                        </div>
                    </div>
                </div>

                <div class="bg-blue-50 p-4 rounded-lg border border-blue-100">
                    <h4 class="font-bold text-blue-800 mb-3 uppercase text-xs tracking-wider">Фінанси</h4>
    
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        
                        <div>
                            <label class="block text-xs font-bold text-blue-900 mb-1 uppercase">Ціна продажу</label>
                            <div class="relative">
                                <input 
                                    v-model.number="newProduct.price" 
                                    type="number" 
                                    step="0.1" 
                                    class="w-full border-2 border-blue-200 rounded-lg p-2 pl-3 text-lg font-bold text-gray-800 focus:ring-2 focus:ring-blue-500 shadow-sm transition h-[46px]"
                                >
                                <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">₴</span>
                            </div>
                        </div>
        
                        <div class="bg-white border border-blue-100 rounded-lg px-3 shadow-sm h-[46px] flex flex-col justify-center">
                            <div class="flex justify-between items-center w-full">
                                <span class="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Собівартість</span>
                                <span class="font-medium text-gray-700">{{ serverCalculatedCost.toFixed(2) }} ₴</span>
                            </div>
                        </div>

                        <div class="bg-white border border-blue-100 rounded-lg px-3 shadow-sm h-[46px] flex flex-col justify-center">
                            <div class="flex justify-between items-center w-full">
                                <span class="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Маржа</span>
                                <div class="font-bold text-sm" :class="newProduct.price > serverCalculatedCost ? 'text-green-600' : 'text-red-500'">
                                    {{ newProduct.price > 0 ? (newProduct.price - serverCalculatedCost).toFixed(2) : 0 }} ₴ 
                                    <span class="text-xs text-gray-400 font-normal ml-1">
                                        ({{ newProduct.price > 0 ? Math.round(((newProduct.price - serverCalculatedCost) / newProduct.price) * 100) : 0 }}%)
                                    </span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <h4 class="font-bold text-gray-700 mb-3 uppercase text-xs tracking-wider">Складський облік</h4>
                    
                    <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                        <label class="flex items-center gap-3 cursor-pointer p-2 hover:bg-gray-50 rounded-lg transition border border-transparent hover:border-gray-200">
                            <input v-model="newProduct.track_stock" type="checkbox" class="w-5 h-5 rounded text-blue-600 focus:ring-blue-500">
                            <span class="font-medium text-gray-700">Вести облік залишків готового продукту</span>
                        </label>
                        
                        <div v-if="newProduct.track_stock" class="flex-1 w-full sm:w-auto animate-fade-in">
                            <label class="text-xs uppercase font-bold text-gray-500 block mb-1">Поточний залишок</label>
                            <div class="flex items-center">
                                <input v-model.number="newProduct.stock_quantity" type="number" class="w-full max-w-xs border rounded-l-lg p-2 focus:ring-2 focus:ring-blue-500">
                                <span class="bg-gray-100 px-4 py-2 border border-l-0 rounded-r-lg text-gray-600 font-medium">шт</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-orange-50 p-4 rounded-lg border border-orange-100 shadow-sm">
                    <h4 class="font-bold text-orange-800 mb-4 flex items-center gap-2 uppercase text-xs tracking-wider">
                        <i class="fas fa-book-open"></i> Технічна карта (Рецепт)
                    </h4>
                    
                    <div class="grid grid-cols-1 md:grid-cols-12 gap-4 mb-4">
                        <div class="md:col-span-8">
                            <label class="block text-sm text-orange-900 mb-1 font-medium">Оберіть рецепт</label>
                            <select v-model="newProduct.master_recipe_id" class="w-full border border-orange-200 rounded-lg p-2.5 text-sm bg-white focus:ring-2 focus:ring-orange-400">
                                <option :value="null">-- Без рецепту --</option>
                                <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                            </select>
                        </div>
                        <div class="md:col-span-4">
                            <label class="block text-sm text-orange-900 mb-1 font-medium">Вага виходу</label>
                            <div class="flex items-center">
                                <input v-model.number="newProduct.output_weight" type="number" class="w-full border border-orange-200 rounded-l-lg p-2.5 text-sm" placeholder="250">
                                <span class="bg-orange-100 px-3 py-2.5 border border-orange-200 border-l-0 rounded-r-lg text-orange-700 text-xs font-bold">мл/г</span>
                            </div>
                        </div>
                    </div>

                    <div v-if="selectedRecipe" class="bg-white rounded-lg border border-orange-200 overflow-hidden">
                        <div class="bg-orange-100 px-4 py-2 border-b border-orange-200 flex justify-between items-center">
                            <h5 class="font-bold text-orange-900 text-sm">Склад техкарти: {{ selectedRecipe.name }}</h5>
                        </div>
                        <table class="w-full text-sm text-left">
                            <thead class="bg-orange-50 text-orange-800 font-medium border-b border-orange-100">
                                <tr>
                                    <th class="p-3 pl-4">Інгредієнт</th>
                                    <th class="p-3">В рецепті</th>
                                    <th class="p-3">Витрата</th>
                                    <th class="p-3 text-right pr-4">Вартість</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-orange-50">
                                <tr v-for="item in selectedRecipe.items" :key="item.id">
                                    <td class="p-3 pl-4 text-gray-700">{{ item.ingredient_name }}</td>
                                    <td class="p-3 text-gray-500 text-xs">
                                        {{ item.quantity }} {{ item.is_percentage ? '%' : (item.unit_name || 'од') }}
                                    </td>
                                    <td class="p-3 font-medium text-gray-800">
                                        {{ item.is_percentage 
                                            ? ((item.quantity / 100) * (newProduct.output_weight || 0)).toFixed(1) 
                                            : item.quantity 
                                        }} {{ item.is_percentage ? 'мл/г' : (item.unit_name || 'од') }}
                                    </td>
                                    <td class="p-3 text-right pr-4 text-gray-600 font-mono">
                                        {{ ((item.is_percentage 
                                                ? ((item.quantity / 100) * (newProduct.output_weight || 0)) 
                                                : item.quantity
                                            ) * getIngredientPrice(item.ingredient_id)).toFixed(2) 
                                        }} ₴
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <h4 class="font-bold text-gray-800 mb-3 border-b pb-2 flex items-center gap-2">
                        <i class="fas fa-lemon text-yellow-500"></i> Додаткові інгредієнти
                    </h4>
                    
                    <div class="flex gap-2 mb-4 bg-gray-50 p-2 rounded-lg">
                        <IngredientSelect 
                            v-model="tempSimpleIngredient.id" 
                            :ingredients="ingredients" 
                            class="flex-1" 
                        />
                        <input v-model.number="tempSimpleIngredient.qty" type="number" step="0.001" placeholder="К-сть" class="w-24 border rounded p-2 text-sm focus:ring-2 focus:ring-yellow-400">
                        <button @click="addSimpleIngredient" class="bg-yellow-500 text-white px-4 rounded hover:bg-yellow-600 font-medium shadow-sm transition">
                            <i class="fas fa-plus"></i> Додати
                        </button>
                    </div>

                    <div v-if="newProduct.ingredients?.length" class="border rounded-lg overflow-hidden">
                        <table class="w-full text-sm">
                            <thead class="bg-gray-100 text-gray-600 text-left text-xs uppercase tracking-wider">
                                <tr>
                                    <th class="p-3 pl-4">Назва</th>
                                    <th class="p-3">К-сть</th>
                                    <th class="p-3 text-right">Вартість</th>
                                    <th class="p-3 w-10"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-100">
                                <tr v-for="(ing, idx) in newProduct.ingredients" :key="idx" class="hover:bg-gray-50">
                                    <td class="p-3 pl-4 font-medium">{{ ing.ingredient_name }}</td>
                                    <td class="p-3 text-gray-600">{{ ing.quantity }}</td>
                                    <td class="p-3 text-right font-mono text-gray-700">
                                        {{ (ing.quantity * getIngredientPrice(ing.ingredient_id)).toFixed(2) }} ₴
                                    </td>
                                    <td class="p-3 text-center">
                                        <button @click="removeSimpleIngredient(idx)" class="text-red-400 hover:text-red-600 hover:bg-red-50 p-1 rounded transition">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-else class="text-sm text-gray-400 italic text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">
                        Немає додаткових інгредієнтів
                    </div>
                </div>

                <div class="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <h4 class="font-bold text-gray-800 mb-3 border-b pb-2 flex items-center gap-2">
                        <i class="fas fa-box-open text-blue-500"></i> Витратні матеріали
                    </h4>

                    <div class="flex gap-2 mb-4 bg-gray-50 p-2 rounded-lg">
                        <select v-model="tempProductConsumable.consumable_id" class="flex-1 border rounded p-2 text-sm bg-white focus:ring-2 focus:ring-blue-400">
                            <option value="">Оберіть матеріал...</option>
                            <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                        </select>
                        <input v-model.number="tempProductConsumable.quantity" type="number" placeholder="Шт" class="w-24 border rounded p-2 text-sm focus:ring-2 focus:ring-blue-400">
                        <button @click="handleAddConsumable" class="bg-blue-500 text-white px-4 rounded hover:bg-blue-600 font-medium shadow-sm transition">
                            <i class="fas fa-plus"></i> Додати
                        </button>
                    </div>

                    <div v-if="newProduct.consumables?.length" class="border rounded-lg overflow-hidden">
                        <table class="w-full text-sm">
                            <thead class="bg-gray-100 text-gray-600 text-left text-xs uppercase tracking-wider">
                                <tr>
                                    <th class="p-3 pl-4">Назва</th>
                                    <th class="p-3">К-сть</th>
                                    <th class="p-3 text-right">Вартість</th>
                                    <th class="p-3 w-10"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-100">
                                <tr v-for="(c, idx) in newProduct.consumables" :key="idx" class="hover:bg-gray-50">
                                    <td class="p-3 pl-4 font-medium">{{ c.name || c.consumable_name }}</td>
                                    <td class="p-3 text-gray-600">{{ c.quantity }} шт</td>
                                    <td class="p-3 text-right font-mono text-gray-700">
                                        {{ (c.quantity * getConsumablePrice(c.consumable_id)).toFixed(2) }} ₴
                                    </td>
                                    <td class="p-3 text-center">
                                        <button @click="removeProductConsumable(idx)" class="text-red-400 hover:text-red-600 hover:bg-red-50 p-1 rounded transition">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-else class="text-sm text-gray-400 italic text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">
                        Немає витратних матеріалів
                    </div>
                </div>

            </div>

            <div class="p-5 border-t bg-gray-50 flex justify-end gap-3">
                <button @click="$emit('close')" class="px-5 py-2.5 border border-gray-300 rounded-lg text-gray-700 hover:bg-white transition font-medium">
                    Скасувати
                </button>
                <button @click="handleSave" class="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-md transition font-medium flex items-center gap-2">
                    <i class="fas fa-check"></i> {{ isEdit ? 'Зберегти' : 'Створити' }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
</style>