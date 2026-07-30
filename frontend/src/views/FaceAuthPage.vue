<template>
  <div class="face-auth-page" :class="{ dark: isDark }">
    <!-- 状态环 -->
    <section class="fa-status-section">
      <div class="status-ring" :class="ringClass">
        <div class="ring-outer">
          <div class="ring-inner">
            <span class="ring-icon">{{ ringIcon }}</span>
          </div>
        </div>
      </div>
      <p class="status-label">{{ statusLabel }}</p>
      <p v-if="guardAuthorizedUser" class="status-user">已授权: {{ guardAuthorizedUser }}</p>
    </section>

    <!-- 锁定横幅 -->
    <section v-if="kbLocked" class="fa-locked-banner">
      <span class="lock-icon">🔒</span>
      <span>知识库已锁定 · {{ guardCount }}/{{ guardThreshold }}</span>
      <button class="fa-btn fa-btn-sm fa-btn-primary" @click="unlock">解锁</button>
    </section>

    <div v-if="guardActive && !kbLocked" class="fa-guard-bar">
      <span class="guard-dot" />
      <span>守护中 · {{ guardCount }}/{{ guardThreshold }}</span>
      <button class="fa-btn fa-btn-sm fa-btn-danger" @click="stopGuard">停止</button>
    </div>

    <!-- 摄像头预览 -->
    <section class="fa-camera-card">
      <div class="fa-camera-area">
        <video ref="videoEl" autoplay playsinline muted class="fa-camera" :class="{ active: cameraActive }" />
        <div v-if="!cameraActive" class="camera-placeholder">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z"/><path d="M12 14c-3.3 0-6 1.8-6 4v1h12v-1c0-2.2-2.7-4-6-4z"/></svg>
          <span>摄像头未开启</span>
        </div>
        <canvas ref="canvasEl" class="fa-canvas" />
      </div>
      <div class="camera-actions">
        <button v-if="!cameraActive" class="fa-btn fa-btn-primary fa-btn-sm" @click="startCamera">开启摄像头</button>
        <template v-else>
          <button class="fa-btn fa-btn-sm" @click="stopCamera">关闭</button>
        </template>
      </div>
    </section>

    <!-- 录入人脸 -->
    <section class="fa-card">
      <div class="card-row">
        <input v-model="enrollName" class="fa-input" placeholder="输入用户名..." :disabled="enrolling" />
        <button
          class="fa-btn fa-btn-primary fa-btn-sm"
          :disabled="!cameraActive || enrolling || !enrollName"
          @click="startEnroll"
        >
          {{ enrolling ? `采集中 ${capturedFrames}/10` : '录入' }}
        </button>
      </div>
      <p v-if="enrollResult" class="fa-result">{{ enrollResult }}</p>
    </section>

    <!-- 已录入用户 -->
    <section class="fa-card">
      <h3 class="card-title">已录入用户</h3>
      <div v-if="enrolledUsers.length === 0" class="fa-empty">暂无用户</div>
      <div v-for="user in enrolledUsers" :key="user" class="fa-user-row">
        <span class="fa-user-avatar">👤</span>
        <span class="fa-user-name">{{ user }}</span>
        <button class="fa-btn fa-btn-sm fa-btn-danger" @click="remove(user)">移除</button>
      </div>
    </section>

    <!-- 活体检测 -->
    <section class="fa-card">
      <h3 class="card-title">活体检测</h3>
      <template v-if="!livenessActive && !livenessResult">
        <p class="fa-hint">开启摄像头后自动检测，按提示完成动作即可</p>
        <button class="fa-btn fa-btn-primary" :disabled="!cameraActive" @click="startAutoLiveness">
          {{ cameraActive ? '开始验证' : '请先开启摄像头' }}
        </button>
      </template>

      <div v-if="livenessActive" class="liveness-overlay">
        <div class="liveness-ring" :class="{ scanning: livenessScanning, detected: ringDetectedFlash }">
          <video ref="livenessVideoEl" autoplay playsinline muted class="liveness-video-ring" />
          <div class="ring-overlay">
            <div class="ring-progress" :style="{ strokeDashoffset: ringOffset }" />
          </div>
        </div>
        <p class="liveness-action-text">{{ currentActionText }}</p>
        <div v-if="liveBioData" class="live-bio-data">
          <div class="bio-row"><span>EAR 眨眼</span><span :class="liveBioData.blink ? 'bio-detect' : ''">{{ liveBioData.ear?.toFixed(2) || '--' }} {{ liveBioData.blink ? '⚡' : '' }}</span></div>
          <div class="bio-row"><span>MAR 张嘴</span><span :class="liveBioData.mouth_open ? 'bio-detect' : ''">{{ liveBioData.mar?.toFixed(2) || '--' }} {{ liveBioData.mouth_open ? '⚡' : '' }}</span></div>
          <div class="bio-row"><span>Yaw 左右</span><span>{{ liveBioData.yaw?.toFixed(0) || '--' }}°</span></div>
          <div class="bio-row"><span>Pitch 俯仰</span><span>{{ liveBioData.pitch?.toFixed(0) || '--' }}°</span></div>
          <div class="bio-row"><span>Roll 歪头</span><span>{{ liveBioData.roll?.toFixed(0) || '--' }}°</span></div>
          <div class="bio-row"><span>人脸数</span><span>{{ liveBioData.faceCount || 0 }}</span></div>
        </div>
        <div class="liveness-progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
        </div>
        <div class="liveness-step-checks">
          <span v-for="s in livenessSteps" :key="s.key" class="check-item" :class="{ done: s.done, active: s.active }">
            <span class="check-icon">{{ s.done ? '✓' : s.active ? '○' : '○' }}</span>
            <span class="check-label">{{ s.label }}</span>
          </span>
        </div>
        <button class="fa-btn fa-btn-sm" style="margin-top:12px" @click="cancelLiveness">取消</button>
      </div>

      <div v-if="livenessResult" class="fa-liveness-result">
        <p class="liveness-summary" :class="livenessAllPassed ? 'passed' : 'failed'">
          {{ livenessAllPassed ? '活体检测通过 ✓' : '活体检测未通过' }}
        </p>
        <div class="result-grid">
          <p v-for="r in livenessResult" :key="r.action" :class="r.passed ? 'passed' : 'failed'">
            {{ r.passed ? '✓' : '✗' }} {{ r.label }}
          </p>
        </div>
        <div v-if="verifyResult" class="verify-result">
          <p class="verify-label">身份识别</p>
          <p v-if="verifyResult.identified" class="verify-match">
            匹配用户: <b>{{ verifyResult.username }}</b> (置信度: {{ (verifyResult.confidence * 100).toFixed(1) }}%)
          </p>
          <p v-else class="verify-no-match">未匹配到已注册用户</p>
        </div>
        <button class="fa-btn fa-btn-sm" style="margin-top:8px" @click="resetLiveness">重新检测</button>
      </div>
    </section>

    <!-- 人脸守护 -->
    <section class="fa-card">
      <h3 class="card-title">人脸守护</h3>
      <div class="card-row">
        <input v-model="guardUser" class="fa-input" placeholder="授权用户名..." />
        <button class="fa-btn fa-btn-primary fa-btn-sm" :disabled="!guardUser" @click="startGuard">开启守护</button>
      </div>
    </section>

    <p v-if="error" class="fa-error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useFaceAuthStore } from '@/store/faceAuth'
