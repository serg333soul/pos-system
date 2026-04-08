import { ref, computed } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'; // 1. Імпортуємо склад

const cartItems = ref([])
const isProcessing = ref(false)
const paymentMethod = ref('cash')
const selectedCustomer = ref(null)

const totalSum = computed(() => {
    return cartItems.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  })

export function useCart() {
  
  const warehouse = useWarehouse(); // Отримуємо весь об'єкт складу
  const { fetchWarehouseData } = warehouse; // 2. Дістаємо функцію завантаження
  // Ця сума тепер ТІЛЬКИ для відображення користувачу
  

  const cartCount = computed(() => {
    return cartItems.value.reduce((sum, item) => sum + item.quantity, 0)
  })

  const fetchCart = async () => {
    try {
      const res = await fetch('/api/cart/')
      if (res.ok) {
        const items = await res.json()
        cartItems.value = items.sort((a, b) => a.name.localeCompare(b.name))
      }
    } catch (err) { console.error("Cart fetch error:", err) }
  }

  const addToCart = async (payload) => {
    try {
      const res = await fetch('/api/cart/add', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) await fetchCart()
    } catch (err) { console.error(err) }
  }
  
  const removeFromCart = async (itemId) => {
     try {
      await fetch(`/api/cart/${itemId}`, { method: 'DELETE' })
      await fetchCart()
    } catch (err) { console.error(err) }
  }
  
  const reservedResources = computed(() => {
    const ingredients = {} 
    const consumables = {} 

    cartItems.value.forEach(item => {
        const product = warehouse.products.value.find(p => p.id === item.product_id)
        const variant = product?.variants?.find(v => v.id === item.variant_id)

        if (variant) {
            // 1. ПЕРЕВІРКА ТЕХКАРТИ (MasterRecipe) - 🔥 ЦЕ ТЕ, ЧОГО НЕ ВИСТАЧАЛО
            if (variant.master_recipe_id) {
                const recipe = warehouse.recipes.value.find(r => r.id === variant.master_recipe_id)
                recipe?.items?.forEach(rItem => {
                    // Розраховуємо кількість (враховуючи % від ваги виходу)
                    let qty = rItem.quantity
                    if (rItem.is_percentage) {
                        qty = (rItem.quantity / 100) * (variant.output_weight || 0)
                    }
                    ingredients[rItem.ingredient_id] = (ingredients[rItem.ingredient_id] || 0) + (qty * item.quantity)
                })
            }

            // 2. Додаткові інгредієнти (якщо є)
            variant.ingredients?.forEach(ing => {
                ingredients[ing.ingredient_id] = (ingredients[ing.ingredient_id] || 0) + (ing.quantity * item.quantity)
            })

            // 3. Матеріали (стаканчики тощо)
            variant.consumables?.forEach(con => {
                consumables[con.consumable_id] = (consumables[con.consumable_id] || 0) + (con.quantity * item.quantity)
            })
        }
    })
    return { ingredients, consumables }
})

  const clearCart = async () => {
    try {
        await fetch('/api/cart/', { method: 'DELETE' })
        cartItems.value = []
    } catch(e) { console.error(e) }
  }

  // ОСНОВНА ЗМІНА ТУТ
  // Додаємо аргумент options з деструктуризацією, щоб отримати useBonuses з CartDrawer
  const processCheckout = async ({ useBonuses = false } = {}) => {
    if (cartItems.value.length === 0) return
    isProcessing.value = true
    
    try {
      const payload = {
        items: cartItems.value.map(item => ({
          product_id: item.product_id,
          variant_id: item.variant_id || null,
          quantity: item.quantity,
          consumable_overrides: item.consumable_overrides || [],
          ingredient_overrides: item.ingredient_overrides || [],
          modifiers: Array.isArray(item.modifiers) 
            ? item.modifiers.map(m => ({
              modifier_id: typeof m === 'number' ? m : (m.id || m.modifier_id),
              quantity: m.quantity || 1 
              }))
            : []
        })),
        payment_method: paymentMethod.value,
        customer_id: selectedCustomer.value ? selectedCustomer.value.id : null,
        // 🔥 ПЕРЕДАЄМО ПРАПОРЕЦЬ БОНУСІВ НА БЕКЕНД
        use_bonuses: useBonuses 
      }

      console.log("📤 Checkout Request:", payload)

      const res = await fetch('/api/orders/checkout/', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
          const err = await res.json()
          await fetchWarehouseData(); // Оновлюємо дані складу (виніс перед throw)
          throw new Error(err.detail || "Помилка при оплаті")
      }

      const responseData = await res.json()

      await fetchWarehouseData();
      
      // Очищення (тепер ми НЕ скидаємо selectedCustomer тут, це робить CartDrawer.vue)
      await fetch('/api/cart/', { method: 'DELETE' })
      cartItems.value = []
      // ❌ selectedCustomer.value = null (ВИДАЛЕНО, щоб не ламалася анімація в CartDrawer)
      
      return {
        success: true,
        text: `✅ Оплата успішна!\nСписано: ${responseData.total_price} ₴`
      }

    } catch (err) {
      console.error(err)
      return { success: false, text: `❌ Помилка: ${err.message}` }
    } finally {
      isProcessing.value = false
    }
  }


  const setCustomer = (c) => { selectedCustomer.value = c }
  const removeCustomer = () => { selectedCustomer.value = null }

  return {
    cartItems, cartCount, totalSum, isProcessing, paymentMethod, selectedCustomer,
    fetchCart, addToCart, removeFromCart, clearCart, processCheckout,
    setCustomer, removeCustomer, reservedResources
  }
}