import { ref, computed } from 'vue'

// Глобальний стан (зберігається, навіть якщо закрити компоненти)
const cartItems = ref([])
const isProcessing = ref(false)
const paymentMethod = ref('cash')
const selectedCustomer = ref(null)

export function useCart() {
  
  // --- GETTERS ---
  const totalSum = computed(() => {
    return cartItems.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  })

  const cartCount = computed(() => {
    return cartItems.value.reduce((sum, item) => sum + item.quantity, 0)
  })

  // --- ACTIONS ---
  
  const fetchCart = async () => {
    try {
      const res = await fetch('/api/cart/')
      if (res.ok) {
        const items = await res.json()
        cartItems.value = items.sort((a, b) => a.name.localeCompare(b.name))
      }
    } catch (err) {
      console.error("Cart fetch error:", err)
    }
  }

  const addToCart = async (payload) => {
    // payload: { product_id, variant_id, modifiers, quantity, ... }
    try {
      // --- ВИПРАВЛЕННЯ ТУТ: додано "/add" в кінці URL ---
      const res = await fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      // --- ДОДАТКОВО: Перевірка на помилку сервера ---
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`)
      }

      await fetchCart() // Оновлюємо список
    } catch (err) {
      console.error("Add to cart error:", err)
      alert("Не вдалося додати товар! Перевірте консоль.")
    }
  }

  const updateQty = async (cartItemId, change) => {
    try {
      await fetch(`/api/cart/${cartItemId}/update?change=${change}`, { method: 'POST' })
      await fetchCart()
    } catch (err) { console.error(err) }
  }

  const removeItem = async (cartItemId) => {
    if (!confirm('Видалити цей товар?')) return
    try {
      await fetch(`/api/cart/${cartItemId}`, { method: 'DELETE' })
      await fetchCart()
    } catch (err) { console.error(err) }
  }

  const clearCart = async (skipConfirm = false) => {
    if (!skipConfirm && !confirm('Очистити весь кошик?')) return
    try {
      await fetch('/api/cart/', { method: 'DELETE' })
      cartItems.value = []
      selectedCustomer.value = null
    } catch (err) { console.error(err) }
  }

  const processCheckout = async () => {
    if (cartItems.value.length === 0) return
    isProcessing.value = true

    try {
      const payload = {
        items: cartItems.value.map(item => ({
          product_id: item.product_id,
          variant_id: item.variant_id,
          modifiers: item.modifiers,
          quantity: item.quantity
        })),
        payment_method: paymentMethod.value,
        total_price: totalSum.value,
        customer_id: selectedCustomer.value ? selectedCustomer.value.id : null
      }

      const res = await fetch('/api/orders/checkout/', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) throw new Error("Помилка списання")

      await fetch('/api/cart/', { method: 'DELETE' })
      
      const resultMsg = {
        success: true,
        text: `✅ Оплата успішна!\nСума: ${totalSum.value} ₴` + (selectedCustomer.value ? `\nКлієнт: ${selectedCustomer.value.name}` : '')
      }
      
      cartItems.value = []
      selectedCustomer.value = null
      
      return resultMsg

    } catch (err) {
      console.error(err)
      return { success: false, text: "❌ Помилка при оплаті!" }
    } finally {
      isProcessing.value = false
    }
  }

  // Робота з клієнтом
  const setCustomer = (customer) => { selectedCustomer.value = customer }
  const removeCustomer = () => { selectedCustomer.value = null }

  return {
    cartItems,
    isProcessing,
    paymentMethod,
    selectedCustomer,
    totalSum,
    cartCount,
    fetchCart,
    addToCart,
    updateQty,
    removeItem,
    clearCart,
    processCheckout,
    setCustomer,
    removeCustomer
  }
}