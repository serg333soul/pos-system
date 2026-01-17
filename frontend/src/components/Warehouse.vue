<script setup>
import { ref, onMounted, computed } from 'vue'
import IngredientSelect from './IngredientSelect.vue'

const activeTab = ref('products') 
const categories = ref([]); const units = ref([]); const ingredients = ref([]); const products = ref([]);
const recipes = ref([]) 
const consumables = ref([]) // <-- НОВЕ

const loading = ref(false)

// Forms
const newCategory = ref({ name: '', slug: '', color: '#3b82f6', parent_id: '' }) 
const newUnit = ref({ name: '', symbol: '' })
const newIngredient = ref({ name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 })
const newConsumable = ref({ name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 }) // <-- НОВЕ

// --- РЕЦЕПТИ (Master Recipes) ---
const editingRecipeId = ref(null)
const newRecipe = ref({ name: '', description: '', items: [] })
const tempRecipeItem = ref({ ingredient_id: '', quantity: 0, is_percentage: false })

// --- ТОВАР (Product) ---
const isVariantMode = ref(false)
const editingProductId = ref(null) 
const productSearch = ref('') 
const newProduct = ref({
  name: '', description: '', category_id: '',
  price: 0, 
  master_recipe_id: null,
  output_weight: 0, 
  variants: [], 
  modifier_groups: [],
  consumables: [] // <-- НОВЕ: Consumables для головного товару
})
const variantBuilder = ref({ 
  name: '', price: 0, master_recipe_id: null, output_weight: 0,
  consumables: [] // <-- НОВЕ: Consumables для варіанту
})

// Тимчасові змінні для додавання consumable до товару/варіанту в UI
const tempProductConsumable = ref({ consumable_id: '', quantity: 1 })
const tempVariantConsumable = ref({ consumable_id: '', quantity: 1 })

// --- ЗАВАНТАЖЕННЯ ---
const fetchData = async () => {
  loading.value = true
  const safeFetch = async (url) => {
    try {
      const res = await fetch(url)
      if (!res.ok) return [] 
      return await res.json()
    } catch (e) { return [] }
  }

  categories.value = await safeFetch('/api/categories/')
  units.value = await safeFetch('/api/units/')
  ingredients.value = await safeFetch('/api/ingredients/')
  consumables.value = await safeFetch('/api/consumables/') // <-- НОВЕ
  products.value = await safeFetch('/api/products/')
  recipes.value = await safeFetch('/api/recipes/')
  
  loading.value = false
}

const getParentName = (parentId) => {
    if (!parentId) return '';
    const parent = categories.value.find(c => c.id === parentId);
    return parent ? parent.name : '???';
}

// --- CONSUMABLES CRUD ---
const createConsumable = async () => {
    if(!newConsumable.value.name) return;
    await fetch('/api/consumables/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newConsumable.value)});
    newConsumable.value={name:'',unit_id:'',cost_per_unit:0,stock_quantity:0};
    fetchData();
}
const deleteConsumable = async (id) => {
    if(!confirm("Видалити?")) return;
    await fetch(`/api/consumables/${id}`, {method:'DELETE'});
    fetchData();
}

// --- PRODUCT FORM LOGIC UPDATES ---
const addConsumableToProduct = () => {
    if(!tempProductConsumable.value.consumable_id) return
    const c = consumables.value.find(x => x.id === tempProductConsumable.value.consumable_id)
    newProduct.value.consumables.push({
        consumable_id: tempProductConsumable.value.consumable_id,
        quantity: tempProductConsumable.value.quantity,
        name: c ? c.name : '???' // Для відображення
    })
    tempProductConsumable.value = { consumable_id: '', quantity: 1 }
}
const removeConsumableFromProduct = (idx) => newProduct.value.consumables.splice(idx, 1)

const addConsumableToVariant = () => {
    if(!tempVariantConsumable.value.consumable_id) return
    const c = consumables.value.find(x => x.id === tempVariantConsumable.value.consumable_id)
    variantBuilder.value.consumables.push({
        consumable_id: tempVariantConsumable.value.consumable_id,
        quantity: tempVariantConsumable.value.quantity,
        name: c ? c.name : '???'
    })
    tempVariantConsumable.value = { consumable_id: '', quantity: 1 }
}
const removeConsumableFromVariant = (idx) => variantBuilder.value.consumables.splice(idx, 1)


// --- ЛОГІКА РЕЦЕПТІВ (CRUD) ---
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
    
    let url = '/api/recipes/'; let method = 'POST'
    if(editingRecipeId.value) { url = `/api/recipes/${editingRecipeId.value}`; method = 'PUT' }
    
    const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newRecipe.value)
    })
    if(res.ok) {
        alert("Рецепт збережено!")
        fetchData()
        resetRecipeForm()
    } else { alert("Помилка") }
}
const deleteRecipe = async (id) => {
    if(!confirm("Видалити цей рецепт?")) return
    const res = await fetch(`/api/recipes/${id}`, { method: 'DELETE' })
    if(res.ok) fetchData()
    else { 
        const err = await res.json()
        alert("Помилка: " + err.detail) 
    }
}


