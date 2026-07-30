<template>
  <header class="ios-navbar ios-glass">
    <div class="navbar-left">
      <slot name="left" />
    </div>
    <h1 class="navbar-title">{{ title }}</h1>
    <div class="navbar-right">
      <slot name="right" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.ios-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 16px;
  z-index: 999;
  border-bottom: 0.5px solid var(--ios-separator);
}

.navbar-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 17px;
  font-weight: 600;
  color: var(--ios-text-primary);
  margin: 0;
  white-space: nowrap;
  letter-spacing: -0.3px;
  font-family: var(--ios-font);
}

.navbar-left,
.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 60px;
  z-index: 1;
}

.navbar-right {
  justify-content: flex-end;
}
</style>
