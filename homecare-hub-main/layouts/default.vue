<template>
  <div class="layout u-p-10px">
    <div class="layout__main">
      <div class="layout__main__page">
        <Logo class="navbar-mobile__logo" />
        <!-- <Topbar class="u-sticky u-top-60.9px u-mt-60px md:u-top-0 md:u-mt-0 u-z-1" :back-invisible="topBackInvisible" -->
        <!--   :back-to="topBackTo"> -->
        <!--   <template #pageTitle> -->
        <!--     <slot name="pageTitle"> -->
        <!--       CAPS' Cloud Computing Exercise Website -->
        <!--     </slot> -->
        <!--   </template> -->
        <!-- </Topbar> -->
      </div>
      <div
        class="layout__main__page__content u-p-15px u-grid u-gap-10px u-place-items-center xs:u-grid-cols-1 sm:u-grid-cols-2 sm:u-grid-rows-2">
        <slot name="mainContent"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAttrs } from 'vue';

const layoutProps = useAttrs()
const topBackInvisible = layoutProps.top_back_invisible || false
const topBackTo = layoutProps.top_back_to
</script>

<style lang="sass" scoped>
.layout
    height: 100vh
    background-color: #fff

    &__main
      flex: 1
      height: 100%
      justify-content: center
      border: 1px solid $primary_color

      &__page
        max-width: 100%
        flex: 1
        border: 1px solid #E5E5E5

        &__content
          height: calc(100% - 60px)

.navbar-mobile
    // display: flex
    justify-content: center
    padding: 0px
    width: 100%
    height: 60px
    position: relative
    background-color: $primary-color

    &__btn
        position: absolute
        width: 40px
        height: 40px
        left: 10px
        padding: 0 8px
        color: #fff
        font-size: 20px
        border-radius: $corner-radius

    &__logo
        padding: 0px
        scale: 0.8

    &__sidebar
        width: auto
        position: relative
        display: flex
        height: 100% !important
        border-radius: $corner-radius
</style>
