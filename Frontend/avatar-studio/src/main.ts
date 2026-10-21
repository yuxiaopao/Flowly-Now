import { createApp } from 'vue'
import App from './App.vue'
import './styles.css'
import { installAvatarBridge } from './flowlyBridge'

const app = createApp(App).mount('#app')
installAvatarBridge(() => app.$.exposed?.capturePreferences?.())
