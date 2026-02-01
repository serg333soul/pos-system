import { ref, computed } from 'vue'
import axios from 'axios'
import { useWarehouse } from '@/composables/useWarehouse'

// Глобальний стан
const newProduct = ref({
    name: '', category_id: null, price: 0, has_variants: false,
    master_recipe_id: null, output_weight: 0,
    track_stock: false, stock_quantity: 0,
    consumables: [], variants: [], process_group_ids: [],
    // 👇 Додані поля для відображення (приходять з беку)
    cost_price: 0, margin: 0 
})

const editingId = ref(null)
const isEditing = ref(false)
const productSearch = ref('')

// Стан редагування варіанту
const editingVariantIndex = ref(null) 

// Тимчасові змінні
const tempProductConsumable = ref({ consumable_id: "", quantity: 1 })
const tempVariantConsumable = ref({ consumable_id: "", quantity: 1 })
const tempVariantIngredient = ref({ ingredient_id: "", quantity: 0 })

const variantBuilder = ref({
    name: '', price: 0, sku: '', // 👈 SKU тепер тут
    master_recipe_id: null, 
    output_weight: 0, stock_quantity: 0, 
    consumables: [], ingredients: [],
    // 👇 Додані поля для відображення
    cost_price: 0, margin: 0 
})

export function useProducts() {
    const warehouse = useWarehouse()
    const products = warehouse?.products || ref([])
    const consumables = warehouse?.consumables || ref([])
    const ingredients = warehouse?.ingredients || ref([]) // Треба для роботи з інгредієнтами

    // --- CRUD Товарів ---
    const fetchProducts = async () => {
        if (warehouse && warehouse.fetchProducts) {
            await warehouse.fetchProducts()
        }
    }

    const resetForm = () => {
        newProduct.value = {
            name: '', category_id: null, price: 0, has_variants: false,
            master_recipe_id: null, output_weight: 0,
            track_stock: false, stock_quantity: 0,
            consumables: [], variants: [], process_group_ids: [],
            cost_price: 0, margin: 0
        }
        variantBuilder.value = {
            name: '', price: 0, sku: '',
            master_recipe_id: null, output_weight: 0, stock_quantity: 0, 
            consumables: [], ingredients: [],
            cost_price: 0, margin: 0
        }
        isEditing.value = false
        editingId.value = null
        editingVariantIndex.value = null
    }

    const prepareEdit = (product) => {
        // Копіюємо об'єкт, щоб не змінювати його в списку до збереження
        newProduct.value = JSON.parse(JSON.stringify(product))
        editingId.value = product.id
        isEditing.value = true
        // Якщо process_group_ids не прийшли (старий формат), ініціалізуємо
        if (!newProduct.value.process_group_ids) newProduct.value.process_group_ids = []
    }

    const saveProduct = async () => {
        try {
            // Формуємо payload
            const payload = {
                ...newProduct.value,
                // Переконуємось, що числа є числами
                price: parseFloat(newProduct.value.price),
                stock_quantity: parseFloat(newProduct.value.stock_quantity),
                output_weight: parseFloat(newProduct.value.output_weight),
            }

            if (isEditing.value) {
                await axios.put(`/api/products/${editingId.value}`, payload)
            } else {
                await axios.post('/api/products/', payload)
            }
            
            await fetchProducts()
            resetForm()
            return true
        } catch (e) {
            console.error("Помилка збереження товару:", e)
            alert("Помилка збереження: " + (e.response?.data?.detail || e.message))
            return false
        }
    }

    const deleteProduct = async (id) => {
        if (!confirm('Видалити цей товар?')) return
        try {
            await axios.delete(`/api/products/${id}`)
            await fetchProducts()
        } catch (e) {
            console.error(e)
            alert("Не вдалося видалити товар")
        }
    }

    // --- Варіанти ---
    const saveVariant = () => {
        const v = JSON.parse(JSON.stringify(variantBuilder.value))
        
        // Валідація вже на рівні UI, тут просто додаємо
        if (editingVariantIndex.value !== null) {
            newProduct.value.variants[editingVariantIndex.value] = v
            editingVariantIndex.value = null
        } else {
            newProduct.value.variants.push(v)
        }
        
        // Очищення білдера (але SKU очищаємо, щоб не дублювати)
        variantBuilder.value = {
            name: '', price: 0, sku: '',
            master_recipe_id: null, output_weight: 0, stock_quantity: 0, 
            consumables: [], ingredients: [],
            cost_price: 0, margin: 0
        }
    }

    const editVariant = (index) => {
        variantBuilder.value = JSON.parse(JSON.stringify(newProduct.value.variants[index]))
        editingVariantIndex.value = index
    }

    const removeVariant = (index) => {
        newProduct.value.variants.splice(index, 1)
        if (editingVariantIndex.value === index) {
            editingVariantIndex.value = null
            // Очистити форму
            variantBuilder.value = {
                name: '', price: 0, sku: '',
                master_recipe_id: null, output_weight: 0, stock_quantity: 0, 
                consumables: [], ingredients: [], cost_price: 0, margin: 0
            }
        }
    }

    const cancelVariantEdit = () => {
        editingVariantIndex.value = null
        variantBuilder.value = {
            name: '', price: 0, sku: '',
            master_recipe_id: null, output_weight: 0, stock_quantity: 0, 
            consumables: [], ingredients: [], cost_price: 0, margin: 0
        }
    }

    // --- Допоміжні (Consumables / Ingredients) ---
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

    // --- Фільтрація ---
    const filteredProducts = computed(() => {
        if (!productSearch.value) return products.value
        const s = productSearch.value.toLowerCase()
        return products.value.filter(p => p.name.toLowerCase().includes(s))
    })

    return {
        newProduct, isEditing, editingId, productSearch, filteredProducts,
        variantBuilder, tempProductConsumable, tempVariantConsumable, tempVariantIngredient,
        editingVariantIndex, saveVariant, editVariant, cancelVariantEdit,
        fetchProducts, saveProduct, deleteProduct, resetForm, prepareEdit,
        removeVariant,
        addProductConsumable, removeProductConsumable,
        addVariantConsumable, removeVariantConsumable,
        addIngredientToVariant, removeIngredientFromVariant
    }
}