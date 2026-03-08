import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { useWarehouse } from '@/composables/useWarehouse'

// Глобальний стан
const newProduct = ref({
    name: '', category_id: null, price: 0, has_variants: false,
    master_recipe_id: null, output_weight: 0,
    track_stock: false, stock_quantity: 0,
    consumables: [], ingredients: [], variants: [], process_group_ids: [],
    // 👇 Додані поля для відображення (приходять з беку)
    cost_price: 0, margin: 0 
})

const editingId = ref(null)
const isEditing = ref(false)
const productSearch = ref('')
const isSaving = ref(false); // Запобіжник

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
    const calculatedStock = ref(null) // Змінна для збереження результату
    const variantCalculatedCost = ref(0) // Для збереження розрахункової собівартості варіанту
    
    const fetchCalculatedStock = async (productId, variantId) => {
        calculatedStock.value = null;
        if (!productId || !variantId) return;
    
        try {
            // Додай /api на початку шляху 🔥
            const res = await axios.get(`/api/products/${productId}/variants/${variantId}/calculated-stock?t=${Date.now()}`);
        
            calculatedStock.value = res.data.calculated_stock;
            console.log("✅ Отримано розрахунковий залишок:", res.data.calculated_stock);
        } catch (err) {
            console.error("Помилка розрахунку залишку:", err);
            calculatedStock.value = 0;
        }
    }
    
    const fetchVariantCost = async () => {
        // Формуємо об'єкт для калькулятора [6, 7]
        const payload = {
            master_recipe_id: variantBuilder.value.master_recipe_id,
            output_weight: variantBuilder.value.output_weight || 0,
            ingredients: variantBuilder.value.ingredients,
            consumables: variantBuilder.value.consumables
        };

        try {
            const res = await axios.post('/api/products/calculate-cost', payload);
            variantCalculatedCost.value = res.data.total_cost;
            
            // Оновлюємо дані в самому білдері для збереження
            variantBuilder.value.cost_price = res.data.total_cost;
        } catch (err) {
            console.error("Помилка розрахунку собівартості варіанту", err);
        }
    }

    watch(
        () => [
            variantBuilder.value.master_recipe_id, 
            variantBuilder.value.output_weight,
            variantBuilder.value.ingredients,
            variantBuilder.value.consumables
        ],
        () => {
            fetchVariantCost();
        },
        { deep: true }
    )

    const generateSKU = () => {
        // Перевіряємо, чи є базова інформація для генерації
        const productName = newProduct.value.name || 'PROD';
        const variantName = variantBuilder.value.name || 'VAR';
        
        // Беремо перші 3 літери назви товару та варіанту в верхньому регістрі
        const pPart = productName.substring(0, 3).toUpperCase().replace(/\s/g, '');
        const vPart = variantName.substring(0, 3).toUpperCase().replace(/\s/g, '');
        
        // Генеруємо випадкове 4-значне число
        const randomPart = Math.floor(1000 + Math.random() * 9000);
        
        // Формуємо SKU
        variantBuilder.value.sku = `${pPart}-${vPart}-${randomPart}`;
        
        console.log("🆕 Згенеровано новий SKU:", variantBuilder.value.sku);
    }

    // 🔥 Додаємо автоматичне оновлення розрахунку при зміні залишків інгредієнтів
    watch(() => warehouse.ingredients, () => {
        // Якщо зараз відкрита форма редагування конкретного варіанту
        if     (editingId.value && variantBuilder.value.id) {
            console.log("🔄 Склад змінився, перераховую залишок варіанту...");
            fetchCalculatedStock(editingId.value, variantBuilder.value.id);
        }
    }, { deep: true });

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

        // 1. Валідація: не даємо зберегти, якщо ім'я пусте
        if (!newProduct.value.name || newProduct.value.name.trim() === '') {
            alert("Назва товару не може бути порожньою!");
            return false;
        }

        if (isSaving.value) return;
        isSaving.value = true;

        try {
            // Формуємо payload
            const payload = {
                ...newProduct.value,
                // Переконуємось, що числа є числами
                price: parseFloat(newProduct.value.price) || 0,
                stock_quantity: parseFloat(newProduct.value.stock_quantity) || 0,
                output_weight: parseFloat(newProduct.value.output_weight) || 0
            }

            if (isEditing.value && editingId.value) {
                await axios.put(`/api/products/${editingId.value}`, payload);
                // ПІСЛЯ РЕДАГУВАННЯ: не викликаємо resetForm тут, 
                // якщо хочемо залишити вікно відкритим з даними.
            } else {
                await axios.post('/api/products/', payload);
                resetForm(); // Тільки при створенні нового можна скинути
            }
            
            await fetchProducts()
            //resetForm()
            return true
        } catch (e) {
            console.error("Помилка збереження:", e);
            alert("Помилка: " + (e.response?.data?.detail || e.message));
            return false;
        } finally {
            isSaving.value = false;
        }
    }

    const deleteProduct = async (id) => {
        if (!confirm('Видалити цей товар?')) return
        try {
            await axios.delete(`/api/products/${id}`)
            await fetchProducts()
        } catch (e) {
            console.error(e)
            // Виводимо конкретну помилку від бекенда (напр. "Товар у замовленнях")
            const msg = e.response?.data?.detail || "Не вдалося видалити товар"
            alert(msg)
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
        console.log("🛠 [DEBUG] Клік на редагування варіанту. Індекс:", index);
    
        variantBuilder.value = JSON.parse(JSON.stringify(newProduct.value.variants[index]));
        editingVariantIndex.value = index;

        // Перевіряємо значення перед умовою
        console.log("🔍 [DEBUG] Перевірка ID для запиту:");
        console.log(" - Product ID (editingId):", editingId.value);
        console.log(" - Variant ID (variantBuilder.id):", variantBuilder.value.id);

        if (editingId.value && variantBuilder.value.id) {
            console.log("🚀 [DEBUG] Умова виконана! Відправляю запит на сервер...");
            fetchCalculatedStock(editingId.value, variantBuilder.value.id);
        } else {
            console.warn("⚠️ [DEBUG] Запит НЕ відправлено: ID продукту або варіанту відсутній.");
            console.log("Підказка: якщо ви тільки що створили цей варіант і не зберегли товар, у нього ще немає ID в базі.");
        }
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
        addIngredientToVariant, removeIngredientFromVariant,
        calculatedStock, variantCalculatedCost,fetchVariantCost,
        fetchCalculatedStock, generateSKU
    }
}