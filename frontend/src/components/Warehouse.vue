<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('products') 
const categories = ref([]); const units = ref([]); const ingredients = ref([]); const products = ref([]);
const loading = ref(false)

// Forms for simple data
const newCategory = ref({ name: '', slug: '' })
const newUnit = ref({ name: '', symbol: '' })
const newIngredient = ref({ name: '', unit_id: '', cost_per_unit: 0, stock_quantity: 0 })

// --- СКЛАДНИЙ ТОВАР ---
const isVariantMode = ref(false) // Toggle: Simple vs Variant
const newProduct = ref({
  name: '', description: '', category_id: '',
  price: 0, // Тільки для простого
  recipe: [], // Тільки для простого
  variants: [], // Тільки для складного
  modifier_groups: [] // Для обох
})

// Тимчасові змінні для UI конструктора варіантів
const variantBuilder = ref({ name: '', price: 0, recipe: [] })
const modGroupBuilder = ref({ name: '', is_required: false, modifiers: [] })

// --- ЗАВАНТАЖЕННЯ ---
const fetchData = async () => {
  loading.value = true
  try {
    const [c, u, i, p] = await Promise.all([
      fetch('/api/categories/').then(r=>r.json()),
      fetch('/api/units/').then(r=>r.json()),
      fetch('/api/ingredients/').then(r=>r.json()),
      fetch('/api/products/').then(r=>r.json())
    ])
    categories.value = c; units.value = u; ingredients.value = i; products.value = p;
  } catch (e) { console.error(e) } finally { loading.value = false }
}

// --- ЛОГІКА РЕЦЕПТІВ (Helper) ---
const addIngToRecipe = (recipeArray) => recipeArray.push({ ingredient_id: '', quantity: 0 })
const removeIngFromRecipe = (recipeArray, idx) => recipeArray.splice(idx, 1)

// --- ЛОГІКА ВАРІАНТІВ ---
const addVariant = () => {
    if(!variantBuilder.value.name || !variantBuilder.value.price) return alert("Вкажіть назву та ціну варіанту")
    // Копіюємо дані
    newProduct.value.variants.push({
        name: variantBuilder.value.name,
        price: variantBuilder.value.price,
        recipe: JSON.parse(JSON.stringify(variantBuilder.value.recipe))
    })
    // Очищаємо білдер
    variantBuilder.value = { name: '', price: 0, recipe: [] }
}
const removeVariant = (idx) => newProduct.value.variants.splice(idx, 1)

// --- ЛОГІКА МОДИФІКАТОРІВ ---
const addModifierOption = () => modGroupBuilder.value.modifiers.push({ name: '', price_change: 0 })
const addModGroup = () => {
    if(!modGroupBuilder.value.name) return
    newProduct.value.modifier_groups.push(JSON.parse(JSON.stringify(modGroupBuilder.value)))
    modGroupBuilder.value = { name: '', is_required: false, modifiers: [] }
}

