<template>
  <nav class="ios-tabbar ios-glass">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="tabbar-item"
      :class="{ active: modelValue === tab.id }"
      @click="$emit('update:modelValue', tab.id)"
    >
      <span class="tabbar-icon" v-html="tab.icon"></span>
      <span class="tabbar-label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
}>()

defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const tabs = [
  {
    id: 'chat',
    label: 'Chat',
    icon: `<svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  },
  {
    id: 'wiki',
    label: 'Wiki',
    icon: `<svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
  },
  {
    id: 'face',
    label: 'Face ID',
    icon: `<svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z"/><path d="M12 14c-3.3 0-6 1.8-6 4v1h12v-1c0-2.2-2.7-4-6-4z"/><circle cx="9" cy="8" r="1"/><circle cx="15" cy="8" r="1"/></svg>`,
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: `<svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`,
  },
]
</script>

<style scoped>
.ios-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 84px;
  padding: 0 8px 20px;
  z-index: 1000;
  border-top: 0.5px solid var(--ios-separator);
}

.tabbar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  min-width: 64px;
  padding: 4px 0;
  border: none;
  background: none;
  color: var(--ios-text-secondary);
  cursor: pointer;
  transition: color 0.2s ease;
  font-family: var(--ios-font);
}

.tabbar-item.active {
  color: var(--ios-blue);
}

.tabbar-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.tabbar-label {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: -0.1px;
}
</style>
