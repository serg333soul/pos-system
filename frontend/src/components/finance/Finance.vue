<script setup>
import { ref, onMounted } from 'vue'
import { useFinance } from '@/composables/useFinance'

const { accounts, transactions, pnlReport, fetchAccounts, fetchTransactions, fetchPnlReport, isLoading } = useFinance()

// Вкладки: 'accounts' (Рахунки), 'transactions' (Історія), 'pnl' (Звіти)
const activeTab = ref('accounts')

onMounted(async () => {
    await fetchAccounts()
    await fetchTransactions()
    await fetchPnlReport()
})

// Допоміжна функція для іконок рахунків
const getAccountIcon = (type) => {
    if (type === 'cash') return 'fa-cash-register text-green-500 bg-green-100'
    if (type === 'bank') return 'fa-credit-card text-blue-500 bg-blue-100'
    if (type === 'safe') return 'fa-vault text-purple-500 bg-purple-100'
    return 'fa-wallet text-gray-500 bg-gray-100'
}

const getAccountName = (accountId) => {
    const acc = accounts.value.find(a => a.id === accountId)
    return acc ? acc.name : 'Невідомий рахунок'
}

const formatDate = (dateString) => {
    const date = new Date(dateString)
    // Додаємо локальний час замість UTC
    const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    return localDate.toLocaleString('uk-UA', { 
        day: '2-digit', month: '2-digit', year: 'numeric', 
        hour: '2-digit', minute: '2-digit' 
    })
}
</script>

