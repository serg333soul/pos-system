<script setup>
import { ref } from 'vue';
import { useWarehouse } from '@/composables/useWarehouse';

const { productRooms, createItem, deleteItem } = useWarehouse();
const newRoom = ref({ name: '', description: '' });

const handleCreate = async () => {
  if (!newRoom.value.name) return alert("Вкажіть назву кімнати");
  const success = await createItem('/api/product_rooms/', newRoom.value);
  if (success) newRoom.value = { name: '', description: '' };
};
</script>

<template>
  <div class="p-6">
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-8">
      <h3 class="text-lg font-bold mb-4">📂 Створити нову кімнату</h3>
      <div class="flex gap-4">
        <input v-model="newRoom.name" type="text" placeholder="Назва (напр. Кава Delicate)" class="flex-1 border p-2 rounded-xl">
        <input v-model="newRoom.description" type="text" placeholder="Опис" class="flex-1 border p-2 rounded-xl">
        <button @click="handleCreate" class="bg-purple-600 text-white px-6 py-2 rounded-xl font-bold">Створити</button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div v-for="room in productRooms" :key="room.id" class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h4 class="font-bold text-xl text-purple-700">{{ room.name }}</h4>
            <p class="text-gray-400 text-sm">{{ room.description }}</p>
          </div>
          <button @click="deleteItem(`/api/product_rooms/${room.id}`)" class="text-red-400 hover:text-red-600">Видалити</button>
        </div>
        
        <div class="bg-gray-50 p-4 rounded-xl">
          <p class="text-xs font-bold text-gray-400 uppercase mb-2">Товари в кімнаті:</p>
          <ul v-if="room.products?.length" class="space-y-1">
            <li v-for="p in room.products" :key="p.id" class="text-sm flex justify-between">
              <span>{{ p.name }}</span>
              <span class="font-bold text-gray-400">{{ p.price }} ₴</span>
            </li>
          </ul>
          <p v-else class="text-sm text-gray-300 italic">Порожньо</p>
        </div>
      </div>
    </div>
  </div>
</template>