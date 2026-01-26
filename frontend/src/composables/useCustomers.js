import { ref, watch } from 'vue'

export function useCustomers() {
  const customers = ref([])
  const loading = ref(false)
  
  // Пошук
  const searchQuery = ref('')
  
  // Для модального вікна редагування
  const showModal = ref(false)
  const isEditing = ref(false)
  const editingId = ref(null)
  const formData = ref({ name: '', phone: '', email: '', notes: '' })

  // Для історії
  const showHistoryModal = ref(false)
  const historyLoading = ref(false)
  const currentCustomerHistory = ref(null)
  const customerOrders = ref([])

  // --- ACTIONS ---

  const fetchCustomers = async () => {
    loading.value = true
    try {
      let url = '/api/customers/'
      if (searchQuery.value.length > 0) url = `/api/customers/search/?q=${searchQuery.value}`
      const res = await fetch(url)
      if (res.ok) customers.value = await res.json()
    } catch (err) { console.error(err) } finally { loading.value = false }
  }

  // --- CRUD Operations ---
  
  const openCreateModal = () => {
    isEditing.value = false
    formData.value = { name: '', phone: '', email: '', notes: '' }
    showModal.value = true
  }

  const openEditModal = (customer) => {
    isEditing.value = true
    editingId.value = customer.id
    formData.value = { ...customer } // Копіюємо дані
    showModal.value = true
  }

  const saveCustomer = async () => {
    if (!formData.value.name || !formData.value.phone) {
        alert("Ім'я та Телефон обов'язкові!")
        return false
    }
    
    try {
      let url = '/api/customers/'
      let method = 'POST'
      
      if (isEditing.value) {
        url = `/api/customers/${editingId.value}`
        method = 'PUT'
      }
      
      const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData.value)
      })
      
      if (res.ok) {
        showModal.value = false
        await fetchCustomers()
        return true
      } else {
        const err = await res.json()
        alert("Помилка: " + (err.detail || "Не вдалося зберегти"))
        return false
      }
    } catch (err) { 
        console.error(err)
        return false
    }
  }

  const deleteCustomer = async (id) => {
    if (!confirm("Видалити цього клієнта з бази?")) return
    try {
        await fetch(`/api/customers/${id}`, { method: 'DELETE' })
        await fetchCustomers()
    } catch (err) { console.error(err) }
  }

  // --- History Logic ---

  const openHistory = async (customer) => {
    currentCustomerHistory.value = customer
    customerOrders.value = []
    showHistoryModal.value = true
    historyLoading.value = true
    
    try {
      const res = await fetch(`/api/customers/${customer.id}/orders/`)
      if (res.ok) {
        customerOrders.value = await res.json()
      }
    } catch (err) {
      console.error(err)
      alert("Не вдалося завантажити історію")
    } finally {
      historyLoading.value = false
    }
  }

  // --- Watcher для пошуку ---
  let timeout = null
  watch(searchQuery, () => {
    clearTimeout(timeout)
    timeout = setTimeout(() => { fetchCustomers() }, 500)
  })

  return {
    customers,
    loading,
    searchQuery,
    showModal,
    isEditing,
    formData,
    // History
    showHistoryModal,
    historyLoading,
    currentCustomerHistory,
    customerOrders,
    // Actions
    fetchCustomers,
    openCreateModal,
    openEditModal,
    saveCustomer,
    deleteCustomer,
    openHistory
  }
}