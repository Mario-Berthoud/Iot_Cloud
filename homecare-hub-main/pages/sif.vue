<template>
  <div style="height: 100%;">
    <NuxtLayout name="table">
      <template #mainContent>
        <PrimeDataTable v-model:expandedRows="expandedRows" scrollable scrollHeight="100%" :value="infos"
          :pt="{ root: { style: 'overflow: hidden; height: 100%; max-height: 100%;' }, tableContainer: { style: 'overflow: auto; height: calc(100% - 30px); max-height: 100%;' } }">
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="text-xl font-bold">Latest SIF Status</span>
            </div>
          </template>
          <PrimeColumn expander style="width: 5rem;" />
          <PrimeColumn field="name" header="Name" style="width: 20%;" />
          <PrimeColumn field="subs" header="Subscriptions" style="width: 60%;">
            <template #body="slotProps">
              <PrimeTag v-for="item in slotProps.data.subs" :value="item" severity="info" />
            </template>
          </PrimeColumn>
          <PrimeColumn field="last_invoke" header="Last Invocation" style="width: 20%;">
            <template #body="slotProps">
              {{ translateDate(slotProps.data.last_invoke) }}
            </template>
          </PrimeColumn>
          <template #expansion="slotProps">
            <h5> Invocation Details </h5>
            <PrimeDataTable :value="slotProps.data.events" v-if="slotProps.data.events.length > 0">
              <PrimeColumn field="ready" header="Events Ready" style="width: 50%;">
                <template #body="slotProps">
                  <PrimeTag v-for="evt in slotProps.data.ready" :value="evt" severity="success" />
                </template>
              </PrimeColumn>
              <PrimeColumn field="waiting" header="Event Waiting Queue" style="width: 50%;">
                <template #body="slotProps">
                  <PrimeTag v-for="evt in slotProps.data.waiting" :value="evt" severity="warn" />
                </template>
              </PrimeColumn>
            </PrimeDataTable>
            <span v-else> This function is not waiting for any pending events... </span>
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

function translateDate(timestamp: number | null) {
  if (timestamp === null) {
    return "Never"
  }

  let date = new Date(timestamp);
  return date.toLocaleString("de-DE", { timeZone: "Europe/Berlin" })
}

function fetchInfos() {
  try {
    $fetch("/api/sif").then((data) => {
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

definePageMeta({
  layout: "table",
  layoutTransition: {
    name: "table"
  },
})
</script>
<style scoped></style>
