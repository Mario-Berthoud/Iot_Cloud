<template>
  <div>
    <NuxtLayout name="default">
      <template #pageTitle>
        Senior Homecare Hub
      </template>

      <template #mainContent>
        <PrimeButton class="p-button-reduced" label="To-Dos" as="router-link" to="/todo" />
        <PrimeButton class="p-button-reduced" label="Information" as="router-link" to="/info" />
        <PrimeButton class="p-button-reduced" label="SIF Status" as="router-link" to="/sif" />
        <PrimeButton class="p-button-reduced" label="Usage Information" />
      </template>
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">

</script>

<style lang="sass" scoped>
.p-button-reduced 
  width: 100%
  height: 100%
  place-self: center
  font-size: 5cap
  background-color: $secondary-color
</style>

<style lang="sass">
.p-button-label
  color: white
</style>
