<template>
  <div id="app">
    <router-view v-slot="{ Component }">
      <transition name="ios-page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <Toast />
    <GlobalConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Toast from '@/components/ui/Toast.vue'
import GlobalConfirmDialog from '@/components/GlobalConfirmDialog.vue'
import { useTheme } from '@/composables/useTheme'
import { authAPI } from '@/api'

const router = useRouter()
const route = useRoute()
const { initTheme } = useTheme()

const showSecurityWarning = ref(false)
provide('showSecurityWarning', showSecurityWarning)

onMounted(async () => {
  initTheme()
  if (route.path !== '/') return

  try {
    const data = await authAPI.status()
    if (!data.is_local && !data.authenticated) {
      router.replace('/login')
    } else if (data.remote_access_enabled && !data.auth_enabled) {
      showSecurityWarning.value = true
    }
  } catch {}
})
</script>

<style>
@import '@/assets/styles/ios-theme.css';

#app {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: var(--ios-bg-primary);
}

.ios-page-enter-active,
.ios-page-leave-active {
  transition: opacity 0.2s ease;
}

.ios-page-enter-from,
.ios-page-leave-to {
  opacity: 0;
}
</style>
