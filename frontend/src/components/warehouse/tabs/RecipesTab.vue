<script setup>
import { ref, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import IngredientSelect from '@/components/common/IngredientSelect.vue' 

const { recipes, ingredients, fetchData, createItem, deleteItem } = useWarehouse()

const editingRecipeId = ref(null)
const newRecipe = ref({ name: '', description: '', items: [] })
const tempRecipeItem = ref({ ingredient_id: '', quantity: 0, is_percentage: false })

const getSelectedIngredientSymbol = computed(() => {
    if (!tempRecipeItem.value.ingredient_id) return ''
    const ing = ingredients.value.find(i => i.id === tempRecipeItem.value.ingredient_id)
    return ing ? ing.unit.symbol : ''
})

const editRecipe = (r) => {
    editingRecipeId.value = r.id
    newRecipe.value = {
        name: r.name,
        description: r.description,
        items: r.items.map(item => ({ 
            ingredient_id: item.ingredient_id, 
            quantity: item.quantity,
            is_percentage: item.is_percentage, 
            ingredient_name: item.ingredient_name 
        }))
    }
}

const resetRecipeForm = () => {
    editingRecipeId.value = null
    newRecipe.value = { name: '', description: '', items: [] }
    tempRecipeItem.value = { ingredient_id: '', quantity: 0, is_percentage: false }
}

const addIngredientToMaster = () => {
    if(!tempRecipeItem.value.ingredient_id || !tempRecipeItem.value.quantity) return
    const ing = ingredients.value.find(i => i.id === tempRecipeItem.value.ingredient_id)
    newRecipe.value.items.push({
        ingredient_id: tempRecipeItem.value.ingredient_id,
        quantity: tempRecipeItem.value.quantity,
        is_percentage: tempRecipeItem.value.is_percentage, 
        ingredient_name: ing ? ing.name : ''
    })
    tempRecipeItem.value = { ingredient_id: '', quantity: 0, is_percentage: false }
}

const removeIngredientFromMaster = (idx) => {
    newRecipe.value.items.splice(idx, 1)
}

const saveRecipe = async () => {
    if(!newRecipe.value.name) return alert("Вкажіть назву рецепту")
    
    let url = '/api/recipes/'; 
    // createItem в useWarehouse робить тільки POST, тому для PUT нам треба вручну або розширити composable.
    // Тут зробимо це локально, бо це специфічна логіка
    if(editingRecipeId.value) {
        await fetch(`/api/recipes/${editingRecipeId.value}`, { 
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newRecipe.value) 
        })
        await fetchData()
    } else {
        await createItem(url, newRecipe.value)
    }
    
    alert("Рецепт збережено!")
    resetRecipeForm()
}

const handleDelete = (id) => deleteItem(`/api/recipes/${id}`)
</script>

<template>
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div class="xl:col-span-1 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-fit">
            <div class="p-4 bg-gray-50 border-b font-bold text-gray-700">Всі рецепти</div>
            <div class="max-h-[600px] overflow-y-auto custom-scrollbar">
                <div v-for="r in recipes" :key="r.id" class="p-4 border-b hover:bg-orange-50 cursor-pointer flex justify-between items-center group">
                    <div @click="editRecipe(r)" class="flex-1">
                        <div class="font-bold text-gray-800">{{ r.name }}</div>
                        <div class="text-xs text-gray-400">{{ r.items.length }} інгр.</div>
                    </div>
                    <button @click="handleDelete(r.id)" class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"><i class="fas fa-trash"></i></button>
                </div>
            </div>
            <button @click="resetRecipeForm" class="w-full py-3 text-center text-orange-600 font-bold hover:bg-orange-50 transition border-t">
                <i class="fas fa-plus-circle"></i> Створити новий
            </button>
        </div>

        <div class="xl:col-span-2 bg-white rounded-2xl shadow-sm border border-orange-100 border-2 h-fit">
             <div class="p-6 border-b flex justify-between items-center bg-orange-50 rounded-t-xl">
                 <h3 class="font-bold text-xl text-orange-800">{{ editingRecipeId ? 'Редагування' : 'Новий рецепт' }}</h3>
                 <button v-if="editingRecipeId" @click="resetRecipeForm" class="text-xs text-red-500 hover:underline">Закрити</button>
             </div>
             
             <div class="p-6 space-y-4">
                 <input v-model="newRecipe.name" placeholder="Назва рецепту" class="w-full border p-2 rounded focus:ring-2 ring-orange-200 outline-none text-lg font-bold">
                 
                 <div class="bg-gray-50 p-4 rounded-xl border border-gray-200">
                     <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Склад рецепту</label>
                     <div class="space-y-2 mb-4">
                         <div v-for="(item, idx) in newRecipe.items" :key="idx" class="flex items-center gap-3 bg-white p-2 rounded border shadow-sm">
                             <span class="flex-1 font-bold text-gray-700">{{ item.ingredient_name }}</span>
                             <span class="font-mono bg-gray-100 px-2 rounded" :class="item.is_percentage ? 'text-blue-600' : ''">
                                 {{ item.quantity }} {{ item.is_percentage ? '%' : '' }}
                             </span>
                             <button @click="removeIngredientFromMaster(idx)" class="text-red-400 hover:text-red-600"><i class="fas fa-times"></i></button>
                         </div>
                     </div>

                     <div class="flex gap-2 items-end border-t pt-3">
                         <div class="flex-1">
                             <label class="text-[10px] text-gray-400 font-bold uppercase">Інгредієнт</label>
                             <IngredientSelect v-model="tempRecipeItem.ingredient_id" :ingredients="ingredients" />
                         </div>
                         
                         <div class="flex flex-col">
                             <label class="text-[10px] text-gray-400 font-bold uppercase mb-1">Тип</label>
                             <div class="flex bg-white border rounded h-[38px] overflow-hidden">
                                 <button @click="tempRecipeItem.is_percentage=false" :class="!tempRecipeItem.is_percentage ? 'bg-gray-200 font-bold':''" class="px-2 text-xs border-r hover:bg-gray-100">FIX</button>
                                 <button @click="tempRecipeItem.is_percentage=true" :class="tempRecipeItem.is_percentage ? 'bg-blue-100 text-blue-700 font-bold':''" class="px-2 text-xs hover:bg-gray-100">%</button>
                             </div>
                         </div>

                         <div class="w-24">
                             <label class="text-[10px] text-gray-400 font-bold uppercase">Кількість</label>
                             <div class="relative">
                                 <input v-model="tempRecipeItem.quantity" type="number" step="0.001" class="w-full border p-2 rounded h-[38px] pr-8">
                                 <span class="absolute right-2 top-2 text-xs text-gray-400">
                                     {{ tempRecipeItem.is_percentage ? '%' : getSelectedIngredientSymbol }}
                                 </span>
                             </div>
                         </div>
                         <button @click="addIngredientToMaster" class="bg-orange-500 text-white w-10 h-[38px] rounded hover:bg-orange-600 transition"><i class="fas fa-plus"></i></button>
                     </div>
                 </div>

                 <button @click="saveRecipe" class="w-full bg-green-600 text-white py-3 rounded-xl font-bold hover:bg-green-700 shadow-lg mt-2">Зберегти рецепт</button>
             </div>
        </div>
    </div>
</template>