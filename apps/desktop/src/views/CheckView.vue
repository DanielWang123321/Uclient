<script setup lang="ts">
import RobotPanel from '../components/RobotPanel.vue'
import TcpPanel from '../components/TcpPanel.vue'
import PayloadPanel from '../components/PayloadPanel.vue'
import Viewport from '../components/Viewport.vue'
import MotionBar from '../components/MotionBar.vue'
import InfoPanel from '../components/InfoPanel.vue'
</script>

<template>
  <div class="check">
    <aside class="left">
      <RobotPanel />
      <el-divider />
      <TcpPanel />
      <el-divider />
      <PayloadPanel />
    </aside>
    <main class="center">
      <div class="vp"><Viewport /></div>
      <MotionBar />
    </main>
    <aside class="right">
      <InfoPanel />
    </aside>
  </div>
</template>

<style scoped>
.check { display: grid; grid-template-columns: 250px 1fr 330px; height: 100%; min-height: 0; }
.left, .right { background: var(--uc-panel-bg); overflow-y: auto; padding: 4px 12px 12px; }
.left { border-right: 1px solid var(--uc-border); }
.right { border-left: 1px solid var(--uc-border); }
.center { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.vp { position: relative; flex: 1; min-height: 0; }
:deep(.el-divider--horizontal) { margin: 10px 0; }
</style>
