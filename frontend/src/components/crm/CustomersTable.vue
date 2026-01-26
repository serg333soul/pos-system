<script setup>
defineProps({
  customers: Array,
  loading: Boolean
})

const emit = defineEmits(['edit', 'delete', 'history'])
</script>

<template>
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
              <button @click="emit('history', c)" class="text-purple-400 hover:text-purple-600 transition px-2" title="Історія покупок">
                  <i class="fas fa-history"></i>
              </button>
              <button @click="emit('edit', c)" class="text-gray-400 hover:text-blue-500 transition px-2" title="Редагувати">
                  <i class="fas fa-pen"></i>
              </button>
              <button @click="emit('delete', c.id)" class="text-gray-400 hover:text-red-500 transition px-2" title="Видалити">
                  <i class="fas fa-trash"></i>
              </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>