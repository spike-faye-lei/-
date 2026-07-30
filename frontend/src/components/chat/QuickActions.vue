<template>
  <div v-if="actions.length" class="quick-actions" :class="{ 'is-streaming': streaming }">
    <button
      v-for="action in visibleActions"
      :key="action.id"
      class="qa-btn"
      :class="[`qa-${action.style || 'secondary'}`]"
      :title="action.label"
      @click="handleAction(action)"
      :disabled="streaming"
    >
      <span v-if="action.icon" class="qa-icon">{{ action.icon }}</span>
      <span class="qa-label">{{ action.label }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface QuickAction {
  id: string
  label: string
  type: string
  icon?: string
  style?: 'primary' | 'secondary' | 'danger'
}

const props = defineProps<{
  actions: QuickAction[]
  streaming?: boolean
}>()

const emit = defineEmits<{
  (e: 'action', action: QuickAction): void
}>()

const visibleActions = computed(() => props.actions.slice(0, 6))

function handleAction(action: QuickAction) {
  if (!props.streaming) {
    emit('action', action)
  }
}
</script>

<style scoped>
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0 4px;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.quick-actions.is-streaming {
  opacity: 0.4;
  pointer-events: none;
}

.qa-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: 1px solid var(--color-border-primary, #3a3a3c);
  border-radius: 20px;
  background: var(--color-bg-secondary, #1c1c1e);
  color: var(--color-text-primary, #f5f5f7);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.qa-btn:hover {
  background: var(--color-bg-tertiary, #2c2c2e);
  border-color: var(--color-primary, #0a84ff);
  transform: translateY(-1px);
}

.qa-btn:active {
  transform: scale(0.96);
}

.qa-btn.qa-primary {
  background: var(--color-primary, #0a84ff);
  border-color: var(--color-primary, #0a84ff);
  color: #fff;
}

.qa-btn.qa-primary:hover {
  background: var(--color-primary-hover, #409cff);
}

.qa-btn.qa-danger {
  border-color: var(--color-danger, #ff453a);
  color: var(--color-danger, #ff453a);
}

.qa-icon {
  font-size: 15px;
  line-height: 1;
}

.qa-label {
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

/* iOS-style tap feedback */
@media (hover: none) {
  .qa-btn:hover {
    transform: none;
  }
  .qa-btn:active {
    background: var(--color-primary, #0a84ff);
    color: #fff;
    border-color: var(--color-primary, #0a84ff);
  }
}
</style>
