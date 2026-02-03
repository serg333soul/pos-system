import { ref, computed } from 'vue'

const cartItems = ref([])
const isProcessing = ref(false)
const paymentMethod = ref('cash')
const selectedCustomer = ref(null)

export function useCart() {
  
  // Ця сума тепер ТІЛЬКИ для відображення користувачу
  const totalSum = computed(() => {
    return cartItems.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  })

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
  
  const clearCart = async () => {
    try {
        await fetch('/api/cart/', { method: 'DELETE' })
        cartItems.value = []
    } catch(e) { console.error(e) }
  }

  // 🔥 ОСНОВНА ЗМІНА ТУТ
  const processCheckout = async () => {
    if (cartItems.value.length === 0) return
    isProcessing.value = true
    
    try {
      const payload = {
        items: cartItems.value.map(item => ({
          product_id: item.product_id,
          variant_id: item.variant_id || null,
          quantity: item.quantity,
          // Безпечна обробка модифікаторів
          modifiers: Array.isArray(item.modifiers) 
            ? item.modifiers.map(m => (typeof m === 'number' ? { modifier_id: m } : m))
            : []
        })),
        payment_method: paymentMethod.value,
        // ❌ total_price БІЛЬШЕ НЕ ВІДПРАВЛЯЄМО!
        customer_id: selectedCustomer.value ? selectedCustomer.value.id : null
      }

      console.log("📤 Checkout Request:", payload)

      const res = await fetch('/api/orders/checkout/', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || "Помилка при оплаті")
      }

      const responseData = await res.json()
      
      // Очищення
      await fetch('/api/cart/', { method: 'DELETE' })
      cartItems.value = []
      selectedCustomer.value = null
      
      // Повертаємо результат із СЕРВЕРНОЮ сумою
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
    setCustomer, removeCustomer
  }
}