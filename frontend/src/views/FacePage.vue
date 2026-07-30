<template>
  <div class="ios-page">
    <IosNavBar title="Face ID" />
    <div class="page-body">
      <FaceAuthPage />
    </div>
    <IosTabBar v-model="activeTab" @update:modelValue="onTabChange" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import IosNavBar from '@/components/layout/IosNavBar.vue'
import IosTabBar from '@/components/layout/IosTabBar.vue'
import FaceAuthPage from './FaceAuthPage.vue'

const router = useRouter()
const activeTab = ref('face')

function onTabChange(tab: string) {
  activeTab.value = tab
  if (tab === 'chat') router.push('/')
  else if (tab === 'wiki') router.push('/wiki')
  else if (tab === 'face') router.push('/face-auth')
  else if (tab === 'settings') router.push('/settings')
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
  overflow-y: auto;
  box-sizing: border-box;
}
</style>
