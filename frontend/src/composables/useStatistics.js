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
      console.log("🚀 Запит до API:", url)

      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        
        // --- 🔥 МІКРОСЕРВІСНЕ СКЛЕЮВАННЯ ДАНИХ (Frontend Join) ---
        let fetchedOrders = data.items || []
        
        // 1. Знаходимо всі унікальні ID клієнтів з цих чеків (відкидаємо null/гостей)
        const uniqueCustomerIds = [...new Set(fetchedOrders.map(o => o.customer_id).filter(id => id))]
        
        if (uniqueCustomerIds.length > 0) {
            const customerMap = {}
            
            // 2. Робимо паралельні запити до CRM для отримання імен
            await Promise.all(uniqueCustomerIds.map(async (id) => {
                try {
                    // Звертаємося до ендпоінта, який ми щойно створили в main.py
                    const cRes = await fetch(`/api/customers/${id}`)
                    if (cRes.ok) {
                        customerMap[id] = await cRes.json()
                    }
                } catch (err) {
                    console.error(`Не вдалося завантажити дані клієнта ${id}:`, err)
                }
            }))
            
            // 3. Підміняємо дані: "пришиваємо" об'єкт customer до кожного чека
            fetchedOrders = fetchedOrders.map(order => ({
                ...order,
                customer: order.customer_id ? (customerMap[order.customer_id] || null) : null
            }))
        }
        // ---------------------------------------------------------

        orders.value = fetchedOrders
        totalOrders.value = data.total
        totalPages.value = data.pages
      } else {
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
    orders, loading, totalOrders, totalPages, currentPage, pageSize,
    showDetailModal, selectedOrder, fetchOrders, openDetails, closeDetails
  }
}