import { useTheme } from '@/composables/useTheme'

const store = useFaceAuthStore()
const { isDark } = useTheme()

const ringClass = computed(() => ({
  'ring-blue': !store.kbLocked && !store.guardActive,
  'ring-green': store.guardActive && !store.kbLocked,
  'ring-red': store.kbLocked,
  'ring-pulse': store.guardActive,
}))
const ringIcon = computed(() => store.kbLocked ? '🔒' : store.guardActive ? '🛡️' : '👤')
const statusLabel = computed(() => {
  if (store.kbLocked) return '知识库已锁定'
  if (store.guardActive) return '守护运行中'
  if (store.enrolledUsers.length > 0) return `${store.enrolledUsers.length} 个用户`
  return '未录入用户'
})

const enrolledUsers = computed(() => store.enrolledUsers)
const guardActive = computed(() => store.guardActive)
const guardAuthorizedUser = computed(() => store.guardAuthorizedUser)
const guardCount = computed(() => store.guardUnauthorizedCount)
const guardThreshold = computed(() => store.guardThreshold)
const kbLocked = computed(() => store.kbLocked)
const error = computed(() => store.error)

const videoEl = ref<HTMLVideoElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const livenessVideoEl = ref<HTMLVideoElement | null>(null)
const cameraActive = ref(false)
let stream: MediaStream | null = null

