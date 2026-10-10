<script setup lang="ts">
import RobotPanel from '../components/RobotPanel.vue'
import TcpPanel from '../components/TcpPanel.vue'
import PayloadPanel from '../components/PayloadPanel.vue'
import StatusPanel from '../components/StatusPanel.vue'
import JogPanel from '../components/JogPanel.vue'
import TorquePanel from '../components/TorquePanel.vue'
import Viewport from '../components/Viewport.vue'
</script>

<template>
  <div class="check">
    <aside class="left">
      <RobotPanel />
      <el-divider />
      <TcpPanel />
      <el-divider />
      <PayloadPanel />
      <el-divider />
      <StatusPanel />
    </aside>
    <main class="center"><Viewport /></main>
    <aside class="right">
      <JogPanel />
      <el-divider />
      <TorquePanel />
    </aside>
  </div>
</template>

<style scoped>
.check { display: grid; grid-template-columns: 250px 1fr 330px; height: 100%; min-height: 0; }
.left, .right { background: var(--uc-panel-bg); overflow-y: auto; padding: 4px 12px 12px; }
.left { border-right: 1px solid var(--uc-border); }
.right { border-left: 1px solid var(--uc-border); }
.center { position: relative; min-width: 0; }
:deep(.el-divider--horizontal) { margin: 10px 0; }
</style>
