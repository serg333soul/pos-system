<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useWarehouse } from '@/composables/useWarehouse'
import { useSupplies } from '@/composables/useSupplies'

const props = defineProps({
    isOpen: Boolean,
    item: Object,       // Об'єкт товару/інгредієнта
    entityType: String  // 'ingredient', 'consumable', 'product_variant', 'product'
})

const emit = defineEmits(['close', 'adjusted'])

const { adjustItemStock } = useWarehouse()
const { fetchAvailableBatches } = useSupplies()

// Стан форми
const actualQuantity = ref(0)
const reason = ref('')
const comment = ref('')
const batchId = ref(null)

const availableBatches = ref([])
const isLoading = ref(false)
const isSubmitting = ref(false)

// Типові причини
const reasons = [
    "Псування / Брак",
    "Розбито / Пролито",
    "Помилка інвентаризації",
    "Знайдений лишок",
    "Крадіжка",
    "Списання на потреби закладу",
    "Інше"
]

// Обчислення різниці
const currentQuantity = computed(() => {
  // 🛡 Захищаємо від відсутності item або одиниці виміру
  return props.item?.stock_quantity ?? 0;
})

const difference = computed(() => {
    return Number((actualQuantity.value - currentQuantity.value).toFixed(3))
})

const isFifo = computed(() => {
  return props.item?.costing_method === 'fifo';
})

// Завантаження даних при відкритті
watch(() => props.isOpen, async (isOpen) => {
    if (isOpen && props.item) {
        // Скидаємо форму до значень системи
        actualQuantity.value = currentQuantity.value
        reason.value = ''
        comment.value = ''
        batchId.value = null
        availableBatches.value = []

        // Якщо це FIFO, одразу вантажимо активні партії
        if (isFifo.value) {
            isLoading.value = true
            availableBatches.value = await fetchAvailableBatches(props.entityType, props.item.id)
            isLoading.value = false
        }
    }
})

// Збереження
const handleSave = async () => {
    // 🛡 ЗАХИСТ: Якщо об'єкт не прокинувся, не даємо впасти скрипту
    if (!props.item || !props.item.id) {
        console.error("❌ Помилка: спроба зберегти коригування для undefined товару");
        return;
    }

    if (difference.value === 0) return alert("Немає змін для збереження. Фактичний залишок дорівнює системному.")
    if (!reason.value) return alert("Оберіть причину коригування!")
    
    // Якщо FIFO і це НЕСТАЧА (< 0) - вимагаємо вибрати партію
    if (isFifo.value && difference.value < 0 && !batchId.value) {
        return alert("Для товару FIFO обов'язково оберіть партію, з якої списується нестача!")
    }

    const fullReason = comment.value ? `${reason.value} - ${comment.value}` : reason.value

    isSubmitting.value = true
    const payload = {
        entity_type: props.item.type || 'ingredient', 
        entity_id: props.item.id,
        actual_quantity: actualQuantity.value,
        reason: reason.value,
        batch_id: isFifo.value ? batchId.value : null
    }

    const result = await adjustItemStock(payload)
    isSubmitting.value = false

    if (result.success) {
        emit('adjusted')
        emit('close')
    } else {
        alert("Помилка збереження: " + result.error)
    }
}

