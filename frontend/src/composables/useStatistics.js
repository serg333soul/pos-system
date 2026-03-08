import { ref, watch } from 'vue'

export function useStatistics() {
  const orders = ref([])
  const loading = ref(true)
  const totalOrders = ref(0)
  const totalPages = ref(1)
  
  // 🔥 Параметри пагінації
  const currentPage = ref(1)
  const pageSize = ref(20) // Скільки завантажувати відразу

  // Для модального вікна деталей
  const showDetailModal = ref(false)
  const selectedOrder = ref(null)

  const fetchOrders = async () => {
    loading.value = true
    try {
      const url = `/api/orders/?page=${currentPage.value}&limit=${pageSize.value}`
      console.log("🚀 Запит до API:", url) // Додай для дебагу в консолі

      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        orders.value = data.items
        totalOrders.value = data.total
        totalPages.value = data.pages
      } else {
      // Якщо тут 422 - значить лапки все ще не ті
      console.error("❌ Помилка бекенда:", res.status);
      }
    } catch (err) {
      console.error("Помилка завантаження статистики:", err)
    } finally {
      loading.value = false
    }
  }

  // Слідкуємо за зміною сторінки або ліміту
  watch([currentPage, pageSize], (newValues) => {
    console.log("👀 Вочер спрацював! Нові значення [page, limit]:", newValues);
    fetchOrders();
  }, { immediate: true })

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
    totalOrders, 
    totalPages,
    currentPage, 
    pageSize,
    showDetailModal,
    selectedOrder,
    fetchOrders,
    openDetails,
    closeDetails
  }
}