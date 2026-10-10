<script setup lang="ts">
// Engine connection status and language switch, tucked into the bottom of the left panel.
import { inject, ref } from 'vue'
import { useEngineStore } from '../stores/engine'
const showSettings = ref(false)
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
    <button class="settings" data-test="settings" @click="showSettings = true">⚙ {{ $t('settings.title') }}</button>
  </div>
  <div class="tag">{{ $t('app.personal') }}</div>
  <el-dialog v-model="showSettings" :title="$t('settings.title')" width="420px" class="dark-panel dark-dialog" append-to-body>
    <div class="placeholder" data-test="settings-dialog">{{ $t('settings.placeholder') }}</div>
  </el-dialog>
</template>

<style scoped>
.foot { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #9a9ca3; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #777; }
.dot.connected { background: #4cd28a; }
.dot.connecting { background: #d29922; }
.dot.error { background: #e5383b; }
.flex { flex: 1; }
.lnk { background: none; border: 0; color: #3b6ef5; cursor: pointer; font-size: 11px; }
.settings { background: #2a2b2f; color: #e6e7ea; border: 0; border-radius: 6px; padding: 5px 10px; font: inherit; font-size: 12px; cursor: pointer; }
.settings:hover { background: #34353a; }
.placeholder { color: #9a9ca3; padding: 24px 0; text-align: center; }
.tag { font-size: 10px; color: #6f7177; margin-top: 8px; }
</style>
