<script setup>
import { ref, watch, computed } from 'vue' // 🔥 Додано computed
import { useCart } from '@/composables/useCart'

const props = defineProps({ isOpen: Boolean })
const emit = defineEmits(['close'])

const { 
  cartItems, totalSum, paymentMethod, isProcessing, selectedCustomer,
  fetchCart, removeFromCart, clearCart, processCheckout,
  setCustomer, removeCustomer
} = useCart()

const customerSearch = ref('')
const customerResults = ref([])

// 🔥 НОВІ ЗМІННІ ДЛЯ БОНУСІВ
const useBonuses = ref(false)

// Перераховуємо фінальну суму з урахуванням бонусів
const finalTotal = computed(() => {
  if (!useBonuses.value || !selectedCustomer.value) return totalSum.value;
  const bonuses = Number(selectedCustomer.value.bonus_balance) || 0;
  // Сума не може бути меншою за 0
  return Math.max(0, totalSum.value - bonuses);
})

const handleSearchCustomer = async () => {
  if (customerSearch.value.length < 2) { customerResults.value = []; return }
  try {
    const res = await fetch(`/api/customers/search/?q=${customerSearch.value}`)
    if (res.ok) customerResults.value = await res.json()
  } catch (err) { console.error(err) }
}

const selectCustomerUI = (c) => {
  setCustomer(c)
  customerSearch.value = ''
  customerResults.value = []
  useBonuses.value = false // Скидаємо чекбокс при виборі нового клієнта
}

const handleRemoveCustomerUI = () => {
  removeCustomer()
  useBonuses.value = false // Скидаємо чекбокс при видаленні клієнта
}

const handleClearCart = async () => {
    if (cartItems.value.length === 0) return
    if (confirm('Ви впевнені, що хочете повністю очистити кошик?')) {
        await clearCart()
    }
}