// --- ЛОГІКА ТОВАРІВ ---
const filteredProducts = computed(() => {
    if (!productSearch.value) return products.value
    const lower = productSearch.value.toLowerCase()
    return products.value.filter(p => p.name.toLowerCase().includes(lower))
})
const editProduct = (p) => {
    editingProductId.value = p.id
    isVariantMode.value = p.has_variants
    
    newProduct.value = {
        name: p.name,
        description: p.description || '',
        category_id: p.category_id,
        price: p.price,
        master_recipe_id: p.master_recipe_id,
        output_weight: p.output_weight || 0,
        
        // ВАЖЛИВО: Захищене маппінг варіантів
        variants: p.variants.map(v => ({
            ...v,
            consumables: Array.isArray(v.consumables) ? v.consumables.map(vc => ({
                consumable_id: vc.consumable_id,
                quantity: vc.quantity,
                name: vc.consumable_name || '???' // Фолбек, якщо назва не прийшла
            })) : []
        })),
        
        modifier_groups: p.modifier_groups ? JSON.parse(JSON.stringify(p.modifier_groups)) : [],
        
        // Маппінг матеріалів головного товару
        consumables: p.consumables ? p.consumables.map(c => ({
            consumable_id: c.consumable_id, 
            quantity: c.quantity,
            name: c.consumable_name 
        })) : []
    }
}
const resetProductForm = () => {
    editingProductId.value = null
    isVariantMode.value = false
    newProduct.value = { name: '', description: '', category_id: '', price: 0, master_recipe_id: null, output_weight: 0, variants: [], modifier_groups: [], consumables: [] }
}
const saveProduct = async () => {
    if (!newProduct.value.name || !newProduct.value.category_id) return alert("Вкажіть назву та категорію!")
    const payload = { ...newProduct.value, has_variants: isVariantMode.value, price: isVariantMode.value ? 0 : newProduct.value.price }
    
    let url = '/api/products/'; let method = 'POST'
    if (editingProductId.value) { url = `/api/products/${editingProductId.value}`; method = 'PUT' }
    
    const res = await fetch(url, { method: method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
    if(res.ok) { alert("Збережено!"); fetchData(); resetProductForm() } 
    else { alert("Помилка") }
}
const addVariant = () => {
    if(!variantBuilder.value.name || !variantBuilder.value.price) return alert("Заповніть назву та ціну")
    // Копіюємо consumables з білдера
    const variantPayload = {
        ...variantBuilder.value,
        consumables: [...variantBuilder.value.consumables]
    }
    newProduct.value.variants.push(variantPayload)
    // Reset builder
    variantBuilder.value = { name: '', price: 0, master_recipe_id: null, output_weight: 0, consumables: [] }
}
const removeVariant = (idx) => newProduct.value.variants.splice(idx, 1)

// Helpers for other CRUDs
const createUnit = async () => {
    if (!newUnit.value.name || !newUnit.value.symbol) { alert("Заповніть!"); return; }
    await fetch('/api/units/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newUnit.value) });
    newUnit.value = { name: '', symbol: '' }; fetchData();
}
const createIngredient = async () => { if(!newIngredient.value.name) return; await fetch('/api/ingredients/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newIngredient.value)}); newIngredient.value={name:'',unit_id:'',cost_per_unit:0,stock_quantity:0}; fetchData() }
const createCategory = async () => {
    if (!newCategory.value.name) return alert("Назва!");
    const payload = { ...newCategory.value };
    if (!payload.slug) payload.slug = payload.name.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now().toString().slice(-4);
    if (payload.parent_id === "") payload.parent_id = null;
    await fetch('/api/categories/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    newCategory.value = { name: '', slug: '', color: '#3b82f6', parent_id: '' }; fetchData();
}

const getSelectedIngredientSymbol = computed(() => {
    if (!tempRecipeItem.value.ingredient_id) return ''
    const ing = ingredients.value.find(i => i.id === tempRecipeItem.value.ingredient_id)
    return ing ? ing.unit.symbol : ''
})

onMounted(fetchData)
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    <div class="flex justify-between items-center mb-8">
      <h2 class="text-3xl font-bold text-gray-800">📦 Управління</h2>
      <button @click="fetchData" class="text-blue-600 hover:bg-blue-50 p-2 rounded-full"><i class="fas fa-sync-alt"></i></button>
    </div>

    <div class="flex space-x-1 bg-gray-200 p-1 rounded-xl w-fit mb-8 overflow-x-auto">
      <button @click="activeTab='recipes'" :class="activeTab==='recipes'?'bg-white text-orange-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-book-open mr-2"></i>Рецепти</button>
      <button @click="activeTab='products'" :class="activeTab==='products'?'bg-white text-purple-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Товари</button>
      <button @click="activeTab='ingredients'" :class="activeTab==='ingredients'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Інгредієнти</button>
      <button @click="activeTab='consumables'" :class="activeTab==='consumables'?'bg-white text-teal-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all"><i class="fas fa-box-open mr-2"></i>Витр. матеріали</button>
      <button @click="activeTab='units'" :class="activeTab==='units'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Одиниці</button>
      <button @click="activeTab='categories'" :class="activeTab==='categories'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Категорії</button>
    </div>

    <div v-if="activeTab === 'recipes'" class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div class="xl:col-span-1 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-fit">
            <div class="p-4 bg-gray-50 border-b font-bold text-gray-700">Всі рецепти</div>
            <div class="max-h-[600px] overflow-y-auto custom-scrollbar">
                <div v-for="r in recipes" :key="r.id" class="p-4 border-b hover:bg-orange-50 cursor-pointer flex justify-between items-center group">
                    <div @click="editRecipe(r)" class="flex-1">
                        <div class="font-bold text-gray-800">{{ r.name }}</div>
                        <div class="text-xs text-gray-400">{{ r.items.length }} інгр.</div>
                    </div>
                    <button @click="deleteRecipe(r.id)" class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"><i class="fas fa-trash"></i></button>
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


    <div v-if="activeTab === 'products'" class="grid grid-cols-1 xl:grid-cols-3 gap-8">
       <div class="xl:col-span-2 flex flex-col gap-4 h-fit">
           <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-3">
                 <i class="fas fa-search text-gray-400 ml-2"></i>
                 <input v-model="productSearch" type="text" placeholder="Пошук товару..." class="w-full outline-none text-gray-700">
            </div>
            <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <table class="w-full text-left">
                    <thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Назва</th><th class="p-4">Категорія</th><th class="p-4">Рецепт</th><th class="p-4 text-right">Ціна</th><th class="p-4"></th></tr></thead>
                    <tbody>
                        <tr v-for="p in filteredProducts" :key="p.id" class="border-b hover:bg-gray-50">
                            <td class="p-4 font-bold">{{ p.name }}</td>
                            <td class="p-4 text-sm text-gray-500">{{ p.category?.name }}</td>
                            <td class="p-4 text-sm">
                                <span v-if="p.master_recipe" class="text-orange-600 font-bold"><i class="fas fa-scroll"></i> {{ p.master_recipe.name }}</span>
                                <span v-else-if="p.has_variants && p.variants.some(v=>v.master_recipe_id)" class="text-purple-600 font-bold">По варіантах</span>
                                <span v-else class="text-gray-300">-</span>
                            </td>
                            <td class="p-4 text-right font-mono">{{ p.has_variants ? '...' : p.price + ' ₴' }}</td>
                            <td class="p-4 text-right"><button @click="editProduct(p)" class="text-blue-500 hover:text-blue-700"><i class="fas fa-pen"></i></button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
       </div>

       <div class="bg-white p-6 rounded-2xl shadow-sm border border-purple-100 border-2 h-fit sticky top-4 overflow-y-auto max-h-[90vh] custom-scrollbar">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold text-purple-700">{{ editingProductId ? 'Редагування' : 'Новий товар' }}</h3>
                <button v-if="editingProductId" @click="resetProductForm" class="text-red-500 text-xs hover:underline">Скасувати</button>
            </div>
            
            <div class="space-y-4">
                <input v-model="newProduct.name" placeholder="Назва" class="w-full border p-2 rounded">
                <select v-model="newProduct.category_id" class="w-full border p-2 rounded bg-white">
                    <option value="" disabled>Категорія...</option>
                    <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>

                <div class="flex items-center gap-3 bg-gray-100 p-2 rounded-lg">
                    <span class="text-xs font-bold uppercase text-gray-500 ml-2">Тип:</span>
                    <button @click="isVariantMode=false" :class="!isVariantMode ? 'bg-white shadow text-gray-800':'text-gray-400'" class="flex-1 py-1 rounded text-sm font-bold transition">Простий</button>
                    <button @click="isVariantMode=true" :class="isVariantMode ? 'bg-white shadow text-purple-600':'text-gray-400'" class="flex-1 py-1 rounded text-sm font-bold transition">З варіантами</button>
                </div>

                <div class="bg-teal-50 p-3 rounded-lg border border-teal-100 space-y-2">
                    <label class="block text-xs font-bold text-teal-600 uppercase">Витратні матеріали (для товару)</label>
                    <div class="space-y-1">
                        <div v-for="(c, idx) in newProduct.consumables" :key="idx" class="flex justify-between bg-white px-2 py-1 rounded text-sm">
                            <span>{{ c.name }}</span>
                            <span>x{{ c.quantity }} <button @click="removeConsumableFromProduct(idx)" class="text-red-400 ml-2">x</button></span>
                        </div>
                    </div>
                    <div class="flex gap-2">
                         <select v-model="tempProductConsumable.consumable_id" class="flex-1 border p-1 rounded text-xs bg-white">
                             <option value="">Матеріал...</option>
                             <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                         </select>
                         <input v-model="tempProductConsumable.quantity" type="number" class="w-16 border p-1 rounded text-xs" placeholder="К-сть">
                         <button @click="addConsumableToProduct" class="bg-teal-500 text-white px-2 rounded hover:bg-teal-600">+</button>
                    </div>
                </div>

                <div v-if="!isVariantMode" class="space-y-3 animate-fade-in">
                    <input v-model="newProduct.price" type="number" placeholder="Ціна (₴)" class="w-full border p-2 rounded font-bold text-right">
                    
                    <div class="bg-orange-50 p-3 rounded-lg border border-orange-100 space-y-2">
                        <label class="block text-xs font-bold text-orange-600 uppercase">Технологічна карта</label>
                        <select v-model="newProduct.master_recipe_id" class="w-full border p-2 rounded bg-white text-sm">
                            <option :value="null">-- Без списання --</option>
                            <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                        </select>
                        <div v-if="newProduct.master_recipe_id" class="animate-fade-in">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase">Вага виходу (для % списання)</label>
                            <div class="flex items-center gap-2">
                                <input v-model="newProduct.output_weight" type="number" class="w-full border p-2 rounded text-sm" placeholder="напр. 250">
                                <span class="text-xs font-bold text-gray-400">г/мл</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-if="isVariantMode" class="bg-purple-50 p-3 rounded-xl border border-purple-100 animate-fade-in">
                    <div v-if="newProduct.variants.length > 0" class="mb-4 space-y-2">
                         <div v-for="(v, idx) in newProduct.variants" :key="idx" class="bg-white p-2 rounded border shadow-sm text-sm">
                             <div class="flex justify-between mb-1">
                                 <span class="font-bold">{{ v.name }} ({{ v.price }} ₴)</span>
                                 <button @click="removeVariant(idx)" class="text-red-400"><i class="fas fa-times"></i></button>
                             </div>
                             <div class="text-xs text-gray-500 mb-1">
                                 Вага: {{ v.output_weight || 0 }}, Рецепт: {{ recipes.find(r=>r.id===v.master_recipe_id)?.name || '-' }}
                             </div>
                             <div v-if="v.consumables && v.consumables.length > 0" class="flex flex-wrap gap-1">
                                 <span v-for="vc in v.consumables" :key="vc.consumable_id" class="bg-teal-100 text-teal-800 text-[10px] px-1 rounded">
                                     {{ consumables.find(x=>x.id==vc.consumable_id)?.name }}: {{ vc.quantity }}
                                 </span>
                             </div>
                         </div>
                    </div>

                    <div class="bg-white/50 p-2 rounded-lg border border-dashed border-purple-200 space-y-2">
                        <div class="flex gap-2">
                            <input v-model="variantBuilder.name" placeholder="Назва (L)" class="flex-1 border p-1 rounded text-sm">
                            <input v-model="variantBuilder.price" type="number" placeholder="Ціна" class="w-20 border p-1 rounded text-sm">
                        </div>
                        
                        <div class="flex gap-2">
                             <input v-model="variantBuilder.output_weight" type="number" placeholder="Вага" class="w-20 border p-1 rounded text-sm">
                             <select v-model="variantBuilder.master_recipe_id" class="flex-1 border p-1 rounded text-xs bg-white">
                                <option :value="null">Рецепт...</option>
                                <option v-for="r in recipes" :key="r.id" :value="r.id">{{ r.name }}</option>
                             </select>
                        </div>

                         <div class="bg-teal-50/50 p-2 rounded border border-teal-100">
                             <label class="text-[10px] uppercase font-bold text-teal-600">Матеріали варіанту (напр. стакан)</label>
                             <div class="flex gap-1 mb-1">
                                 <select v-model="tempVariantConsumable.consumable_id" class="flex-1 border p-1 rounded text-[10px] bg-white h-7">
                                     <option value="">Матеріал...</option>
                                     <option v-for="c in consumables" :key="c.id" :value="c.id">{{ c.name }}</option>
                                 </select>
                                 <input v-model="tempVariantConsumable.quantity" type="number" class="w-10 border p-1 rounded text-[10px] h-7" placeholder="Qty">
                                 <button @click="addConsumableToVariant" class="bg-teal-500 text-white w-7 h-7 rounded hover:bg-teal-600 text-xs">+</button>
                             </div>
                             <div class="flex flex-wrap gap-1">
                                 <span v-for="(vc, vi) in variantBuilder.consumables" :key="vi" class="bg-white border text-[10px] px-1 rounded flex items-center gap-1">
                                     {{ vc.name }} x{{ vc.quantity }} <button @click="removeConsumableFromVariant(vi)" class="text-red-500 font-bold">&times;</button>
                                 </span>
                             </div>
                         </div>

                        <button @click="addVariant" class="w-full bg-purple-200 text-purple-800 text-sm font-bold py-1 rounded hover:bg-purple-300">Додати варіант</button>
                    </div>
                </div>

                <button @click="saveProduct" class="w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 shadow-lg">Зберегти</button>
            </div>
       </div>
    </div>
    
    <div v-if="activeTab === 'ingredients'" class="grid grid-cols-1 lg:grid-cols-2 gap-8"><div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit"><h3 class="font-bold mb-6 text-gray-700 border-b pb-2">🌱 Новий інгредієнт</h3><div class="space-y-5"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва інгредієнта</label><input v-model="newIngredient.name" placeholder="Напр. Кава в зернах" class="border p-2 rounded-lg w-full bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition"></div><div class="grid grid-cols-2 gap-4"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Одиниця виміру</label><select v-model="newIngredient.unit_id" class="border p-2 rounded-lg w-full bg-white h-[42px]"><option value="" disabled>Оберіть...</option><option v-for="u in units" :key="u.id" :value="u.id">{{u.name}} ({{u.symbol}})</option></select></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Собівартість (₴/од)</label><input v-model="newIngredient.cost_per_unit" type="number" placeholder="0.00" class="border p-2 rounded-lg w-full"></div></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Початковий залишок на складі</label><input v-model="newIngredient.stock_quantity" type="number" placeholder="0" class="border p-2 rounded-lg w-full"></div><button @click="createIngredient" class="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition mt-2"><i class="fas fa-plus mr-2"></i> Додати в базу</button></div></div><div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100"><table class="w-full text-sm text-left"><thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Назва</th><th class="p-4 text-right">Залишок</th><th class="p-4 text-center">Дії</th></tr></thead><tbody class="divide-y divide-gray-100"><tr v-for="i in ingredients" :key="i.id" class="hover:bg-gray-50"><td class="p-4 font-bold text-gray-700">{{ i.name }}<div class="text-xs text-gray-400 font-normal">Собівартість: {{ i.cost_per_unit }} ₴/{{ i.unit?.symbol }}</div></td><td class="p-4 text-right font-mono text-lg" :class="i.stock_quantity > 0 ? 'text-green-600' : 'text-red-500'">{{ i.stock_quantity }} <span class="text-xs text-gray-400 font-sans">{{ i.unit?.symbol }}</span></td><td class="p-4 text-center"><div class="flex justify-center gap-2"><button @click="openEditIngModal(i)" class="text-gray-400 hover:text-blue-500 px-2"><i class="fas fa-pen"></i></button><button @click="deleteIngredient(i.id)" class="text-gray-400 hover:text-red-500 px-2"><i class="fas fa-trash"></i></button></div></td></tr></tbody></table></div></div>
     
    <div v-if="activeTab === 'consumables'" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit">
            <h3 class="font-bold mb-6 text-gray-700 border-b pb-2">📦 Новий матеріал</h3>
            <div class="space-y-5">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва</label>
                    <input v-model="newConsumable.name" placeholder="Напр. Стакан 300мл" class="border p-2 rounded-lg w-full">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Одиниця</label>
                        <select v-model="newConsumable.unit_id" class="border p-2 rounded-lg w-full bg-white h-[42px]">
                            <option value="" disabled>Оберіть...</option>
                            <option v-for="u in units" :key="u.id" :value="u.id">{{u.name}} ({{u.symbol}})</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ціна (₴/од)</label>
                        <input v-model="newConsumable.cost_per_unit" type="number" class="border p-2 rounded-lg w-full">
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Залишок</label>
                    <input v-model="newConsumable.stock_quantity" type="number" class="border p-2 rounded-lg w-full">
                </div>
                <button @click="createConsumable" class="bg-teal-600 hover:bg-teal-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-teal-200 transition mt-2">Додати</button>
            </div>
        </div>
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
                    <tr><th class="p-4">Назва</th><th class="p-4 text-right">Залишок</th><th class="p-4 text-center">Дії</th></tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="c in consumables" :key="c.id" class="hover:bg-gray-50">
                        <td class="p-4 font-bold text-gray-700">{{ c.name }}
                            <div class="text-xs text-gray-400 font-normal">{{ c.cost_per_unit }} ₴/{{ c.unit?.symbol }}</div>
                        </td>
                        <td class="p-4 text-right font-mono text-lg" :class="c.stock_quantity > 10 ? 'text-green-600' : 'text-red-500'">
                            {{ c.stock_quantity }} <span class="text-xs text-gray-400 font-sans">{{ c.unit?.symbol }}</span>
                        </td>
                        <td class="p-4 text-center">
                            <button @click="deleteConsumable(c.id)" class="text-gray-400 hover:text-red-500 px-2"><i class="fas fa-trash"></i></button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div v-if="activeTab === 'units'" class="grid grid-cols-1 lg:grid-cols-2 gap-8"><div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit"><h3 class="font-bold mb-4 text-gray-700">📏 Створити одиницю виміру</h3><div class="space-y-3"><input v-model="newUnit.name" placeholder="Назва (напр. Грами)" class="border p-2 rounded w-full"><input v-model="newUnit.symbol" placeholder="Символ (напр. г)" class="border p-2 rounded w-full"><button @click="createUnit" class="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition">Зберегти</button></div></div><div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100"><table class="w-full text-sm text-left"><thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Назва</th><th class="p-4 text-right">Символ</th></tr></thead><tbody class="divide-y divide-gray-100"><tr v-for="u in units" :key="u.id" class="hover:bg-gray-50"><td class="p-4 font-bold text-gray-700">{{ u.name }}</td><td class="p-4 text-right font-mono">{{ u.symbol }}</td></tr></tbody></table></div></div>
    <div v-if="activeTab === 'categories'" class="grid grid-cols-1 lg:grid-cols-3 gap-8"><div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit"><h3 class="font-bold mb-4 text-gray-700">📂 Нова категорія</h3><div class="space-y-4"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Назва</label><input v-model="newCategory.name" class="border p-2 rounded w-full"></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Код</label><input v-model="newCategory.slug" class="border p-2 rounded w-full font-mono text-sm"></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Колір</label><div class="flex items-center gap-2"><input v-model="newCategory.color" type="color" class="h-10 w-16 border rounded cursor-pointer"><span class="text-sm text-gray-600">{{ newCategory.color }}</span></div></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Батько</label><select v-model="newCategory.parent_id" class="border p-2 rounded w-full bg-white"><option value="">(Немає)</option><option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option></select></div><button @click="createCategory" class="bg-blue-600 text-white w-full py-3 rounded-xl font-bold hover:bg-blue-700 shadow-lg mt-2">Створити</button></div></div><div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"><table class="w-full text-sm text-left"><thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Колір</th><th class="p-4">Назва</th><th class="p-4">Код</th><th class="p-4">Батько</th></tr></thead><tbody class="divide-y divide-gray-100"><tr v-for="c in categories" :key="c.id" class="hover:bg-gray-50"><td class="p-4"><div class="w-8 h-8 rounded-lg shadow-sm border border-gray-200" :style="{ backgroundColor: c.color || '#fff' }"></div></td><td class="p-4 font-bold text-gray-800 text-lg">{{ c.name }}</td><td class="p-4 font-mono text-gray-500">{{ c.slug }}</td><td class="p-4"><span v-if="c.parent_id" class="bg-blue-50 text-blue-600 px-2 py-1 rounded text-xs font-bold">{{ getParentName(c.parent_id) }}</span><span v-else class="text-gray-300 text-xs">-</span></td></tr></tbody></table></div></div>
    
    <div v-if="showEditIngModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm"><div class="bg-white p-6 rounded-2xl shadow-2xl w-96"><h3 class="text-xl font-bold mb-4">Редагувати інгредієнт</h3><div class="space-y-3"><div><label class="text-xs font-bold text-gray-500 uppercase">Назва</label><input v-model="editIngData.name" class="border p-2 rounded w-full"></div><div><label class="text-xs font-bold text-gray-500 uppercase">Одиниця</label><select v-model="editIngData.unit_id" class="border p-2 rounded w-full bg-white"><option v-for="u in units" :key="u.id" :value="u.id">{{u.name}} ({{u.symbol}})</option></select></div><div><label class="text-xs font-bold text-gray-500 uppercase">Ціна</label><input v-model="editIngData.cost_per_unit" type="number" class="border p-2 rounded w-full"></div><div class="flex gap-2 mt-4"><button @click="showEditIngModal=false" class="flex-1 py-2 text-gray-500 font-bold hover:bg-gray-100 rounded-lg">Скасувати</button><button @click="updateIngredient" class="flex-1 py-2 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700">Зберегти</button></div></div></div></div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-in; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>