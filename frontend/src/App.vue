<script setup>
import { ref, onMounted, computed } from 'vue'
// --- Імпортуємо НОВІ компоненти ---
import Sidebar from '@/components/common/Sidebar.vue'
import ProductCard from '@/components/pos/ProductCard.vue'
import CartDrawer from '@/components/pos/CartDrawer.vue'
import ProductModal from '@/components/pos/ProductModal.vue'
import ProductRoomModal from '@/components/pos/ProductRoomModal.vue'; // 🔥 Імпорт нової модалки [13, 14]

// --- Імпортуємо великі розділи ---
import Warehouse from '@/components/warehouse/Warehouse.vue'
import Statistics from '@/components/stats/Statistics.vue'
import Customers from '@/components/crm/Customers.vue'
import Finance from '@/components/finance/Finance.vue'

// --- Імпортуємо логіку (Composables) ---
import { useProducts } from '@/composables/useProducts'
import { useCart } from '@/composables/useCart'
import { useWarehouse } from '@/composables/useWarehouse'
import { useFinance } from '@/composables/useFinance'

// Стан навігації
const currentPage = ref('pos')
const activeWarehouseTab = ref('supplies') // Новий стан для вкладок складу
const { products, productRooms, loading, fetchWarehouseData } = useWarehouse()

// --- Логіка POS (Каси) ---
// Використовуємо useProducts для завантаження товарів на вітрину
const { 
  filteredProducts, // Вже відфільтровані пошуком
  productSearch, 
  fetchProducts 
} = useProducts()

// Використовуємо useCart для кошика (лічильник, відкриття)
const { 
  cartCount, 
  fetchCart // Щоб оновити лічильник при старті
} = useCart()

// 🔥 НОВЕ: Логіка фінансів та касової зміни
const { 
  activeShift, checkActiveShift, openShift, closeShift, 
  createTransaction, accounts, fetchAccounts, isLoading: isFinanceLoading 
} = useFinance()
const openingBalance = ref('')

// Стан для фінансових модалок
const isTransactionModalOpen = ref(false)
const isCloseShiftModalOpen = ref(false)

// Форми даних
const txForm = ref({ amount: '', type: 'EXPENSE', description: '' })
const closeForm = ref({ actualBalance: '', transferToSafe: '' })

// Допоміжна функція пошуку рахунків
const getAccountId = (typeStr, nameStr = '') => {
  const acc = accounts.value.find(a => a.type === typeStr || (nameStr && a.name.includes(nameStr)))
  return acc ? acc.id : 1
}

// Обробка Внесення/Винесення
const handleTransaction = async () => {
  if (!txForm.value.amount || txForm.value.amount <= 0) return alert("Введіть коректну суму")
  
  const cashId = getAccountId('cash') // Знаходимо ID Каси
  const amount = txForm.value.type === 'EXPENSE' ? -Math.abs(txForm.value.amount) : Math.abs(txForm.value.amount)

  const payload = {
    amount: amount,
    account_id: cashId,
    shift_id: activeShift.value.id,
    user_id: 1, // Тимчасово, поки немає авторизації
    description: txForm.value.description || (txForm.value.type === 'EXPENSE' ? 'Службове винесення' : 'Службове внесення')
  }

  const success = await createTransaction(payload)
  if (success) {
    isTransactionModalOpen.value = false
    txForm.value = { amount: '', type: 'EXPENSE', description: '' }
    // Можна додати тост-сповіщення "Успішно"
  }
}

// Обробка Z-звіту
const handleCloseShift = async () => {
  if (closeForm.value.actualBalance === '') return alert("Введіть фактичну суму в касі")

  const cashId = getAccountId('cash')
  const safeId = getAccountId('safe', 'сейф') // Знаходимо ID Сейфу

  const success = await closeShift(
    activeShift.value.id,
    Number(closeForm.value.actualBalance),
    Number(closeForm.value.transferToSafe || 0),
    cashId,
    safeId,
    1 // user_id
  )

  if (success) {
    isCloseShiftModalOpen.value = false
    closeForm.value = { actualBalance: '', transferToSafe: '' }
    // Зміна закрита, activeShift стане null, і автоматично з'явиться екран блокування!
  }
}