const enrollName = ref('')
const enrolling = ref(false)
const capturedFrames = ref(0)
const capturedData = ref<string[]>([])
const enrollResult = ref('')

const livenessActive = ref(false)
const livenessScanning = ref(false)
const ringDetectedFlash = ref(false)
const ringOffset = ref(283)
const progressPercent = ref(0)
const currentActionText = ref('准备中...')
const livenessResult = ref<{ action: string; label: string; passed: boolean }[] | null>(null)
const verifyResult = ref<{ identified: boolean; username: string; confidence: number } | null>(null)
const liveBioData = ref<any>(null)
const livenessSteps = ref<{ key: string; label: string; active: boolean; done: boolean }[]>([
  { key: 'front', label: '正对摄像头', active: false, done: false },
  { key: 'blink', label: '眨眼', active: false, done: false },
  { key: 'mouth_open', label: '张嘴', active: false, done: false },
  { key: 'turn_left', label: '左转', active: false, done: false },
  { key: 'turn_right', label: '右转', active: false, done: false },
])
const livenessAllPassed = computed(() => {
  if (!livenessResult.value) return false
  return livenessResult.value.filter(r => r.passed).length >= 3
})
const guardUser = ref('')

onMounted(() => store.fetchStatus())
onUnmounted(() => stopCamera())

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } })
    if (videoEl.value) videoEl.value.srcObject = stream
    if (livenessVideoEl.value) livenessVideoEl.value.srcObject = stream
    cameraActive.value = true
  } catch (e: any) { error.value = `摄像头: ${e.message}` }
}
function stopCamera() {
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }
  cameraActive.value = false
}
function captureFrame(): string | null {
  if (!videoEl.value || !canvasEl.value) return null
  const c = canvasEl.value, v = videoEl.value
  c.width = v.videoWidth || 640; c.height = v.videoHeight || 480
  c.getContext('2d')?.drawImage(v, 0, 0)
  return c.toDataURL('image/jpeg', 0.85)
}

async function startEnroll() {
  if (!enrollName.value || enrolling.value) return
  enrolling.value = true; capturedFrames.value = 0; capturedData.value = []; enrollResult.value = ''
  const iv = setInterval(() => {
    const f = captureFrame(); if (f) { capturedData.value.push(f); capturedFrames.value++ }
    if (capturedFrames.value >= 10) { clearInterval(iv); finishEnroll() }
  }, 300)
}
async function finishEnroll() {
  const r = await store.enroll(enrollName.value, capturedData.value)
  enrollResult.value = r.message; enrolling.value = false
}

