<template>
  <div class="ios-page">
    <IosNavBar title="Wiki">
      <template #right>
        <button class="navbar-btn" @click="syncWiki" title="同步索引">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>
      </template>
    </IosNavBar>
    <div class="page-body">
      <WikiPanel />
    </div>
    <IosTabBar v-model="activeTab" @update:modelValue="onTabChange" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import IosNavBar from '@/components/layout/IosNavBar.vue'
import IosTabBar from '@/components/layout/IosTabBar.vue'
import WikiPanel from '@/modules/wiki/WikiPanel.vue'

const router = useRouter()
const route = useRoute()
const activeTab = ref('wiki')

function onTabChange(tab: string) {
  activeTab.value = tab
  if (tab === 'chat') router.push('/')
  else if (tab === 'wiki') router.push('/wiki')
  else if (tab === 'face') router.push('/face-auth')
  else if (tab === 'settings') router.push('/settings')
}

onMounted(() => {
  const entrySlug = route.query.entry as string
  if (entrySlug) {
    const panel = document.querySelector('.wiki-panel')
    if (panel) {
      import('@/modules/wiki/services/wikiApi').then(({ wikiApi }) => {
        wikiApi.getEntry(entrySlug).then(entry => {
          const event = new CustomEvent('wiki-view-entry', { detail: entry })
          panel.dispatchEvent(event)
        }).catch(() => {})
      })
    }
  }
})

async function syncWiki() {
  try {
    const { wikiApi } = await import('@/modules/wiki/services/wikiApi')
    await wikiApi.syncIndex()
    window.location.reload()
  } catch {}
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