const handleCheckout = async () => {
  // Зберігаємо вибір касира
  const wantsToUseBonuses = useBonuses.value;
  const customerId = selectedCustomer.value?.id;
  
  // Одразу вимикаємо галочку, щоб Vue не намагався малювати бонуси після очищення кошика
  useBonuses.value = false; 

  // 🔥 Передаємо інформацію про бонуси в composable/backend
  const res = await processCheckout({ 
    useBonuses: wantsToUseBonuses,
    customer_id: customerId
  })
  
  if (res && res.success) {
    alert(res.text) 
    //useBonuses.value = false // Очищаємо після успішної оплати
    emit('close')
  } else if (res && !res.success) {
    alert(res.text)
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm transition-opacity" @click="emit('close')"></div>
  
  <div 
    class="fixed top-0 right-0 h-full w-96 bg-gray-50 shadow-2xl z-50 transform transition-transform duration-300 flex flex-col"
    :class="isOpen ? 'translate-x-0' : 'translate-x-full'"
  >
    <div class="p-5 bg-white border-b flex justify-between items-center">
      <h2 class="text-xl font-bold text-gray-800 flex items-center gap-2">
        <i class="fas fa-shopping-cart text-purple-600"></i> Кошик
      </h2>
      <div class="flex gap-2">
        <button @click="handleClearCart" title="Очистити кошик" class="w-8 h-8 rounded-full bg-red-50 text-red-500 hover:bg-red-100 flex items-center justify-center transition">
            <i class="fas fa-trash-alt"></i>
        </button>
        <button @click="emit('close')" class="w-8 h-8 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 flex items-center justify-center transition">
            <i class="fas fa-times"></i>
        </button>
      </div>
    </div>

    <div class="p-4 bg-white border-b">
      <div v-if="!selectedCustomer" class="relative">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <i class="fas fa-user-plus text-gray-400"></i>
        </div>
        <input 
          v-model="customerSearch" 
          @input="handleSearchCustomer"
          type="text" 
          placeholder="Пошук клієнта (ім'я або телефон)..." 
          class="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none transition"
        >
        <div v-if="customerResults.length > 0" class="absolute z-10 w-full mt-1 bg-white border rounded-xl shadow-lg max-h-48 overflow-y-auto">
          <div 
            v-for="c in customerResults" :key="c.id" 
            @click="selectCustomerUI(c)"
            class="p-3 hover:bg-purple-50 cursor-pointer border-b last:border-0 flex justify-between items-center"
          >
            <div>
                <div class="font-bold text-gray-800 text-sm">{{ c.name }}</div>
                <div class="text-xs text-gray-500">{{ c.phone }}</div>
            </div>
            <div class="text-xs font-bold text-green-600" v-if="c.bonus_balance > 0">
              {{ Number(c.bonus_balance).toFixed(2) }} ₴
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="bg-purple-50 rounded-xl p-3 border border-purple-100">
        <div class="flex justify-between items-start">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-purple-200 text-purple-700 flex items-center justify-center">
                    <i class="fas fa-user"></i>
                </div>
                <div>
                    <div class="text-xs text-purple-400 font-bold uppercase tracking-wider">Клієнт</div>
                    <div class="font-bold text-gray-800">{{ selectedCustomer.name }}</div>
                </div>
            </div>
            <button @click="handleRemoveCustomerUI" class="text-purple-400 hover:text-purple-600 p-1">
                <i class="fas fa-times-circle text-lg"></i>
            </button>
        </div>

        <div class="mt-3 p-3 bg-white rounded-lg border border-purple-100 flex justify-between items-center shadow-sm">
            <div>
                <div class="text-xs text-gray-500">Доступно бонусів:</div>
                <div class="font-bold text-green-600 text-lg">{{ Number(selectedCustomer.bonus_balance || 0).toFixed(2) }} ₴</div>
            </div>
            <label v-if="Number(selectedCustomer.bonus_balance) > 0" class="flex items-center cursor-pointer gap-2 bg-gray-50 px-3 py-1.5 rounded-lg border hover:bg-gray-100 transition">
                <span class="text-sm font-bold text-gray-700">Списати</span>
                <input type="checkbox" v-model="useBonuses" class="w-5 h-5 text-purple-600 rounded focus:ring-purple-500 cursor-pointer">
            </label>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-4 custom-scrollbar bg-gray-50">
      <div v-if="cartItems.length === 0" class="h-full flex flex-col items-center justify-center text-gray-400 gap-3">
        <i class="fas fa-shopping-basket text-5xl opacity-50"></i>
        <p>Кошик порожній</p>
      </div>
      
      <div v-else class="space-y-3">
        <div v-for="item in cartItems" :key="item.id" class="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex gap-3 relative group">
            <button 
                @click="removeFromCart(item.id)" 
                class="absolute -top-2 -right-2 w-6 h-6 bg-red-100 text-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm hover:bg-red-500 hover:text-white"
            >
                <i class="fas fa-times text-xs"></i>
            </button>

            <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 flex-shrink-0">
                <i class="fas fa-coffee text-2xl"></i>
            </div>
            
            <div class="flex-1 flex flex-col justify-between">
                <div>
                    <h3 class="font-bold text-gray-800 text-sm leading-tight">{{ item.name }}</h3>
                    <p v-if="item.details" class="text-xs text-gray-500 mt-0.5">{{ item.details }}</p>
                </div>
                <div class="flex justify-between items-end mt-2">
                    <span class="text-xs font-bold text-gray-400 bg-gray-100 px-2 py-1 rounded-md">x{{ item.quantity }}</span>
                    <span class="font-bold text-gray-900">{{ (item.price * item.quantity).toFixed(2) }} ₴</span>
                </div>
            </div>
        </div>
      </div>
    </div>

    <div class="p-5 bg-white border-t shadow-[0_-10px_40px_rgba(0,0,0,0.05)]">
        <div class="space-y-4">
            <div class="space-y-1">
                <div class="flex justify-between items-center text-gray-500 text-sm" v-if="useBonuses">
                    <span>Сума замовлення:</span>
                    <span>{{ totalSum.toFixed(2) }} ₴</span>
                </div>
                <div class="flex justify-between items-center text-green-600 text-sm font-bold" v-if="useBonuses && selectedCustomer">
                    <span>Списано бонусів:</span>
                    <span>- {{ Math.min(totalSum, Number(selectedCustomer.bonus_balance)).toFixed(2) }} ₴</span>
                </div>
                <div class="flex justify-between items-end">
                    <span class="text-gray-500 font-bold">До сплати:</span>
                    <span class="text-3xl font-black text-gray-900">{{ finalTotal.toFixed(2) }} ₴</span>
                </div>
            </div>

            <div class="flex gap-2">
                <button @click="paymentMethod='cash'" :class="paymentMethod==='cash' ? 'bg-green-100 text-green-700 border-green-500 ring-1 ring-green-500' : 'bg-white border-gray-300 hover:bg-gray-50'" class="flex-1 py-2.5 border rounded-lg font-bold transition flex items-center justify-center gap-2 text-sm">
                    <i class="fas fa-money-bill-wave"></i> Готівка
                </button>
                <button @click="paymentMethod='card'" :class="paymentMethod==='card' ? 'bg-blue-100 text-blue-700 border-blue-500 ring-1 ring-blue-500' : 'bg-white border-gray-300 hover:bg-gray-50'" class="flex-1 py-2.5 border rounded-lg font-bold transition flex items-center justify-center gap-2 text-sm">
                    <i class="fas fa-credit-card"></i> Картка
                </button>
            </div>

            <button 
                @click="handleCheckout"
                :disabled="cartItems.length === 0 || isProcessing"
                class="w-full py-3.5 bg-purple-600 text-white rounded-xl font-bold text-lg hover:bg-purple-700 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] transition flex items-center justify-center gap-2"
            >
                <span v-if="isProcessing"><i class="fas fa-spinner fa-spin"></i></span>
                <span v-else>Оплатити {{ finalTotal.toFixed(2) }} ₴</span>
            </button>
        </div>
    </div>
  </div>
</template>