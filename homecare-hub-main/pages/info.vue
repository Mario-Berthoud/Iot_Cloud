<template>
  <div style="height: 100%;">
    <NuxtLayout name="table">
      <template #mainContent>
        <PrimeDataTable sortField="timestamp" :sortOrder="-1" v-model:expandedRows="expandedRows" :value="infos"
          scrollable scrollHeight="100%"
          :pt="{ root: { style: 'overflow: hidden; height: 100%; max-height: 100%;' }, tableContainer: { style: 'overflow: auto; height: calc(100% - 30px); max-height: 100%;' } }">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="text-xl font-bold">Latest Information</span>
            </div>
          </template>
          <PrimeColumn expander style="width: 5rem;" />
          <PrimeColumn field="timestamp" header="Time" style="width: 20%;">
            <template #body="slotProps">
              {{ translateDate(slotProps.data.timestamp) }}
            </template>
          </PrimeColumn>
          <PrimeColumn field="summary" header="Summary" style="width: 60%;"></PrimeColumn>
          <PrimeColumn field="level" header="Severity" style="width: 20%; text-align: center;"
            :pt="{ columnHeaderContent: { style: 'justify-content: center;' } }">
            <template #body="slotProps">
              <PrimeTag :value="translateLevel(slotProps.data.level)"
                :severity="translateSeverity(slotProps.data.level)" />
            </template>
          </PrimeColumn>
          <PrimeColumn style="width: 5rem;" header="Action">
            <template #body="slotProps">
              <PrimeButton class="pi pi-trash" @click="deleteInfo(slotProps.data.timestamp)"
                :pt="{ label: { style: 'display: none;' }, root: { style: 'width: 100%;' } }" />
            </template>
          </PrimeColumn>
          <template #expansion="slotProps">
            <h5> More details </h5>
            <p>{{ slotProps.data.detail }} </p>
          </template>

        </PrimeDataTable>
      </template>
    </NuxtLayout>
  </div>
</template>
<script setup lang="ts">
import 'primeicons/primeicons.css';
import { ref, onMounted, onBeforeUnmount } from 'vue';
const expandedRows = ref();
const infos = ref();

let timer: NodeJS.Timeout;

function translateDate(timestamp: number) {
  let date = new Date(timestamp);
  return date.toLocaleString("de-DE", { timeZone: "Europe/Berlin" })
}

function fetchInfos() {
  try {
    $fetch("/api/info").then((data) => {
      infos.value = data
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
  fetchInfos();
  timer = setInterval(fetchInfos, 30000);
})

const deleteInfo = (timestamp: number) => {
  $fetch("/api/info",
    {
      "method": "DELETE",
      "body": {
        "timestamp": timestamp
      }
    }).then((res) => {
      $fetch("/api/info").then((res) => {
        infos.value = res
      })
    })
}

function translateLevel(lvl: number) {
  switch (lvl) {
    case 0: {
      return "LOW"
    }
    case 1: {
      return "MEDIUM"
    }
    case 2: {
      return "HIGH"
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
