<template>
  <RouterLink to="/">
    <div class="logo">
      <div v-if="!collapsed" class="logo__text">
        Senior Homecare Hub
      </div>
    </div>
  </RouterLink>
</template>

<script lang="ts">
import IconLogo from '~icons/material-symbols-light/blur-on'

export default defineComponent({
  name: 'Logo',
  components: {
    IconLogo,
  },
  props: {
    collapsed: Boolean,
  },
  setup() {
    return {}
  },
})
</script>

<style lang="sass" scoped>
.logo
    height: 60px
    display: flex
    gap: 0px
    padding: 0px
    margin-top: 0px
    font-size: 28px
    font-weight: 400
    color: white
    align-items: center
    background-color: $primary-color
    justify-content: center

    &__icon
        display: flex
        align-items: center
        font-size: 28px

    &__text
        overflow: hidden
        word-wrap: break-word
</style>
