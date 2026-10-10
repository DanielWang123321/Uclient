<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enLocale from 'element-plus/es/locale/lang/en'
import CheckView from './views/CheckView.vue'
import TrajectoryView from './views/TrajectoryView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { useEngineStore } from './stores/engine'
import { useRobotStore } from './stores/robot'

const { locale } = useI18n()
const engine = useEngineStore()
const robot = useRobotStore()
const tab = ref<'check' | 'trajectory' | 'workspace'>('check')
const elLocale = computed(() => (locale.value === 'zh' ? zhCn : enLocale))
watch(locale, (l) => localStorage.setItem('uclient.locale', l))

async function start() {
  if (await engine.connect()) {
    await robot.fetchRobots()
    await robot.load('uf850')
  }
}
onMounted(start)
</script>

<template>
  <el-config-provider :locale="elLocale" size="small">
    <div class="shell">
      <header class="top">
        <div class="brand"><span class="logo">U</span> Uclient <span class="tag">{{ $t('app.personal') }}</span></div>
        <el-segmented
          v-model="tab" :options="[
            { label: $t('tabs.check'), value: 'check' },
            { label: $t('tabs.trajectory'), value: 'trajectory' },
            { label: $t('tabs.workspace'), value: 'workspace' },
          ]"
        />
        <el-radio-group v-model="locale" size="small">
          <el-radio-button value="zh">中</el-radio-button>
          <el-radio-button value="en">EN</el-radio-button>
        </el-radio-group>
      </header>
      <section class="body">
        <CheckView v-show="tab === 'check'" />
        <TrajectoryView v-if="tab === 'trajectory'" />
        <WorkspaceView v-if="tab === 'workspace'" />
      </section>
      <footer class="status">
        <span :class="['dot', engine.status]"></span>
        <span data-test="engine-status">{{ $t(`engine.${engine.status}`) }}</span>
        <template v-if="engine.hello">
          <span class="num">core {{ engine.hello.core_version }} / ufactory_genesis {{ engine.hello.ufactory_genesis_commit }} / pinocchio {{ engine.hello.pinocchio_version }}</span>
        </template>
        <span v-if="engine.error" class="err">{{ engine.error }}</span>
        <el-button v-if="engine.status === 'error'" size="small" text @click="start">{{ $t('engine.retry') }}</el-button>
      </footer>
    </div>
  </el-config-provider>
</template>

<style scoped>
.shell { display: grid; grid-template-rows: 44px 1fr 26px; height: 100vh; }
.top { display: flex; align-items: center; justify-content: space-between; padding: 0 12px; background: #fff; border-bottom: 1px solid var(--uc-border); }
.brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.logo { display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 6px; background: var(--el-color-primary); color: #fff; font-size: 14px; }
.tag { font-weight: 400; font-size: 11px; color: #6e7781; }
.body { min-height: 0; }
.status { display: flex; align-items: center; gap: 10px; padding: 0 12px; font-size: 11px; background: #f6f8fa; border-top: 1px solid var(--uc-border); color: #57606a; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #999; }
.dot.connected { background: var(--uc-ok); }
.dot.connecting { background: var(--uc-warn); }
.dot.error { background: var(--uc-high); }
.err { color: var(--uc-high); }
</style>