// Функція для кнопки "Відкрити зміну"
const handleOpenShift = async () => {
    if (openingBalance.value === '' || Number(openingBalance.value) < 0) {
        alert("Введіть коректну суму розмінки")
        return
    }
    // Передаємо user_id = 1 (в майбутньому тут буде ID авторизованого касира)
    const success = await openShift(1, Number(openingBalance.value))
    if (success) {
        openingBalance.value = '' // Очищаємо поле після успішного відкриття
    }
}

// Стан для кімнат
const isRoomModalOpen = ref(false)
const selectedRoom = ref(null)

const handleRoomClick = (room) => {
  selectedRoom.value = room;
  isRoomModalOpen.value = true;
}

// Фільтрація: показуємо лише товари, які НЕ входять в жодну кімнату [15, 16]
const independentProducts = computed(() => {
  return products.value.filter(p => p.room_id === null);
})

// Кімнати, що підпадають під пошук
const filteredRooms = computed(() => {
  if (!productSearch.value) return productRooms.value;
  const s = productSearch.value.toLowerCase();
  return productRooms.value.filter(r => r.name.toLowerCase().includes(s));
})

// Обробка кліку
const handleItemClick = (item, type) => {
  if (type === 'room') {
    selectedRoom.value = item;
    isRoomModalOpen.value = true;
  } else {
    selectedProduct.value = item;
    isModalOpen.value = true;
  }
}

// Товари, що підпадають під пошук ТА не належать до кімнат
const independentFilteredProducts = computed(() => {
  // 1. Спочатку беремо товари без кімнат
  const independent = products.value.filter(p => !p.room_id)
  
  // 2. Потім фільтруємо їх за пошуком
  if (!productSearch.value) return independent;
  const s = productSearch.value.toLowerCase();
  return independent.filter(p => p.name.toLowerCase().includes(s));
})

// Стан для UI каси
const isCartOpen = ref(false)
const isModalOpen = ref(false)
const selectedProduct = ref(null)

// Обробка кліку по товару
const handleProductClick = (product) => {
  // Якщо є варіанти або модифікатори -> відкриваємо модалку
  if (product.has_variants || (product.modifier_groups && product.modifier_groups.length > 0) || (product.process_groups && product.process_groups.length > 0)) {
    selectedProduct.value = product
    isModalOpen.value = true
  } else {
    // Якщо простий товар -> додаємо в кошик (через ProductModal логіку або напряму, 
    // але для простоти відкриємо модалку або можна викликати addToCart напряму.
    // Тут краще відкрити модалку для підтвердження або швидкого додавання)
    selectedProduct.value = product
    isModalOpen.value = true
  }
}

