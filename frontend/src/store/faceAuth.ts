/** Face Auth Pinia Store */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { faceAuthApi } from '@/api/faceAuth'

export interface FaceStatus {
  enrolled_users: string[]
  guard_status: {
    active: boolean
    authorized_user: string
    unauthorized_count: number
    threshold: number
    kb_locked: boolean
  }
}

export const useFaceAuthStore = defineStore('faceAuth', () => {
  const enrolledUsers = ref<string[]>([])
  const guardActive = ref(false)
  const guardAuthorizedUser = ref('')
  const guardUnauthorizedCount = ref(0)
  const guardThreshold = ref(10)
  const kbLocked = ref(false)
  const isLoading = ref(false)
  const error = ref('')

  const isKbLocked = computed(() => kbLocked.value)

  async function fetchStatus() {
    try {
      isLoading.value = true
      const status = await faceAuthApi.getStatus()
      enrolledUsers.value = status.enrolled_users || []
      guardActive.value = status.guard_status?.active || false
      guardAuthorizedUser.value = status.guard_status?.authorized_user || ''
      guardUnauthorizedCount.value = status.guard_status?.unauthorized_count || 0
      guardThreshold.value = status.guard_status?.threshold || 10
      kbLocked.value = status.guard_status?.kb_locked || false
      error.value = ''
    } catch (e: any) {
      error.value = e?.message || 'Failed to fetch face auth status'
    } finally {
      isLoading.value = false
    }
  }

  async function enroll(username: string, frames: string[]): Promise<{ ok: boolean; message: string }> {
    try {
      isLoading.value = true
      const result = await faceAuthApi.enroll(username, frames)
      if (result.success) {
        enrolledUsers.value.push(username)
      }
      return { ok: result.success, message: result.message }
    } catch (e: any) {
      return { ok: false, message: e?.message || 'Enrollment failed' }
    } finally {
      isLoading.value = false
    }
  }

  async function detect(frame: string): Promise<any> {
    return faceAuthApi.detect(frame)
  }

  async function livenessCheck(frames: string[], actions: string[]): Promise<any> {
    return faceAuthApi.livenessCheck(frames, actions)
  }

  async function startGuard(username: string) {
    try {
      await faceAuthApi.startGuard(username)
      guardActive.value = true
      guardAuthorizedUser.value = username
      guardUnauthorizedCount.value = 0
    } catch (e: any) {
      error.value = e?.message || 'Failed to start guard'
    }
  }

  async function stopGuard() {
    try {
      await faceAuthApi.stopGuard()
      guardActive.value = false
    } catch (e: any) {
      error.value = e?.message || 'Failed to stop guard'
    }
  }

  async function resetGuard() {
    try {
      await faceAuthApi.resetGuard()
      guardUnauthorizedCount.value = 0
    } catch (e: any) {
      error.value = e?.message || 'Failed to reset guard'
    }
  }

  async function unlockKb(restore: boolean = true) {
    try {
      await faceAuthApi.unlockKb(restore)
      kbLocked.value = false
    } catch (e: any) {
      error.value = e?.message || 'Failed to unlock KB'
    }
  }

  async function removeUser(username: string) {
    try {
      await faceAuthApi.removeEnrollment(username)
      enrolledUsers.value = enrolledUsers.value.filter(u => u !== username)
    } catch (e: any) {
      error.value = e?.message || 'Failed to remove user'
    }
  }

  async function verify(frame: string): Promise<{ identified: boolean; username: string; confidence: number }> {
    return faceAuthApi.verify(frame)
  }

  return {
    enrolledUsers,
    guardActive,
    guardAuthorizedUser,
    guardUnauthorizedCount,
    guardThreshold,
    kbLocked,
    isLoading,
    error,
    isKbLocked,
    fetchStatus,
    enroll,
    detect,
    livenessCheck,
    verify,
    startGuard,
    stopGuard,
    resetGuard,
    unlockKb,
    removeUser,
  }
})
