<template>
  <div class="ios-page">
    <IosNavBar title="Chat">
      <template #right>
        <button class="navbar-btn" @click="$router.push('/login')" title="Logout">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </template>
    </IosNavBar>
    <div class="page-body">
      <ChatWindow />
    </div>
    <IosTabBar v-model="activeTab" @update:modelValue="onTabChange" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import IosNavBar from '@/components/layout/IosNavBar.vue'
import IosTabBar from '@/components/layout/IosTabBar.vue'
import ChatWindow from '@/modules/chat/ChatWindow.vue'

const router = useRouter()
const activeTab = ref('chat')

function onTabChange(tab: string) {
  activeTab.value = tab
  if (tab === 'wiki') router.push('/wiki')
  else if (tab === 'face') router.push('/face-auth')
  else if (tab === 'settings') router.push('/settings')
  else if (tab === 'chat') router.push('/')
}
</script>

<style scoped>
.ios-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: var(--ios-bg-primary);
}

.page-body {
  flex: 1;
  padding-top: 44px;
  padding-bottom: 84px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.page-body :deep(.chat-window) {
  height: 100% !important;
  min-height: 0 !important;
}

.navbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: var(--ios-fill-secondary);
  color: var(--ios-blue);
  cursor: pointer;
  transition: background 0.15s;
}

.navbar-btn:hover {
  background: var(--ios-fill-primary);
}
</style>