// Завантаження даних при старті
onMounted(async() => {

  // 1. Спочатку завантажуємо актуальні залишки зі складу
  await fetchWarehouseData()

  fetchProducts()
  // ВІДРАЗУ завантажуємо вміст кошика з сервера
  // Це наповнить cartItems і активує "м'яку броню" для ProductModal
  await fetchCart()
  await checkActiveShift() 
  await fetchAccounts() // Для фінансових операцій
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
    <Sidebar 
      :current-page="currentPage" 
      :active-sub-page="activeWarehouseTab"
      @change-page="(page) => currentPage = page"
      @change-sub-page="(tab) => activeWarehouseTab = tab"
    />

    <main v-if="currentPage === 'pos'" class="flex-1 ml-64 flex flex-col h-screen relative">
      <!-- ... (код для POS сторінки не змінюється) ... -->
      <div v-if="activeShift === null" class="absolute inset-0 z-50 bg-gray-50/95 backdrop-blur-sm flex flex-col items-center justify-center p-8">
          <div class="bg-white p-10 rounded-3xl shadow-2xl max-w-md w-full text-center border border-gray-100 animate-fade-in-up">
              <div class="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6 text-indigo-500 text-3xl">
                  <i class="fas fa-lock"></i>
              </div>
              <h2 class="text-3xl font-bold text-gray-800 mb-2">Зміна закрита</h2>
              <p class="text-gray-500 mb-8 leading-relaxed">Для початку роботи каси введіть суму розмінної монети (готівку в шухляді на даний момент).</p>
              
              <div class="text-left mb-8">
                  <label class="block text-xs font-bold text-gray-500 uppercase mb-3 text-center">Розмінна монета (Готівка, ₴)</label>
                  <div class="relative">
                      <span class="absolute left-6 top-1/2 -translate-y-1/2 text-gray-400 font-bold text-xl">₴</span>
                      <input v-model="openingBalance" type="number" min="0" placeholder="0" 
                             class="w-full text-3xl font-black text-center border-2 border-gray-200 py-4 px-10 rounded-2xl bg-gray-50 focus:bg-white focus:border-indigo-500 outline-none transition-all shadow-inner">
                  </div>
              </div>

              <button @click="handleOpenShift" :disabled="isFinanceLoading" 
                      class="w-full bg-indigo-600 text-white text-lg py-4 rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 disabled:opacity-50 hover:-translate-y-1">
                  <span v-if="isFinanceLoading"><i class="fas fa-spinner fa-spin mr-2"></i> Відкриття...</span>
                  <span v-else>Відкрити зміну</span>
              </button>
          </div>
      </div>
      <!-- Header залишаємо без змін, він працює добре -->
      <header class="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gray-200 px-8 py-4 flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Меню</h2>
          <div class="flex items-center gap-2 mt-1">
             <i class="fas fa-search text-gray-400"></i>
             <input v-model="productSearch" type="text" placeholder="Пошук кави..." class="bg-transparent outline-none text-sm w-64">
          </div>
        </div>
        <div v-if="activeShift" class="flex items-center gap-2 border-r pr-4 border-gray-200">
            <button @click="isTransactionModalOpen = true" class="text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl font-medium transition">
              <i class="fas fa-money-bill-transfer mr-2"></i> Внесення/Винесення
            </button>
            <button @click="isCloseShiftModalOpen = true" class="text-red-600 bg-red-50 hover:bg-red-100 px-4 py-2 rounded-xl font-bold transition">
              <i class="fas fa-cash-register mr-2"></i> Z-Звіт
            </button>
        </div>
        <button @click="isCartOpen = true" class="bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition shadow-lg flex items-center gap-3 active:scale-95">
          <i class="fas fa-shopping-cart"></i> <span>Кошик: {{ cartCount }}</span>
        </button>
      </header>

      <div class="p-8 overflow-y-auto flex-1 custom-scrollbar">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
          
          <!-- 1. РЕНДЕРИМО КІМНАТИ (ЯК ПАПКИ) -->
          <!-- Ми фільтруємо кімнати за пошуковим запитом назви кімнати -->
          <div 
            v-for="room in filteredRooms" 
            :key="'room-' + room.id"
            @click="handleRoomClick(room)"
            class="cursor-pointer bg-gradient-to-br from-purple-600 to-indigo-700 p-6 rounded-2xl text-white shadow-lg transform hover:scale-[1.02] transition-all flex flex-col items-center justify-center text-center group relative overflow-hidden"
          >
            <!-- Декор папки -->
            <div class="absolute -right-4 -top-4 bg-white/10 w-20 h-20 rounded-full blur-2xl group-hover:bg-white/20 transition-colors"></div>
            
            <div class="text-5xl mb-3 drop-shadow-md">📂</div>
            <div class="font-bold text-lg leading-tight">{{ room.name }}</div>
            <div class="text-xs opacity-80 mt-2 bg-black/20 px-3 py-1 rounded-full">
              {{ room.products?.length || 0 }} позицій
            </div>
          </div>

          <!-- 2. РЕНДЕРИМО НЕЗАЛЕЖНІ ТОВАРИ -->
          <!-- Використовуємо оновлений computed "independentFilteredProducts" -->
          <ProductCard 
            v-for="item in independentFilteredProducts" 
            :key="item.id" 
            :product="item" 
            @click="handleProductClick" 
          />
        </div>
        
        <!-- Стан порожнього пошуку -->
        <div v-if="independentFilteredProducts.length === 0 && filteredRooms.length === 0" class="text-center text-gray-400 mt-20">
            <i class="fas fa-mug-hot text-6xl mb-4 opacity-20"></i>
            <p>Товарів не знайдено</p>
        </div>
      </div>

      <CartDrawer 
        :is-open="isCartOpen"
        @close="isCartOpen = false"
      />
      
      <!-- СТАНДАРТНА МОДАЛКА (для товарів без кімнат) -->
      <ProductModal 
        v-if="selectedProduct"
        :is-open="isModalOpen"
        :product="selectedProduct"
        @close="isModalOpen = false"
      />

      <!-- НОВА МОДАЛКА КІМНАТИ (для вибору фасувань) -->
      <ProductRoomModal
        v-if="selectedRoom"
        :is-open="isRoomModalOpen"
        :group="selectedRoom"
        @close="isRoomModalOpen = false"
      />
    </main>

    <Warehouse v-if="currentPage === 'warehouse'" :current-tab="activeWarehouseTab" />
    <Statistics v-if="currentPage === 'statistics'" />
    <Customers v-if="currentPage === 'customers'" />
    <Finance v-if="currentPage === 'finance'" />
  </div>
  <div v-if="isTransactionModalOpen" class="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-xl font-bold">Службова операція</h3>
            <button @click="isTransactionModalOpen = false" class="text-gray-400 hover:text-gray-600"><i class="fas fa-times text-xl"></i></button>
          </div>
          
          <div class="flex gap-2 mb-4">
            <button @click="txForm.type = 'EXPENSE'" :class="txForm.type === 'EXPENSE' ? 'bg-red-50 text-red-600 border-red-200' : 'bg-gray-50 text-gray-500 border-transparent'" class="flex-1 py-3 border rounded-xl font-bold transition">Винесення</button>
            <button @click="txForm.type = 'INCOME'" :class="txForm.type === 'INCOME' ? 'bg-green-50 text-green-600 border-green-200' : 'bg-gray-50 text-gray-500 border-transparent'" class="flex-1 py-3 border rounded-xl font-bold transition">Внесення</button>
          </div>

          <div class="space-y-4 mb-6">
            <div>
              <label class="block text-sm text-gray-500 mb-1">Сума (₴)</label>
              <input v-model="txForm.amount" type="number" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-indigo-500 text-lg font-bold">
            </div>
            <div>
              <label class="block text-sm text-gray-500 mb-1">Коментар</label>
              <input v-model="txForm.description" type="text" placeholder="Наприклад: Оплата за воду" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-indigo-500">
            </div>
          </div>

          <button @click="handleTransaction" :disabled="isFinanceLoading" class="w-full bg-gray-900 text-white font-bold py-4 rounded-xl hover:bg-gray-800 transition disabled:opacity-50">
            <span v-if="isFinanceLoading"><i class="fas fa-spinner fa-spin"></i></span>
            <span v-else>Провести операцію</span>
          </button>
        </div>
      </div>

      <div v-if="isCloseShiftModalOpen" class="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 border-t-8 border-red-500">
          <div class="text-center mb-6">
            <div class="w-16 h-16 bg-red-100 text-red-500 rounded-full flex items-center justify-center mx-auto mb-2 text-2xl"><i class="fas fa-file-invoice-dollar"></i></div>
            <h3 class="text-2xl font-bold text-gray-800">Закриття зміни (Z-Звіт)</h3>
            <p class="text-gray-500 text-sm mt-1">Перерахуйте готівку в касі та заповніть поля</p>
          </div>

          <div class="space-y-4 mb-8">
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Фактично в касі (₴)</label>
              <input v-model="closeForm.actualBalance" type="number" placeholder="0" class="w-full bg-gray-50 border-2 border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-red-400 text-2xl text-center font-black">
            </div>
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Вилучити в сейф (Інкасація ₴)</label>
              <input v-model="closeForm.transferToSafe" type="number" placeholder="Скільки забираєте з каси" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-red-400 text-lg text-center font-bold">
              <p class="text-xs text-gray-400 text-center mt-2">Різниця залишиться як розмінка на наступний день</p>
            </div>
          </div>

          <div class="flex gap-3">
            <button @click="isCloseShiftModalOpen = false" class="flex-1 py-4 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition">Скасувати</button>
            <button @click="handleCloseShift" :disabled="isFinanceLoading" class="flex-1 py-4 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl transition disabled:opacity-50 shadow-lg shadow-red-200">
              <span v-if="isFinanceLoading"><i class="fas fa-spinner fa-spin"></i></span>
              <span v-else>Закрити зміну</span>
            </button>
          </div>
        </div>
      </div>
</template>