async function startAutoLiveness() {
  if (livenessActive.value) return
  livenessActive.value = true; livenessScanning.value = true
  livenessResult.value = null; verifyResult.value = null
  progressPercent.value = 0

  const sequence = [
    { action: 'front', label: '请正对摄像头', check: (d: any) => d.faceCount > 0, duration: 1500 },
    { action: 'blink', label: '请眨眼', check: (d: any) => d.blink, duration: 3000 },
    { action: 'mouth_open', label: '请张嘴', check: (d: any) => d.mouth_open, duration: 3000 },
    { action: 'turn_left', label: '请向左转头', check: (d: any) => (d.yaw || 0) < -15, duration: 3000 },
    { action: 'turn_right', label: '请向右转头', check: (d: any) => (d.yaw || 0) > 15, duration: 3000 },
  ]

  const results: { action: string; label: string; passed: boolean }[] = []
  const passedActions: string[] = []
  const frames: string[] = []

  for (let i = 0; i < sequence.length; i++) {
    const step = sequence[i]
    livenessSteps.value[i].active = true; livenessSteps.value[i].done = false
    currentActionText.value = step.label
    progressPercent.value = (i / sequence.length) * 100

    let detected = false
    const start = Date.now()
    while (Date.now() - start < step.duration) {
      await new Promise(r => setTimeout(r, 200))
      const frame = captureFrame()
      if (!frame) continue
      try {
        const data = await store.detect(frame)
        liveBioData.value = {
          ear: data.faces?.[0]?.ear, mar: data.faces?.[0]?.mar,
          yaw: data.faces?.[0]?.head_pose?.yaw,
          pitch: data.faces?.[0]?.head_pose?.pitch,
          roll: data.faces?.[0]?.head_pose?.roll,
          blink: data.faces?.[0]?.blink, mouth_open: data.faces?.[0]?.mouth_open,
          faceCount: data.faces?.length || 0,
        }
        if (!detected && step.check(liveBioData.value)) {
          detected = true; ringDetectedFlash.value = true
          setTimeout(() => ringDetectedFlash.value = false, 500)
          frames.push(frame)
        }
      } catch {}
    }
    livenessSteps.value[i].done = detected; livenessSteps.value[i].active = false
    results.push({ action: step.action, label: step.label, passed: detected })
    if (detected) passedActions.push(step.action)
  }

  progressPercent.value = 100; ringOffset.value = 0; livenessScanning.value = false
  livenessResult.value = results

  // Verify identity
  const frame = captureFrame()
  if (frame) {
    try { verifyResult.value = await store.verify(frame) } catch {}
  }
  currentActionText.value = results.filter(r => r.passed).length >= 3 ? '验证通过！' : '验证未通过'
}

function resetLiveness() {
  livenessResult.value = null; verifyResult.value = null; livenessActive.value = false
  ringOffset.value = 283; progressPercent.value = 0
  livenessSteps.value.forEach(s => { s.active = false; s.done = false })
}
function cancelLiveness() { resetLiveness() }

async function startGuard() { await store.startGuard(guardUser.value) }
async function stopGuard() { await store.stopGuard() }
async function unlock() { await store.unlockKb(true) }
async function remove(username: string) { await store.removeUser(username) }
</script>

