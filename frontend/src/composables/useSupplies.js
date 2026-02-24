import { ref } from 'vue'

export function useSupplies() {
    const suppliers = ref([])
    const supplies = ref([])
    const isLoading = ref(false)
    const error = ref(null)
    
    const fetchSuppliers = async () => {
    try {
        const res = await fetch('/api/supplies/suppliers/');
        if (res.ok) suppliers.value = await res.json();
    } catch (err) { console.error(err); }
    };

    const addSupplier = async (data) => {
        const res = await fetch('/api/supplies/suppliers/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        if (res.ok) {
            await fetchSuppliers();
            return await res.json();
        }
        const errorData = await res.json();
        console.error("Server error:", errorData);
        return null;
        }

    // Отримання історії постачань
    const fetchSupplies = async () => {
        isLoading.value = true
        try {
            const response = await fetch('/api/supplies/')
            if (!response.ok) throw new Error('Помилка завантаження постачань')
            supplies.value = await response.json()
        } catch (err) {
            error.value = err.message
            console.error(err)
        } finally {
            isLoading.value = false
        }
    }

    // Відправка нової накладної
    const createSupply = async (supplyData) => {
        isLoading.value = true
        try {
            const response = await fetch('/api/supplies/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(supplyData)
            })
            
            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || 'Помилка створення постачання')
            }
            
            return await response.json()
        } catch (err) {
            error.value = err.message
            console.error(err)
            throw err
        } finally {
            isLoading.value = false
        }
    }

    // Отримання доступних партій (знадобиться пізніше для Каси)
    const fetchAvailableBatches = async (entityType, entityId) => {
        try {
            // Формуємо URL з параметрами запиту
            const response = await fetch(`/api/supplies/batches/?entity_type=${entityType}&entity_id=${entityId}`)
            if (!response.ok) throw new Error('Помилка завантаження партій')
            
            return await response.json()
        } catch (err) {
            console.error("Помилка завантаження партій", err)
            return []
        }
    }

    return {
        suppliers,
        supplies,
        isLoading,
        error,
        fetchSuppliers,
        fetchSupplies,
        createSupply,
        addSupplier,
        fetchAvailableBatches
    }
}