import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'

// 导入全局样式
import './assets/styles/variables.scss'
import './assets/styles/themes.scss'
import './assets/styles/page-layout.scss'
import './assets/styles/motion.scss'
import './assets/styles/surface-system.scss'
import './assets/styles/nav-accents.scss'
import './styles/workflow-domain-node.scss'
import './styles/vue-flow-custom-node-overrides.scss'

// 创建应用实例
const app = createApp(App)

// 安装 Pinia
const pinia = createPinia()
app.use(pinia)

// 安装 Vue Router
app.use(router)

// 安装 Element Plus
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default'
})

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err)
  console.error('Error info:', info)
}

// 全局警告处理
app.config.warnHandler = (msg, instance, trace) => {
  console.warn('Vue warning:', msg)
  console.warn('Trace:', trace)
}

// 挂载应用
app.mount('#app')
