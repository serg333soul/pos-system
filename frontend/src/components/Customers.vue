<script setup>
import { ref, onMounted, watch } from 'vue'

const customers = ref([])
const loading = ref(false)
const searchQuery = ref('')
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

// --- НОВЕ: ЗМІННІ ДЛЯ ІСТОРІЇ ---
const showHistoryModal = ref(false)
const historyLoading = ref(false)
const currentCustomerHistory = ref(null) // Клієнт, чию історію дивимось
const customerOrders = ref([]) // Список його замовлень

// Форма
const formData = ref({
  name: '',
  phone: '',
  email: '',
  notes: ''
})

// Форматування дати
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

// --- API ЗАПИТИ (CRUD) ---
const fetchCustomers = async () => {
  loading.value = true
  try {
    let url = '/api/customers/'
    if (searchQuery.value.length > 0) url = `/api/customers/search/?q=${searchQuery.value}`
    const res = await fetch(url)
    if (res.ok) customers.value = await res.json()
  } catch (err) { console.error(err) } finally { loading.value = false }
}

const openCreateModal = () => {
  isEditing.value = false
  formData.value = { name: '', phone: '', email: '', notes: '' }
  showModal.value = true
}

const openEditModal = (customer) => {
  isEditing.value = true
  editingId.value = customer.id
  formData.value = { name: customer.name, phone: customer.phone, email: customer.email, notes: customer.notes }
  showModal.value = true
}

const saveCustomer = async () => {
  if (!formData.value.name || !formData.value.phone) return alert("Ім'я та Телефон обов'язкові!")
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
      fetchCustomers()
      alert(isEditing.value ? "Клієнта оновлено!" : "Клієнта створено!")
    } else {
      const err = await res.json()
      alert("Помилка: " + (err.detail || "Не вдалося зберегти"))
    }
  } catch (err) { console.error(err) }
}

const deleteCustomer = async (id) => {
  if (!confirm("Видалити цього клієнта з бази?")) return
  await fetch(`/api/customers/${id}`, { method: 'DELETE' })
  fetchCustomers()
}

// --- НОВЕ: ЛОГІКА ІСТОРІЇ ---
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

let timeout = null
watch(searchQuery, () => {
  clearTimeout(timeout)
  timeout = setTimeout(() => { fetchCustomers() }, 500)
})

onMounted(() => {
  fetchCustomers()
})
</script>

