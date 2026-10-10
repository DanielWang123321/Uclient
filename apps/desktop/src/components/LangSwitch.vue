<script setup lang="ts">
// Language switch, floating at the top right of the window (mockup .seg style on a dark pill).
import { useI18n } from 'vue-i18n'
const { locale } = useI18n()
</script>

<template>
  <div class="lang" data-test="lang-switch">
    <span :class="{ on: locale === 'zh' }" @click="locale = 'zh'">中</span>
    <span :class="{ on: locale === 'en' }" @click="locale = 'en'">EN</span>
  </div>
</template>

<style scoped>
.lang { display: inline-flex; background: #1f2023; border-radius: 10px; padding: 6px; gap: 2px; font-size: 13px; }
.lang span { padding: 6px 12px; color: #aab; cursor: pointer; border-radius: 6px; }
.lang .on { background: #3b6ef5; color: #fff; }
</style>
