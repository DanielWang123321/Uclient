import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import './styles/theme.scss'
import App from './App.vue'
import { i18n } from './i18n'

createApp(App).use(createPinia()).use(i18n).mount('#app')
