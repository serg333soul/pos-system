import { ref } from 'vue'

export function useStatistics() {
  const orders = ref([])
  const loading = ref(true)
  
  // Для модального вікна деталей
  const showDetailModal = ref(false)
  const selectedOrder = ref(null)

  const fetchOrders = async () => {
    loading.value = true
    try {
      const res = await fetch('/api/orders/')
      if (res.ok) {
        orders.value = await res.json()
      }
    } catch (err) {
      console.error("Помилка завантаження статистики:", err)
    } finally {
      loading.value = false
    }
  }

  const openDetails = (order) => {
    selectedOrder.value = order
    showDetailModal.value = true
  }

  const closeDetails = () => {
    showDetailModal.value = false
    selectedOrder.value = null
  }

  return {
    orders,
    loading,
    showDetailModal,
    selectedOrder,
    fetchOrders,
    openDetails,
    closeDetails
  }
}