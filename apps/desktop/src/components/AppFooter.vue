<script setup lang="ts">
// Engine connection status and language switch, tucked into the bottom of the left panel.
import { inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEngineStore } from '../stores/engine'
const { locale } = useI18n()
const engine = useEngineStore()
const retry = inject<() => void>('engine.retry', () => {})
</script>

<template>
  <div class="foot">
    <span :class="['dot', engine.status]" />
    <span data-test="engine-status" :title="engine.error || (engine.hello ? `core ${engine.hello.core_version} / ufactory_genesis ${engine.hello.ufactory_genesis_commit} / pinocchio ${engine.hello.pinocchio_version}` : '')">
      {{ $t(`engine.${engine.status}`) }}
    </span>
    <button v-if="engine.status === 'error'" class="lnk" @click="retry">{{ $t('engine.retry') }}</button>
    <span class="flex" />
    <div class="seg">
      <span :class="{ on: locale === 'zh' }" @click="locale = 'zh'">中</span>
      <span :class="{ on: locale === 'en' }" @click="locale = 'en'">EN</span>
    </div>
  </div>
  <div class="tag">{{ $t('app.personal') }}</div>
</template>

<style scoped>
.foot { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #9a9ca3; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #777; }
.dot.connected { background: #4cd28a; }
.dot.connecting { background: #d29922; }
.dot.error { background: #e5383b; }
.flex { flex: 1; }
.lnk { background: none; border: 0; color: #3b6ef5; cursor: pointer; font-size: 11px; }
.seg { display: inline-flex; background: #2a2b2f; border-radius: 5px; overflow: hidden; }
.seg span { padding: 3px 9px; color: #aab; cursor: pointer; }
.seg .on { background: #3b6ef5; color: #fff; }
.tag { font-size: 10px; color: #6f7177; margin-top: 8px; }
</style>