// --- ЗБЕРЕЖЕННЯ ТОВАРУ ---
const createProduct = async () => {
    const p = newProduct.value
    if (!p.name || !p.category_id) return alert("Вкажіть назву та категорію!")
    
    // Формуємо payload
    const payload = {
        name: p.name,
        description: p.description,
        category_id: p.category_id,
        has_variants: isVariantMode.value,
        price: isVariantMode.value ? 0 : p.price,
        // Очищаємо пусті рецепти
        recipe: p.recipe.filter(r => r.ingredient_id && r.quantity > 0),
        variants: p.variants.map(v => ({
            ...v,
            recipe: v.recipe.filter(r => r.ingredient_id && r.quantity > 0)
        })),
        modifier_groups: p.modifier_groups
    }

    const res = await fetch('/api/products/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    
    if(res.ok) {
        alert("Товар створено!"); fetchData();
        // Reset form
        newProduct.value = { name: '', description: '', category_id: '', price: 0, recipe: [], variants: [], modifier_groups: [] }
    } else {
        alert("Помилка створення")
    }
}

// Прості CRUD функції для категорій/інгредієнтів залишаємо такі ж, як були (для економії місця не дублюю, якщо вони в тебе є)
// Але оскільки я даю повний файл, то додам базові.
const createCategory = async () => { await fetch('/api/categories/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newCategory.value)}); fetchData() }
const createIngredient = async () => { await fetch('/api/ingredients/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newIngredient.value)}); fetchData() }

onMounted(fetchData)
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    <div class="flex justify-between items-center mb-8">
      <h2 class="text-3xl font-bold text-gray-800">📦 Конструктор Меню</h2>
      <button @click="fetchData" class="text-blue-600 hover:bg-blue-50 p-2 rounded-full"><i class="fas fa-sync-alt"></i></button>
    </div>

    <div class="flex space-x-1 bg-gray-200 p-1 rounded-xl w-fit mb-8">
      <button @click="activeTab='products'" :class="activeTab==='products'?'bg-white text-purple-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Товари</button>
      <button @click="activeTab='ingredients'" :class="activeTab==='ingredients'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Склад</button>
      <button @click="activeTab='categories'" :class="activeTab==='categories'?'bg-white text-blue-600 shadow-sm':''" class="px-6 py-2 rounded-lg font-bold transition-all">Категорії</button>
    </div>

    <div v-if="activeTab === 'products'" class="grid grid-cols-1 xl:grid-cols-3 gap-8">
      
      <div class="xl:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <table class="w-full text-left">
           <thead class="bg-gray-50 text-gray-500 uppercase text-xs"><tr><th class="p-4">Назва</th><th class="p-4">Тип</th><th class="p-4 text-right">Ціна</th></tr></thead>
           <tbody>
             <tr v-for="p in products" :key="p.id" class="border-b hover:bg-gray-50">
               <td class="p-4 font-bold">{{ p.name }} <span class="text-gray-400 font-normal text-xs ml-2">{{ p.category?.name }}</span></td>
               <td class="p-4 text-xs uppercase font-bold" :class="p.has_variants ? 'text-purple-600':'text-gray-500'">
                  {{ p.has_variants ? 'Варіанти' : 'Простий' }}
               </td>
               <td class="p-4 text-right font-mono">
                  {{ p.has_variants && p.variants.length > 0 ? `${p.variants[0].price} - ...` : p.price }} ₴
               </td>
             </tr>
           </tbody>
        </table>
      </div>

      <div class="bg-white p-6 rounded-2xl shadow-sm border border-purple-100 border-2 h-fit">
        <h3 class="text-lg font-bold mb-4 text-purple-700"><i class="fas fa-plus-circle"></i> Новий товар</h3>
        
        <div class="space-y-4">
            <input v-model="newProduct.name" type="text" placeholder="Назва (напр. Кава Delicate)" class="w-full border p-2 rounded">
            <select v-model="newProduct.category_id" class="w-full border p-2 rounded bg-white">
                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>

            <div class="flex items-center gap-3 bg-gray-100 p-2 rounded-lg">
                <span class="text-xs font-bold uppercase text-gray-500 ml-2">Тип:</span>
                <button @click="isVariantMode=false" :class="!isVariantMode ? 'bg-white shadow text-gray-800':'text-gray-400'" class="flex-1 py-1 rounded text-sm font-bold transition">Простий</button>
                <button @click="isVariantMode=true" :class="isVariantMode ? 'bg-white shadow text-purple-600':'text-gray-400'" class="flex-1 py-1 rounded text-sm font-bold transition">З варіантами</button>
            </div>

            <div v-if="!isVariantMode" class="space-y-3 animate-fade-in">
                <input v-model="newProduct.price" type="number" placeholder="Ціна (₴)" class="w-full border p-2 rounded font-bold text-right">
                
                <div class="border-t border-dashed pt-2">
                    <label class="text-xs font-bold text-gray-400 uppercase">Рецепт</label>
                    <div v-for="(row, idx) in newProduct.recipe" :key="idx" class="flex gap-2 mt-1">
                        <select v-model="row.ingredient_id" class="flex-1 text-sm border rounded"><option v-for="i in ingredients" :key="i.id" :value="i.id">{{i.name}}</option></select>
                        <input v-model="row.quantity" type="number" step="0.001" placeholder="Кіл" class="w-16 text-sm border rounded">
                        <button @click="removeIngFromRecipe(newProduct.recipe, idx)" class="text-red-400"><i class="fas fa-times"></i></button>
                    </div>
                    <button @click="addIngToRecipe(newProduct.recipe)" class="text-xs text-blue-500 font-bold mt-1">+ Інгредієнт</button>
                </div>
            </div>

            <div v-if="isVariantMode" class="bg-purple-50 p-3 rounded-xl border border-purple-100 animate-fade-in">
                <label class="text-xs font-bold text-purple-600 uppercase">Додати варіант</label>
                <div class="flex gap-2 mt-2 mb-2">
                    <input v-model="variantBuilder.name" placeholder="Назва (250г)" class="flex-1 text-sm border p-1 rounded">
                    <input v-model="variantBuilder.price" type="number" placeholder="Ціна" class="w-20 text-sm border p-1 rounded">
                </div>
                <div class="bg-white p-2 rounded border border-purple-100 mb-2">
                     <div v-for="(row, idx) in variantBuilder.recipe" :key="idx" class="flex gap-1 mb-1">
                        <select v-model="row.ingredient_id" class="flex-1 text-xs border rounded"><option v-for="i in ingredients" :key="i.id" :value="i.id">{{i.name}}</option></select>
                        <input v-model="row.quantity" type="number" step="0.001" class="w-12 text-xs border rounded">
                        <button @click="removeIngFromRecipe(variantBuilder.recipe, idx)" class="text-red-400 text-xs px-1">x</button>
                     </div>
                     <button @click="addIngToRecipe(variantBuilder.recipe)" class="text-xs text-purple-400">+ Склад</button>
                </div>
                <button @click="addVariant" class="w-full bg-purple-200 text-purple-800 text-sm font-bold py-1 rounded hover:bg-purple-300">Додати варіант</button>

                <div class="mt-3 space-y-1">
                    <div v-for="(v, idx) in newProduct.variants" :key="idx" class="flex justify-between text-sm bg-white p-2 rounded shadow-sm">
                        <span>{{ v.name }} ({{ v.price }} ₴)</span>
                        <button @click="removeVariant(idx)" class="text-red-400"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
            </div>

            <div class="border-t pt-4">
                 <label class="text-xs font-bold text-gray-400 uppercase">Модифікатори (Помол, тощо)</label>
                 <div class="mt-2 bg-gray-50 p-2 rounded border">
                    <input v-model="modGroupBuilder.name" placeholder="Назва групи (Помол)" class="w-full text-sm border p-1 rounded mb-1">
                    <div class="flex items-center gap-2 mb-2">
                        <input type="checkbox" v-model="modGroupBuilder.is_required" id="req"><label for="req" class="text-xs">Обов'язково</label>
                    </div>
                    <div v-for="(m, idx) in modGroupBuilder.modifiers" :key="idx" class="flex gap-1 mb-1">
                        <input v-model="m.name" placeholder="Опція (Еспресо)" class="flex-1 text-xs border rounded p-1">
                        <input v-model="m.price_change" type="number" placeholder="+₴" class="w-12 text-xs border rounded p-1">
                    </div>
                    <div class="flex gap-2">
                        <button @click="addModifierOption" class="text-xs text-blue-500">+ Опція</button>
                        <button @click="addModGroup" class="ml-auto text-xs bg-gray-200 px-2 rounded font-bold">Зберегти групу</button>
                    </div>
                 </div>
                 <div class="mt-2 text-xs text-gray-500" v-for="(g, idx) in newProduct.modifier_groups" :key="idx">
                    • {{ g.name }} ({{ g.modifiers.length }} опцій)
                 </div>
            </div>

            <button @click="createProduct" class="w-full bg-green-600 text-white py-3 rounded-xl font-bold hover:bg-green-700 shadow-lg mt-4">Створити товар</button>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'ingredients'" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-2xl shadow-sm">
             <h3 class="font-bold mb-4">Створити інгредієнт</h3>
             <input v-model="newIngredient.name" placeholder="Назва" class="border p-2 rounded w-full mb-2">
             <select v-model="newIngredient.unit_id" class="border p-2 rounded w-full mb-2"><option v-for="u in units" :value="u.id">{{u.name}}</option></select>
             <button @click="createIngredient" class="bg-orange-500 text-white w-full py-2 rounded font-bold">Зберегти</button>
        </div>
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
            <table class="w-full text-sm text-left">
                <tr v-for="i in ingredients" :key="i.id" class="border-b"><td class="p-3">{{ i.name }}</td><td class="p-3 text-right">{{ i.stock_quantity }}</td></tr>
            </table>
        </div>
    </div>
    
    <div v-if="activeTab === 'categories'" class="p-6 bg-white rounded-2xl">
        <input v-model="newCategory.name" placeholder="Нова категорія" class="border p-2 rounded mr-2">
        <input v-model="newCategory.slug" placeholder="slug" class="border p-2 rounded mr-2">
        <button @click="createCategory" class="bg-blue-600 text-white px-4 py-2 rounded">Add</button>
        <div class="mt-4"><span v-for="c in categories" :key="c.id" class="mr-2 bg-gray-100 px-2 py-1 rounded">{{c.name}}</span></div>
    </div>

  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-in; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>