<template>
  <div class="flex-1 ml-64 bg-gray-50 h-screen overflow-y-auto">
    <header class="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-10">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-3xl font-black text-gray-800">Управління фінансами</h2>
          <p class="text-gray-500 mt-1">Контроль рахунків, транзакцій та прибутку</p>
        </div>
        <button class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-bold transition shadow-lg flex items-center gap-2">
            <i class="fas fa-plus"></i> Новий рахунок
        </button>
      </div>

      <div class="flex gap-8 border-b border-gray-100">
        <button @click="activeTab = 'accounts'" :class="activeTab === 'accounts' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-800'" class="pb-4 font-bold border-b-2 transition">Рахунки та Баланси</button>
        <button @click="activeTab = 'transactions'" :class="activeTab === 'transactions' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-800'" class="pb-4 font-bold border-b-2 transition">Історія (Ledger)</button>
        <button @click="activeTab = 'pnl'" :class="activeTab === 'pnl' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-800'" class="pb-4 font-bold border-b-2 transition">P&L (Прибутки і збитки)</button>
      </div>
    </header>

    <main class="p-8">
      
      <div v-if="activeTab === 'accounts'" class="animate-fade-in-up">
        <div v-if="isLoading" class="text-center py-20 text-gray-400">
          <i class="fas fa-spinner fa-spin text-4xl mb-4"></i>
          <p>Завантаження рахунків...</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <div v-for="account in accounts" :key="account.id" class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm hover:shadow-md transition">
            <div class="flex items-start justify-between mb-8">
              <div :class="getAccountIcon(account.type)" class="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl">
                <i class="fas" :class="getAccountIcon(account.type).split(' ')[0]"></i>
              </div>
              <span class="bg-gray-100 text-gray-600 text-xs font-bold px-3 py-1 rounded-full uppercase">{{ account.type }}</span>
            </div>
            
            <h3 class="text-xl font-bold text-gray-800 mb-1">{{ account.name }}</h3>
            <p class="text-sm text-gray-400 mb-4">ID Рахунку: #{{ account.id }}</p>
            
            <div class="bg-gray-50 rounded-2xl p-4 border border-gray-100">
              <span class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Поточний баланс</span>
              <div class="flex items-baseline gap-1">
                <span class="text-3xl font-black text-gray-900">{{ Number(account.balance).toLocaleString('uk-UA') }}</span>
                <span class="text-lg font-bold text-gray-500">{{ account.currency }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'transactions'" class="bg-white rounded-3xl p-10 text-center border border-gray-100 text-gray-400">
        <i class="fas fa-list text-6xl mb-4 opacity-20"></i>
        <h3 class="text-xl font-bold text-gray-600">Історія транзакцій</h3>
        <div v-if="activeTab === 'transactions'" class="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm animate-fade-in-up">
        
        <div class="flex justify-between items-center mb-6">
            <h3 class="text-2xl font-bold text-gray-800">Історія операцій</h3>
            <button @click="fetchTransactions()" class="text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-2 transition">
                <i class="fas fa-sync-alt" :class="{'fa-spin': isLoading}"></i> Оновити
            </button>
        </div>

        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-500 text-sm border-b border-gray-100">
                        <th class="p-4 font-bold rounded-tl-2xl">Дата та Час</th>
                        <th class="p-4 font-bold">Рахунок</th>
                        <th class="p-4 font-bold">Деталі транзакції</th>
                        <th class="p-4 font-bold text-right rounded-tr-2xl">Сума</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="tx in transactions" :key="tx.id" class="border-b border-gray-50 hover:bg-gray-50 transition group">
                        
                        <td class="p-4 text-sm text-gray-500 font-medium">
                            {{ formatDate(tx.timestamp) }}
                        </td>
                        
                        <td class="p-4">
                            <span class="font-bold text-gray-700 bg-white px-3 py-1 border border-gray-200 rounded-lg shadow-sm">
                                {{ getAccountName(tx.account_id) }}
                            </span>
                        </td>
                        
                        <td class="p-4">
                            <div class="text-sm font-bold text-gray-800 mb-1">
                                {{ tx.description || 'Системна операція' }}
                            </div>
                            <div class="flex gap-2">
                                <span v-if="tx.reference_type === 'order'" class="text-[10px] font-bold uppercase tracking-wider bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded cursor-pointer hover:bg-yellow-200">
                                    Чек #{{ tx.reference_id }}
                                </span>
                                <span v-if="tx.reference_type === 'supply'" class="text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-700 px-2 py-0.5 rounded cursor-pointer hover:bg-blue-200">
                                    Постачання #{{ tx.reference_id }}
                                </span>
                            </div>
                        </td>
                        
                        <td class="p-4 text-right">
                            <span :class="tx.amount > 0 ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'" 
                                  class="px-3 py-1 rounded-xl font-black text-lg inline-block min-w-[100px] text-center">
                                {{ tx.amount > 0 ? '+' : '' }}{{ Number(tx.amount).toLocaleString('uk-UA') }} ₴
                            </span>
                        </td>
                    </tr>
                    
                    <tr v-if="transactions.length === 0">
                        <td colspan="4" class="p-12 text-center text-gray-400">
                            <i class="fas fa-receipt text-5xl mb-4 opacity-20"></i>
                            <p class="text-lg">Транзакцій поки немає</p>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
      </div>
      </div>

      <div v-if="activeTab === 'pnl'" class="bg-white rounded-3xl p-10 text-center border border-gray-100 text-gray-400">
        <i class="fas fa-chart-pie text-6xl mb-4 opacity-20"></i>
        <h3 class="text-xl font-bold text-gray-600">Звіт P&L</h3>
        <div v-if="activeTab === 'pnl'" class="animate-fade-in-up">
        
        <div class="flex justify-between items-center mb-6">
            <h3 class="text-2xl font-bold text-gray-800">Фінансовий звіт (P&L)</h3>
            <button @click="fetchPnlReport()" class="text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-2 transition">
                <i class="fas fa-sync-alt" :class="{'fa-spin': isLoading}"></i> Оновити
            </button>
        </div>

        <div v-if="pnlReport" class="space-y-6">
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm">
              <span class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 block">Загальний дохід</span>
              <div class="text-3xl font-black text-green-600">{{ Number(pnlReport.total_income).toLocaleString('uk-UA') }} ₴</div>
            </div>
            
            <div class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm">
              <span class="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 block">Загальні витрати</span>
              <div class="text-3xl font-black text-red-600">-{{ Number(pnlReport.total_expense).toLocaleString('uk-UA') }} ₴</div>
            </div>

            <div class="bg-indigo-600 rounded-3xl p-6 shadow-lg shadow-indigo-200 text-white">
              <span class="text-sm font-bold text-indigo-200 uppercase tracking-wider mb-2 block">Чистий прибуток (Net Profit)</span>
              <div class="text-4xl font-black">
                {{ pnlReport.net_profit > 0 ? '+' : '' }}{{ Number(pnlReport.net_profit).toLocaleString('uk-UA') }} ₴
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <div class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm">
              <h4 class="text-lg font-bold text-gray-800 mb-4 border-b border-gray-100 pb-2"><i class="fas fa-arrow-down text-green-500 mr-2"></i> Структура доходів</h4>
              <ul class="space-y-3">
                <li v-for="(amount, categoryName) in pnlReport.income" :key="categoryName" class="flex justify-between items-center bg-gray-50 px-4 py-3 rounded-xl">
                  <span class="font-medium text-gray-700">{{ categoryName }}</span>
                  <span class="font-bold text-green-600">{{ Number(amount).toLocaleString('uk-UA') }} ₴</span>
                </li>
                <li v-if="Object.keys(pnlReport.income).length === 0" class="text-gray-400 text-center py-4 text-sm">Доходів поки немає</li>
              </ul>
            </div>

            <div class="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm">
              <h4 class="text-lg font-bold text-gray-800 mb-4 border-b border-gray-100 pb-2"><i class="fas fa-arrow-up text-red-500 mr-2"></i> Структура витрат</h4>
              <ul class="space-y-3">
                <li v-for="(amount, categoryName) in pnlReport.expense" :key="categoryName" class="flex justify-between items-center bg-gray-50 px-4 py-3 rounded-xl">
                  <span class="font-medium text-gray-700">{{ categoryName }}</span>
                  <span class="font-bold text-red-600">-{{ Number(amount).toLocaleString('uk-UA') }} ₴</span>
                </li>
                <li v-if="Object.keys(pnlReport.expense).length === 0" class="text-gray-400 text-center py-4 text-sm">Витрат поки немає</li>
              </ul>
            </div>

          </div>
        </div>
      </div>
      </div>

    </main>
  </div>
</template>