<template>
  <div class="p-8 h-screen overflow-y-auto bg-gray-50 ml-64 custom-scrollbar">
    
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-3xl font-bold text-gray-800">👥 Клієнти (CRM)</h2>
        <p class="text-gray-500">База постійних відвідувачів</p>
      </div>
      <button @click="openCreateModal" class="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-blue-700 transition shadow-lg flex items-center gap-2">
        <i class="fas fa-user-plus"></i> Додати клієнта
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 mb-6 flex gap-4 items-center">
      <i class="fas fa-search text-gray-400 text-xl ml-2"></i>
      <input v-model="searchQuery" type="text" placeholder="Пошук за ім'ям або телефоном..." class="w-full text-lg outline-none text-gray-700 placeholder-gray-400">
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-gray-50 text-gray-500 uppercase text-xs">
          <tr>
            <th class="p-4">Ім'я</th>
            <th class="p-4">Телефон</th>
            <th class="p-4">Email / Нотатки</th>
            <th class="p-4 text-center">Дії</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="customers.length === 0" class="text-center text-gray-400">
            <td colspan="4" class="p-8">
                <span v-if="loading"><i class="fas fa-spinner fa-spin"></i> Завантаження...</span>
                <span v-else>Клієнтів не знайдено</span>
            </td>
          </tr>

          <tr v-for="c in customers" :key="c.id" class="hover:bg-blue-50 transition group">
            <td class="p-4 font-bold text-gray-800">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                        {{ c.name.charAt(0) }}
                    </div>
                    {{ c.name }}
                </div>
            </td>
            <td class="p-4 font-mono text-gray-600">{{ c.phone }}</td>
            <td class="p-4 text-sm text-gray-500">
                <div v-if="c.email">{{ c.email }}</div>
                <div v-if="c.notes" class="italic text-xs mt-1">"{{ c.notes }}"</div>
            </td>
            <td class="p-4 text-center flex justify-center gap-2">
                <button @click="openHistory(c)" class="text-purple-400 hover:text-purple-600 transition px-2" title="Історія покупок">
                    <i class="fas fa-history"></i>
                </button>
                <button @click="openEditModal(c)" class="text-gray-400 hover:text-blue-500 transition px-2" title="Редагувати">
                    <i class="fas fa-pen"></i>
                </button>
                <button @click="deleteCustomer(c.id)" class="text-gray-400 hover:text-red-500 transition px-2" title="Видалити">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 relative">
            <button @click="showModal = false" class="absolute top-4 right-4 text-gray-400 hover:text-gray-600"><i class="fas fa-times text-xl"></i></button>
            <h3 class="text-xl font-bold mb-4">{{ isEditing ? 'Редагувати клієнта' : 'Новий клієнт' }}</h3>
            <div class="space-y-4">
                <div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ім'я *</label><input v-model="formData.name" class="w-full border p-3 rounded-lg bg-gray-50 focus:bg-white outline-none"></div>
                <div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Телефон *</label><input v-model="formData.phone" class="w-full border p-3 rounded-lg bg-gray-50 focus:bg-white outline-none"></div>
                <div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Email</label><input v-model="formData.email" class="w-full border p-3 rounded-lg bg-gray-50"></div>
                <div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Нотатки</label><textarea v-model="formData.notes" class="w-full border p-3 rounded-lg bg-gray-50" rows="2"></textarea></div>
                <button @click="saveCustomer" class="w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition mt-2">{{ isEditing ? 'Зберегти зміни' : 'Створити' }}</button>
            </div>
        </div>
    </div>

    <div v-if="showHistoryModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl h-[80vh] flex flex-col relative overflow-hidden">
            <div class="p-6 border-b bg-gray-50 flex justify-between items-center">
                <div>
                    <h3 class="text-xl font-bold text-gray-800">Історія покупок</h3>
                    <p class="text-gray-500" v-if="currentCustomerHistory">{{ currentCustomerHistory.name }} ({{ currentCustomerHistory.phone }})</p>
                </div>
                <button @click="showHistoryModal = false" class="text-gray-400 hover:text-gray-600"><i class="fas fa-times text-2xl"></i></button>
            </div>

            <div class="flex-1 overflow-y-auto p-0">
                <div v-if="historyLoading" class="flex justify-center items-center h-40 text-gray-400">
                    <i class="fas fa-spinner fa-spin text-2xl"></i>
                </div>
                
                <div v-else-if="customerOrders.length === 0" class="flex flex-col justify-center items-center h-64 text-gray-400">
                    <i class="fas fa-shopping-bag text-5xl mb-4 opacity-20"></i>
                    <p>Цей клієнт ще нічого не купував</p>
                </div>

                <table v-else class="w-full text-left">
                    <thead class="bg-gray-100 text-gray-500 uppercase text-xs sticky top-0">
                        <tr>
                            <th class="p-4">Дата</th>
                            <th class="p-4">Товари</th>
                            <th class="p-4 text-right">Сума</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="order in customerOrders" :key="order.id" class="hover:bg-gray-50">
                            <td class="p-4 text-sm whitespace-nowrap">
                                <div class="font-bold text-gray-800">{{ formatDate(order.created_at).split(',')[0] }}</div>
                                <div class="text-xs text-gray-500">{{ formatDate(order.created_at).split(',')[1] }}</div>
                                <span class="text-[10px] px-1.5 py-0.5 rounded border" 
                                      :class="order.payment_method==='card' ? 'text-blue-600 border-blue-200 bg-blue-50' : 'text-green-600 border-green-200 bg-green-50'">
                                    {{ order.payment_method === 'card' ? 'Картка' : 'Готівка' }}
                                </span>
                            </td>
                            <td class="p-4">
                                <ul class="text-sm">
                                    <li v-for="item in order.items" :key="item.id" class="flex justify-between w-full max-w-[200px]">
                                        <span>{{ item.product_name }}</span>
                                        <span class="text-gray-400 ml-2">x{{ item.quantity }}</span>
                                    </li>
                                </ul>
                            </td>
                            <td class="p-4 text-right font-bold font-mono text-gray-700">
                                {{ order.total_price }} ₴
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="p-4 border-t bg-gray-50 text-right text-sm text-gray-500">
                Всього замовлень: <b>{{ customerOrders.length }}</b>
            </div>
        </div>
    </div>

  </div>
</template>