<style scoped>
.face-auth-page {
  padding: 16px 16px 40px;
  background: var(--ios-bg-primary, #000);
  color: var(--ios-text-primary, #f5f5f7);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
}
.fa-status-section { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
.status-ring { margin-bottom: 12px; }
.ring-outer {
  width: 80px; height: 80px; border-radius: 50%;
  border: 3px solid var(--ios-blue, #0a84ff);
  display: flex; align-items: center; justify-content: center;
  transition: border-color 0.5s;
}
.ring-green .ring-outer { border-color: #30d158; }
.ring-red .ring-outer { border-color: #ff453a; }
.ring-pulse .ring-outer { animation: ringPulse 2s ease-in-out infinite; }
@keyframes ringPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.4); }
  50% { box-shadow: 0 0 0 12px rgba(48, 209, 88, 0); }
}
.ring-inner { width: 56px; height: 56px; border-radius: 50%; background: #1c1c1e; display: flex; align-items: center; justify-content: center; }
.ring-icon { font-size: 24px; }
.status-label { font-size: 14px; color: #a1a1a6; }
.status-user { font-size: 12px; color: #a1a1a6; margin-top: 2px; }

.fa-locked-banner {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  background: rgba(255, 69, 58, 0.12); border: 1px solid #ff453a; border-radius: 10px; margin-bottom: 12px; font-size: 13px;
}
.fa-guard-bar { display: flex; align-items: center; gap: 8px; padding: 8px 0; margin-bottom: 12px; font-size: 13px; }
.guard-dot { width: 8px; height: 8px; border-radius: 50%; background: #30d158; animation: dotPulse 1.5s infinite; }
@keyframes dotPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.fa-camera-card { background: #1c1c1e; border-radius: 14px; overflow: hidden; margin-bottom: 14px; }
.fa-camera-area { position: relative; min-height: 200px; background: #000; }
.fa-camera { width: 100%; display: none; transform: scaleX(-1); }
.fa-camera.active { display: block; }
.camera-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 200px; color: #666; gap: 8px; font-size: 13px; }
.fa-canvas { display: none; }
.camera-actions { display: flex; gap: 8px; padding: 12px; }

.fa-card { background: #1c1c1e; border-radius: 14px; padding: 16px; margin-bottom: 14px; }
.card-title { font-size: 15px; font-weight: 600; margin: 0 0 12px; }
.card-row { display: flex; gap: 8px; align-items: center; }

.fa-input {
  flex: 1; padding: 8px 12px; border-radius: 8px;
  border: 1px solid #3a3a3c; background: #2c2c2e; color: #f5f5f7; font-size: 14px;
}

.fa-btn {
  padding: 8px 16px; border-radius: 18px;
  border: 1px solid #3a3a3c; background: #2c2c2e; color: #f5f5f7; font-size: 13px;
  font-weight: 500; cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.fa-btn-primary { background: #0a84ff; border-color: #0a84ff; color: #fff; }
.fa-btn-primary:hover { background: #409cff; }
.fa-btn-danger { border-color: #ff453a; color: #ff453a; }
.fa-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.fa-btn-sm { padding: 6px 12px; font-size: 12px; }

.fa-user-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #3a3a3c; }
.fa-user-row:last-child { border-bottom: none; }
.fa-user-name { flex: 1; font-size: 14px; }
.fa-empty { font-size: 13px; color: #a1a1a6; padding: 4px 0; }
.fa-result { font-size: 13px; color: #a1a1a6; margin-top: 8px; }
.fa-hint { font-size: 13px; color: #a1a1a6; margin-bottom: 10px; }
.fa-error { color: #ff453a; font-size: 13px; }

.liveness-ring { position: relative; width: 200px; height: 200px; margin: 0 auto 12px; border-radius: 50%; overflow: hidden; border: 3px solid #3a3a3c; }
.liveness-ring.scanning { border-color: #0a84ff; animation: ringPulse 1.5s infinite; }
.liveness-ring.detected { border-color: #30d158; }
.liveness-video-ring { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); border-radius: 50%; }
.ring-overlay { position: absolute; inset: 0; border-radius: 50%; border: 3px solid transparent; }
.liveness-action-text { text-align: center; font-size: 16px; font-weight: 600; margin: 8px 0; }
.live-bio-data { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; font-size: 11px; color: #a1a1a6; padding: 8px; background: #2c2c2e; border-radius: 8px; margin-bottom: 10px; }
.bio-row { display: flex; justify-content: space-between; }
.bio-detect { color: #30d158; font-weight: 600; }
.liveness-progress-bar { height: 4px; background: #3a3a3c; border-radius: 2px; margin-bottom: 10px; overflow: hidden; }
.progress-fill { height: 100%; background: #0a84ff; transition: width 0.3s; border-radius: 2px; }
.liveness-step-checks { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.check-item { font-size: 12px; color: #666; display: flex; align-items: center; gap: 4px; }
.check-item.done { color: #30d158; }
.check-item.active { color: #0a84ff; }
.fa-liveness-result { margin-top: 8px; }
.liveness-summary { font-size: 15px; font-weight: 600; }
.liveness-summary.passed { color: #30d158; }
.liveness-summary.failed { color: #ff453a; }
.result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 8px; }
.result-grid p { font-size: 13px; margin: 0; }
.result-grid .passed { color: #30d158; }
.result-grid .failed { color: #666; }
.verify-result { margin-top: 10px; padding: 10px; background: #2c2c2e; border-radius: 8px; }
.verify-label { font-size: 11px; color: #a1a1a6; margin: 0 0 4px; }
.verify-match { font-size: 14px; color: #30d158; margin: 0; }
.verify-no-match { font-size: 14px; color: #ff453a; margin: 0; }
</style>
