import { ref } from 'vue'

export function useFinance() {
    const accounts = ref([])
    const categories = ref([])
    const activeShift = ref(null)
    const transactions = ref([])
    const isLoading = ref(false)
    const pnlReport = ref(null)

    // --- БАЗОВІ ДАНІ ---
    const fetchAccounts = async () => {
        try {
            const res = await fetch('/api/finance/accounts/')
            if (res.ok) accounts.value = await res.json()
        } catch (e) { console.error("Помилка завантаження рахунків:", e) }
    }

    const fetchCategories = async () => {
        try {
            const res = await fetch('/api/finance/categories/')
            if (res.ok) categories.value = await res.json()
        } catch (e) { console.error("Помилка завантаження категорій:", e) }
    }

    // 🔥 НОВА ФУНКЦІЯ: Завантаження історії транзакцій
    const fetchTransactions = async (accountId = null) => {
        isLoading.value = true
        try {
            let url = '/api/finance/transactions/'
            if (accountId) url += `?account_id=${accountId}`
            
            const res = await fetch(url)
            if (res.ok) {
                transactions.value = await res.json()
            }
        } catch (e) { 
            console.error("Помилка завантаження транзакцій:", e) 
        } finally {
            isLoading.value = false
        }
    }

    const fetchPnlReport = async () => {
        isLoading.value = true
        try {
            const res = await fetch('/api/finance/report/pnl')
            if (res.ok) {
                pnlReport.value = await res.json()
            }
        } catch (e) { 
            console.error("Помилка завантаження P&L:", e) 
        } finally {
            isLoading.value = false
        }
    }

    // --- КАСОВІ ЗМІНИ ---
    const checkActiveShift = async () => {
        try {
            const res = await fetch('/api/finance/shifts/active')
            if (res.ok) {
                const data = await res.json()
                activeShift.value = data || null // null, якщо зміна закрита
            }
        } catch (e) { console.error("Помилка перевірки зміни:", e) }
    }

    const openShift = async (userId, openingBalance) => {
        isLoading.value = true
        try {
            const res = await fetch('/api/finance/shifts/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, opening_balance: openingBalance })
            })
            if (res.ok) {
                activeShift.value = await res.json()
                return true
            }
            const error = await res.json()
            alert(`Помилка: ${error.detail}`)
            return false
        } catch (e) {
            console.error("Помилка відкриття зміни:", e)
            return false
        } finally {
            isLoading.value = false
        }
    }

    const closeShift = async (shiftId, actualBalance, transferToSafe, cashAccountId, safeAccountId, userId) => {
        isLoading.value = true
        try {
            const res = await fetch(`/api/finance/shifts/${shiftId}/close?cash_account_id=${cashAccountId}&safe_account_id=${safeAccountId}&user_id=${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    closing_balance_actual: actualBalance,
                    transfer_to_safe_amount: transferToSafe
                })
            })
            if (res.ok) {
                activeShift.value = null
                return true
            }
            const error = await res.json()
            alert(`Помилка: ${error.detail}`)
            return false
        } catch (e) {
            console.error("Помилка закриття зміни:", e)
            return false
        } finally {
            isLoading.value = false
        }
    }

    // --- ТРАНЗАКЦІЇ (СЛУЖБОВЕ ВНЕСЕННЯ/ВИНЕСЕННЯ) ---
    const createTransaction = async (payload) => {
        isLoading.value = true
        try {
            const res = await fetch('/api/finance/transactions/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            if (res.ok) return true
            
            const error = await res.json()
            alert(`Помилка транзакції: ${error.detail}`)
            return false
        } catch (e) {
            console.error("Помилка транзакції:", e)
            return false
        } finally {
            isLoading.value = false
        }
    }

    return {
        accounts,
        categories,
        activeShift,
        transactions,
        pnlReport,
        isLoading,
        fetchAccounts,
        fetchCategories,
        checkActiveShift,
        openShift,
        closeShift,
        createTransaction,
        fetchTransactions,
        fetchPnlReport
    }
}