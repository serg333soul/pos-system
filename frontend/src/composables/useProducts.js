import { ref, computed } from 'vue'
import axios from 'axios'
import { useWarehouse } from '@/composables/useWarehouse'

// Глобальний стан
const newProduct = ref({
    name: '', category_id: null, price: 0, has_variants: false,
    master_recipe_id: null, output_weight: 0,
    track_stock: false, stock_quantity: 0,
    consumables: [], variants: [], process_group_ids: []
})

const editingId = ref(null)
const isEditing = ref(false)
const productSearch = ref('')

// --- НОВЕ: Стан редагування варіанту ---
const editingVariantIndex = ref(null) // null = режим створення, число = індекс варіанту

// Тимчасові змінні
const tempProductConsumable = ref({ consumable_id: "", quantity: 1 })
const tempVariantConsumable = ref({ consumable_id: "", quantity: 1 })
const tempVariantIngredient = ref({ ingredient_id: "", quantity: 0 })

const variantBuilder = ref({
    name: '', price: 0, master_recipe_id: null, 
    output_weight: 0, stock_quantity: 0, 
    consumables: [], ingredients: []
})

export function useProducts() {
    const warehouse = useWarehouse()
    const products = warehouse?.products || ref([])
    const consumables = warehouse?.consumables || ref([])
    const ingredients = warehouse?.ingredients || ref([])
    const fetchWarehouseData = warehouse?.fetchWarehouseData || (async ()=>{})

    const filteredProducts = computed(() => {
        if (!products.value) return []
        if (!productSearch.value) return products.value
        return products.value.filter(p => p.name.toLowerCase().includes(productSearch.value.toLowerCase()))
    })

    const fetchProducts = async () => { await fetchWarehouseData() }

    const saveProduct = async () => {
        if (!newProduct.value.name) return alert("Вкажіть назву товару!")
        
        const cleanPrice = newProduct.value.has_variants ? 0 : (parseFloat(newProduct.value.price) || 0)
        const cleanWeight = parseFloat(newProduct.value.output_weight) || 0
        const cleanStock = parseFloat(newProduct.value.stock_quantity) || 0
        
        const payload = {
            ...newProduct.value,
            category_id: newProduct.value.category_id || null,
            master_recipe_id: newProduct.value.master_recipe_id || null,
            price: cleanPrice,
            output_weight: cleanWeight,
            stock_quantity: cleanStock,
            variants: newProduct.value.has_variants ? newProduct.value.variants : [] 
        }

        try {
            const url = isEditing.value 
                ? `http://localhost:8001/products/${editingId.value}`
                : 'http://localhost:8001/products/'
            const method = isEditing.value ? 'put' : 'post'

            await axios[method](url, payload)
            await fetchProducts()
            resetForm()
            return true
        } catch (err) {
            console.error("Save error:", err)
            alert("Помилка збереження")
            return false
        }
    }

    const deleteProduct = async (id) => {
        if(!confirm("Видалити?")) return
        try {
            await axios.delete(`http://localhost:8001/products/${id}`)
            await fetchProducts()
        } catch(e) { alert("Помилка видалення") }
    }

    const resetForm = () => {
        isEditing.value = false
        editingId.value = null
        editingVariantIndex.value = null // Скидаємо редагування варіанту
        newProduct.value = {
            name: '', category_id: null, price: 0, has_variants: false,
            master_recipe_id: null, output_weight: 0,
            track_stock: false, stock_quantity: 0,
            consumables: [], variants: [], process_group_ids: []
        }
        resetVariantBuilder()
    }

    const resetVariantBuilder = () => {
        variantBuilder.value = { name: '', price: 0, master_recipe_id: null, output_weight: 0, stock_quantity: 0, consumables: [], ingredients: [] }
        editingVariantIndex.value = null
    }

    const prepareEdit = (p) => {
        isEditing.value = true
        editingId.value = p.id
        const copy = JSON.parse(JSON.stringify(p))
        if (copy.variants) {
            copy.variants.forEach(v => {
                if(v.consumables) v.consumables.forEach(c => c.name = c.consumable_name || c.name)
                if(v.ingredients) v.ingredients.forEach(i => i.name = i.ingredient_name || i.name)
            })
        }
        if (copy.consumables) copy.consumables.forEach(c => c.name = c.consumable_name || c.name)
        newProduct.value = copy
    }

    // --- ЛОГІКА ВАРІАНТІВ (Оновлена) ---
    
    // 1. Функція збереження (Додавання АБО Оновлення)
    const saveVariant = () => {
        if(!variantBuilder.value.name) return alert("Вкажіть назву варіанту")
        
        const variantData = JSON.parse(JSON.stringify(variantBuilder.value))

        if (editingVariantIndex.value !== null) {
            // ОНОВЛЕННЯ існуючого
            newProduct.value.variants[editingVariantIndex.value] = variantData
        } else {
            // ДОДАВАННЯ нового
            newProduct.value.variants.push(variantData)
        }
        resetVariantBuilder()
    }

    // 2. Функція підготовки до редагування
    const editVariant = (index) => {
        editingVariantIndex.value = index
        // Копіюємо дані варіанту назад у форму
        variantBuilder.value = JSON.parse(JSON.stringify(newProduct.value.variants[index]))
    }

    // 3. Скасування редагування
    const cancelVariantEdit = () => {
        resetVariantBuilder()
    }

    const removeVariant = (i) => {
        newProduct.value.variants.splice(i, 1)
        if (editingVariantIndex.value === i) resetVariantBuilder()
    }

    // Інші методи (матеріали/інгредієнти)
    const addProductConsumable = () => {
        if(!tempProductConsumable.value.consumable_id) return
        const c = consumables.value.find(x => x.id === tempProductConsumable.value.consumable_id)
        newProduct.value.consumables.push({ ...tempProductConsumable.value, name: c?.name || '???' })
        tempProductConsumable.value.quantity = 1
    }
    const removeProductConsumable = (i) => newProduct.value.consumables.splice(i, 1)

    const addVariantConsumable = () => {
        if(!tempVariantConsumable.value.consumable_id) return
        const c = consumables.value.find(x => x.id === tempVariantConsumable.value.consumable_id)
        variantBuilder.value.consumables.push({ ...tempVariantConsumable.value, name: c?.name || '???' })
        tempVariantConsumable.value.quantity = 1
    }
    const removeVariantConsumable = (i) => variantBuilder.value.consumables.splice(i, 1)

    const addIngredientToVariant = () => {
        if(!tempVariantIngredient.value.ingredient_id) return
        const i = ingredients.value.find(x => x.id === tempVariantIngredient.value.ingredient_id)
        variantBuilder.value.ingredients.push({ ...tempVariantIngredient.value, name: i?.name || '???' })
        tempVariantIngredient.value.quantity = 0
    }
    const removeIngredientFromVariant = (i) => variantBuilder.value.ingredients.splice(i, 1)

    return {
        newProduct, isEditing, editingId, productSearch, filteredProducts,
        variantBuilder, tempProductConsumable, tempVariantConsumable, tempVariantIngredient,
        // Експортуємо нові змінні та методи
        editingVariantIndex, saveVariant, editVariant, cancelVariantEdit,
        
        fetchProducts, saveProduct, deleteProduct, resetForm, prepareEdit,
        removeVariant,
        addProductConsumable, removeProductConsumable,
        addVariantConsumable, removeVariantConsumable,
        addIngredientToVariant, removeIngredientFromVariant
    }
}