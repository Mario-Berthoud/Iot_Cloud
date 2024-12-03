<template>
  <div class="topbar u-backdrop-blur-md u-z-100 u-shadow u-shadow-white">
    <div class="topbar__nav">
      <PrimeButton v-show="!backInvisible" :pt="{ root: { class: 'topbar__nav__button' } }" text severity="secondary"
        size="small" @click="routing">
        <IconBack v-if="backTo" />
        <IconClose v-else />
      </PrimeButton>
    </div>
    <div class="topbar__label">
      <slot name="pageTitle" />
    </div>
    <div class="topbar__actions">
      <slot name="pageActions" />
    </div>
  </div>
</template>

<script lang="ts">
import IconBack from '~icons/material-symbols-light/arrow-back-ios-new-rounded'
import IconClose from '~icons/material-symbols-light/close-rounded'

export default defineComponent({
  components: {
    IconBack,
    IconClose,
  },
  props: {
    label: String,
    backTo: String,
    backInvisible: Boolean,
  },
  emits: ['close'],
  setup() {
    return {}
  },
  methods: {
    routing() {
      if (this.backTo)
        this.$router.push(this.backTo)
      else
        this.$emit('close')
    },
  },
})
</script>

<style lang="sass">
.topbar
    height: auto
    background-color: #ffffffc7
    display: flex
    gap: 20px
    align-items: center
    padding: 20px 30px 10px 30px
    margin-bottom: 10px
    align-items: centery

    &__nav
        height: 35px

        &__button
            width: 35px
            height: 35px
            padding: 3px 0 0 0
            border-radius: $corner-radius
            background-color: $accent-color
            color: #333333
            font-size: 17px
            justify-content: center

    &__label
        margin-bottom: 4.5px
        font-size: 22px
        align-self: center

    &__actions
        display: flex
        height: 35px
        gap: 5px
        margin-left: auto
</style>
