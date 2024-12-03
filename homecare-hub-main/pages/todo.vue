<template>
  <div style="height: 100%;">
    <NuxtLayout name="table">
      <template #mainContent>
        <PrimeDataTable sortField="level" scrollable scrollHeight="100%" :sortOrder="-1"
          v-model:expandedRows="expandedRows" :value="todos"
          :pt="{ root: { style: 'overflow: hidden; height: 100%; max-height: 100%;' }, tableContainer: { style: 'overflow: auto; height: calc(100% - 30px); max-height: 100%;' } }">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="text-xl font-bold">Current To-Dos</span>
            </div>
          </template>
          <PrimeColumn expander style="width: 5rem;" />
          <PrimeColumn field="timestamp" header="Time" style="width: 20%;">
            <template #body="slotProps">
              {{ translateDate(slotProps.data.timestamp) }}
            </template>
          </PrimeColumn>
          <PrimeColumn field="titel" header="Summary" style="width: 60%;"></PrimeColumn>
          <PrimeColumn field="level" header="Severity" style="width: 20%; text-align: center;"
            :pt="{ columnHeaderContent: { style: 'justify-content: center;' } }">
            <template #body="slotProps">
              <PrimeTag :value="translateLevel(slotProps.data.level)"
                :severity="translateSeverity(slotProps.data.level)" />
            </template>
          </PrimeColumn>
          <PrimeColumn style="width: 5rem;" header="Action">
            <template #body="slotProps">
              <PrimeButton class="pi pi-trash" @click="deleteTodo(slotProps.data.timestamp)"
                :pt="{ label: { style: 'display: none;' }, root: { style: 'width: 100%;' } }" />
            </template>
          </PrimeColumn>
          <template #expansion="slotProps">
            <h5> More Details</h5>
            <p>{{ slotProps.data.msg }} </p>
          </template>

        </PrimeDataTable>
      </template>
    </NuxtLayout>
  </div>
</template>
<script setup lang="ts">
import 'primeicons/primeicons.css'
import { ref, onMounted } from 'vue';
const expandedRows = ref();
const todos = ref();

let timer: NodeJS.Timeout;

function translateDate(timestamp: number) {
  let date = new Date(timestamp);
  return date.toLocaleString("de-DE", { timeZone: "Europe/Berlin" })
}
function fetchTodos() {
  try {
    $fetch("/api/todo").then((data) => {
      todos.value = data
    }).catch((err) => {
    })
  } catch (err) {
    console.error(`Failed to fetch from remote... ${err}`)
  }
}

onBeforeUnmount(() => {
  clearInterval(timer)
})

onBeforeRouteLeave(() => {
  clearInterval(timer)
})

onMounted(() => {
  fetchTodos();
  timer = setInterval(fetchTodos, 30000);
})



const deleteTodo = (timestamp: number) => {
  $fetch("/api/todo",
    {
      "method": "DELETE",
      "body": {
        "timestamp": timestamp
      }
    }).then((res) => {
      $fetch("/api/info").then((res) => {
        todos.value = res
      })
    })
}

function translateLevel(lvl: number) {
  switch (lvl) {
    case 0: {
      return "NORMAL"
    }
    case 1: {
      return "IMPORTANT"
    }
    case 2: {
      return "ALERT"
    }
    default: {
      return `Outside of range [${lvl}]`
    }
  }
}

function translateSeverity(lvl: number) {
  switch (lvl) {
    case 0: {
      return "info"
    }
    case 1: {
      return "warn"
    }
    case 2: {
      return "danger"
    }
    default: {
      return "secondary"
    }
  }

}

definePageMeta({
  layout: "table",
  layoutTransition: {
    name: "table"
  },
})
</script>
<style scoped></style>