// Допоміжна функція форматування дати
const formatDate = (dateStr) => {
    if (!dateStr) return '---'
    const d = new Date(dateStr)
    return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth()+1).toString().padStart(2, '0')}.${d.getFullYear()}`
}

onMounted(() => {
  console.log("🏠 Модалка змонтована з item:", props.item?.id, "Type:", props.entityType);
  if (isFifo.value) {
    fetchAvailableBatches(); // Переконайся, що ця функція не зависає
  }
})

</script>

<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div class="bg-white rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
                
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h3 class="text-xl font-black text-gray-800">
                        {{ item?.display_name || item?.name || 'Завантаження...' }}
                        </h3>
                        <p class="text-xs text-gray-400 font-bold uppercase tracking-wider">
                        ⚖️ Коригування залишку
                        </p>
                    </div>
                    <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>

                <div class="p-6 space-y-6">
                    <div class="flex justify-between items-center bg-blue-50/50 border border-blue-100 p-4 rounded-xl">
                        <div>
                            <div class="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-1">Метод обліку</div>
                            <span class="text-xs font-bold px-2 py-1 rounded-full uppercase" 
                                  :class="isFifo ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'">
                                {{ isFifo ? 'FIFO (По партіях)' : 'WAC (Середня ціна)' }}
                            </span>
                        </div>
                        <div class="text-right">
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Системний залишок</div>
                            <div class="text-xl font-mono font-bold text-gray-700">{{ currentQuantity }} {{ item?.unit?.symbol || 'од.' }}</div>
                        </div>
                    </div>

                    <div class="relative">
                        <label class="block text-sm font-bold text-gray-700 mb-2">Фактичний залишок (на полиці)</label>
                        <input 
                            v-model.number="actualQuantity" 
                            type="number" 
                            step="0.01" 
                            class="w-full border-2 border-gray-200 p-4 rounded-xl text-2xl font-mono text-center focus:border-blue-500 focus:ring-0 transition outline-none"
                        >
                        <div v-if="difference !== 0" class="absolute -bottom-6 left-0 right-0 text-center text-sm font-bold animate-fade-in"
                             :class="difference > 0 ? 'text-green-600' : 'text-red-500'">
                            Різниця: {{ difference > 0 ? '+' : '' }}{{ difference }} {{ item?.unit?.symbol || 'од.' }}
                            ({{ difference > 0 ? 'Лишок' : 'Нестача' }})
                        </div>
                    </div>

                    <div v-if="isFifo && difference < 0" class="bg-red-50 p-4 rounded-xl border border-red-100 animate-fade-in mt-8">
                        <label class="block text-xs font-bold text-red-800 uppercase mb-2">З якої партії списати нестачу?</label>
                        <div v-if="isLoading" class="text-xs text-red-600"><i class="fas fa-spinner fa-spin mr-1"></i> Завантаження...</div>
                        <div v-else-if="availableBatches.length === 0" class="text-xs text-red-600">Немає активних партій! Створіть постачання.</div>
                        <select v-else v-model="batchId" class="w-full p-2.5 rounded-lg border border-red-200 bg-white text-sm outline-none focus:ring-2 focus:ring-red-200">
                            <option :value="null" disabled>-- Оберіть партію --</option>
                            <option v-for="b in availableBatches" :key="b.batch_id" :value="b.batch_id">
                                Партія від {{ formatDate(b.supply_date) }} (Залишок: {{ b.remaining_quantity }})
                            </option>
                        </select>
                    </div>

                    <div class="space-y-4 pt-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Причина *</label>
                            <select v-model="reason" class="w-full border p-3 rounded-xl bg-gray-50 focus:bg-white outline-none">
                                <option value="" disabled>-- Оберіть причину --</option>
                                <option v-for="r in reasons" :key="r" :value="r">{{ r }}</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Деталі (Опціонально)</label>
                            <input v-model="comment" type="text" placeholder="Хто розбив, де знайшли і т.д." class="w-full border p-3 rounded-xl bg-gray-50 focus:bg-white outline-none">
                        </div>
                    </div>
                </div>

                <div class="p-6 border-t border-gray-100 bg-gray-50 flex gap-3">
                    <button @click="emit('close')" class="flex-1 py-3 font-bold text-gray-500 hover:bg-gray-200 rounded-xl transition">
                        Скасувати
                    </button>
                    <button 
                        @click="handleSave" 
                        :disabled="isSubmitting || difference === 0 || !reason"
                        class="flex-1 py-3 font-bold text-white rounded-xl shadow-lg transition"
                        :class="isSubmitting || difference === 0 || !reason ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 shadow-blue-200'"
                    >
                        {{ isSubmitting ? 'Збереження...' : 'Підтвердити' }}
                    </button>
                </div>

            </div>
        </div>
    </Teleport>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }
</style>