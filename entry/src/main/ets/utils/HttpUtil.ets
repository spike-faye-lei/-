import http from '@ohos.net.http'
import fs from '@ohos.file.fs'
import { AppStorage, RecognizeResponse, NutritionInfo, FoodLogResponse,
  RecipeListResponse, GuidelineResponse, MemberListResponse,
  FaceStatusResponse, FaceVerifyResponse, FaceEnrollResponse,
  MealResponse, HealthScoreResponse, LeaderboardResponse,
  ChatResponse, BoardStatusResponse } from './DataModels'

export class HttpUtil {
  private baseUrl: string = AppStorage.backendUrl

  setBaseUrl(url: string) {
    this.baseUrl = url
    AppStorage.backendUrl = url
  }

  getBaseUrl(): string {
    return this.baseUrl
  }

  async get(url: string): Promise<string> {
    let httpReq = http.createHttp()
    return new Promise<string>((resolve, reject) => {
      httpReq.request(this.baseUrl + url, { method: http.RequestMethod.GET }).then(data => {
        let resp = data.result as string
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async recognize(imagePath: string): Promise<RecognizeResponse> {
    let httpReq = http.createHttp()

    let buf: ArrayBuffer
    try {
      let file = fs.openSync(imagePath, fs.OpenMode.READ_ONLY)
      let stat = fs.statSync(file.fd)
      buf = new ArrayBuffer(stat.size)
      fs.readSync(file.fd, buf)
      await fs.close(file)
    } catch (e) {
      httpReq.destroy()
      return Promise.reject(e)
    }

    let boundary = '----SmartKitchen' + Date.now().toString(36)
    let header = '--' + boundary + '\r\n' +
      'Content-Disposition: form-data; name="file"; filename="food.jpg"\r\n' +
      'Content-Type: image/jpeg\r\n\r\n'
    let footer = '\r\n--' + boundary + '--\r\n'
    let headerBuf = new ArrayBuffer(header.length)
    let headerView = new Uint8Array(headerBuf)
    for (let i = 0; i < header.length; i++) {
      headerView[i] = header.charCodeAt(i)
    }
    let footerBuf = new ArrayBuffer(footer.length)
    let footerView = new Uint8Array(footerBuf)
    for (let i = 0; i < footer.length; i++) {
      footerView[i] = footer.charCodeAt(i)
    }

    let totalLen = headerBuf.byteLength + buf.byteLength + footerBuf.byteLength
    let fullBody = new ArrayBuffer(totalLen)
    let fullView = new Uint8Array(fullBody)
    fullView.set(new Uint8Array(headerBuf), 0)
    fullView.set(new Uint8Array(buf), headerBuf.byteLength)
    fullView.set(new Uint8Array(footerBuf), headerBuf.byteLength + buf.byteLength)

    let extraData: http.HttpRequestOptions = {
      method: http.RequestMethod.POST,
      header: {
        'Content-Type': 'multipart/form-data; boundary=' + boundary
      },
      extraData: fullBody,
      connectTimeout: 10000,
      readTimeout: 30000
    }

    return new Promise<RecognizeResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/recognize', extraData).then(data => {
        let resp = JSON.parse(data.result as string) as RecognizeResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async getNutrition(name: string, weight: number): Promise<NutritionInfo> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/nutrition?name=' + encodeURIComponent(name) + '&weight=' + weight

    return new Promise<NutritionInfo>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as NutritionInfo
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async logFood(foodName: string, weightG: number, calories: number,
    proteinG: number = 0, fatG: number = 0, carbsG: number = 0,
    confidence: number = 0, member: string = 'default'): Promise<boolean> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/log' +
      '?food_name=' + encodeURIComponent(foodName) +
      '&weight_g=' + weightG +
      '&calories=' + calories +
      '&protein_g=' + proteinG +
      '&fat_g=' + fatG +
      '&carbs_g=' + carbsG +
      '&confidence=' + confidence +
      '&member=' + encodeURIComponent(member)

    return new Promise<boolean>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.POST }).then(() => {
        httpReq.destroy()
        resolve(true)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async getHistory(days: number = 7): Promise<FoodLogResponse> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/history?days=' + days

    return new Promise<FoodLogResponse>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as FoodLogResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async getSummary(): Promise<Record<string, Object>> {
    let httpReq = http.createHttp()
    return new Promise<Record<string, Object>>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/summary?today=true', { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as Record<string, Object>
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }
  // ====== 菜谱 ======

  async getRecipes(mealType?: string): Promise<RecipeListResponse> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/recipes'
    if (mealType) {
      url += '?meal_type=' + encodeURIComponent(mealType)
    }
    return new Promise<RecipeListResponse>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as RecipeListResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async recommendRecipes(goal: string, mealType?: string): Promise<RecipeListResponse> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/recipes/recommend?goal=' + encodeURIComponent(goal)
    if (mealType) {
      url += '&meal_type=' + encodeURIComponent(mealType)
    }
    return new Promise<RecipeListResponse>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as RecipeListResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 膳食指南 ======

  async getGuidelines(goal: string = 'maintain'): Promise<GuidelineResponse> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/guidelines?goal=' + encodeURIComponent(goal)
    return new Promise<GuidelineResponse>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as GuidelineResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 家庭成员 ======

  async getMembers(): Promise<MemberListResponse> {
    let httpReq = http.createHttp()
    return new Promise<MemberListResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/members', { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as MemberListResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async addMember(name: string, healthGoal: string): Promise<boolean> {
    let httpReq = http.createHttp()
    let url = this.baseUrl + '/api/members?name=' + encodeURIComponent(name) +
      '&health_goal=' + encodeURIComponent(healthGoal)
    return new Promise<boolean>((resolve, reject) => {
      httpReq.request(url, { method: http.RequestMethod.POST }).then(() => {
        httpReq.destroy()
        resolve(true)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async deleteMember(memberId: number): Promise<boolean> {
    let httpReq = http.createHttp()
    return new Promise<boolean>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/members/' + memberId, {
        method: http.RequestMethod.DELETE
      }).then(() => {
        httpReq.destroy()
        resolve(true)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 人脸识别 ======

  async getFaceStatus(): Promise<FaceStatusResponse> {
    let httpReq = http.createHttp()
    return new Promise<FaceStatusResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/face-auth/status', { method: http.RequestMethod.GET }).then(data => {
        let resp = JSON.parse(data.result as string) as FaceStatusResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async verifyFace(imagePath: string): Promise<FaceVerifyResponse> {
    let httpReq = http.createHttp()

    let buf: ArrayBuffer
    try {
      let file = fs.openSync(imagePath, fs.OpenMode.READ_ONLY)
      let stat = fs.statSync(file.fd)
      buf = new ArrayBuffer(stat.size)
      fs.readSync(file.fd, buf)
      await fs.close(file)
    } catch (e) {
      httpReq.destroy()
      return Promise.reject(e)
    }

    let bytes = new Uint8Array(buf)
    let boundary = '----FaceKitchen' + Date.now().toString(36)
    let header = '--' + boundary + '\r\n' +
      'Content-Disposition: form-data; name="frame"; filename="face.jpg"\r\n' +
      'Content-Type: image/jpeg\r\n\r\n'
    let footer = '\r\n--' + boundary + '--\r\n'

    let totalLen = header.length + buf.byteLength + footer.length
    let fullBody = new ArrayBuffer(totalLen)
    let fullView = new Uint8Array(fullBody)
    for (let i = 0; i < header.length; i++) fullView[i] = header.charCodeAt(i)
    fullView.set(bytes, header.length)
    for (let i = 0; i < footer.length; i++) fullView[header.length + bytes.length + i] = footer.charCodeAt(i)

    return new Promise<FaceVerifyResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/face-auth/verify', {
        method: http.RequestMethod.POST,
        header: { 'Content-Type': 'multipart/form-data; boundary=' + boundary },
        extraData: fullBody,
        connectTimeout: 10000,
        readTimeout: 30000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as FaceVerifyResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async enrollFace(username: string, imagePath: string): Promise<FaceEnrollResponse> {
    let httpReq = http.createHttp()

    // 简单的 base64 编码
    let buf: ArrayBuffer
    try {
      let file = fs.openSync(imagePath, fs.OpenMode.READ_ONLY)
      let stat = fs.statSync(file.fd)
      buf = new ArrayBuffer(stat.size)
      fs.readSync(file.fd, buf)
      await fs.close(file)
    } catch (e) {
      httpReq.destroy()
      return Promise.reject(e)
    }

    let bytes = new Uint8Array(buf)
    let binary = ''
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    // Use our own base64 encoding
    let chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    let encoded = ''
    for (let i = 0; i < binary.length; i += 3) {
      let a = binary.charCodeAt(i) || 0
      let b = binary.charCodeAt(i + 1) || 0
      let c = binary.charCodeAt(i + 2) || 0
      let b1 = a >> 2
      let b2 = ((a & 3) << 4) | (b >> 4)
      let b3 = ((b & 15) << 2) | (c >> 6)
      let b4 = c & 63
      encoded += chars[b1] + chars[b2]
      if (i + 1 < binary.length) encoded += chars[b3]
      else encoded += '='
      if (i + 2 < binary.length) encoded += chars[b4]
      else encoded += '='
    }

    let body = JSON.stringify({
      username: username,
      frames: [encoded]
    })

    return new Promise<FaceEnrollResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/face-auth/enroll', {
        method: http.RequestMethod.POST,
        header: { 'Content-Type': 'application/json' },
        extraData: body,
        connectTimeout: 10000,
        readTimeout: 30000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as FaceEnrollResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 整餐分析 ======

  async recognizeMeal(imagePath: string): Promise<MealResponse> {
    let httpReq = http.createHttp()
    let buf: ArrayBuffer
    try {
      let file = fs.openSync(imagePath, fs.OpenMode.READ_ONLY)
      let stat = fs.statSync(file.fd)
      buf = new ArrayBuffer(stat.size)
      fs.readSync(file.fd, buf)
      await fs.close(file)
    } catch (e) {
      httpReq.destroy()
      return Promise.reject(e)
    }

    let bytes = new Uint8Array(buf)
    let boundary = '----Meal' + Date.now().toString(36)
    let header = '--' + boundary + '\r\n' +
      'Content-Disposition: form-data; name="file"; filename="meal.jpg"\r\n' +
      'Content-Type: image/jpeg\r\n\r\n'
    let footer = '\r\n--' + boundary + '--\r\n'
    let totalLen = header.length + buf.byteLength + footer.length
    let fullBody = new ArrayBuffer(totalLen)
    let fullView = new Uint8Array(fullBody)
    for (let i = 0; i < header.length; i++) fullView[i] = header.charCodeAt(i)
    fullView.set(bytes, header.length)
    for (let i = 0; i < footer.length; i++) fullView[header.length + bytes.length + i] = footer.charCodeAt(i)

    return new Promise<MealResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/recognize/meal', {
        method: http.RequestMethod.POST,
        header: { 'Content-Type': 'multipart/form-data; boundary=' + boundary },
        extraData: fullBody,
        connectTimeout: 10000,
        readTimeout: 30000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as MealResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 健康评分 ======

  async getHealthScore(member: string): Promise<HealthScoreResponse> {
    let httpReq = http.createHttp()
    return new Promise<HealthScoreResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/health-score?member=' + member, {
        method: http.RequestMethod.GET,
        connectTimeout: 10000,
        readTimeout: 15000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as HealthScoreResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  async getLeaderboard(): Promise<LeaderboardResponse> {
    let httpReq = http.createHttp()
    return new Promise<LeaderboardResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/leaderboard', {
        method: http.RequestMethod.GET,
        connectTimeout: 10000,
        readTimeout: 15000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as LeaderboardResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== AI 营养师对话 ======

  async chat(message: string, member: string): Promise<ChatResponse> {
    let httpReq = http.createHttp()
    let body = JSON.stringify({ message: message, member: member })
    return new Promise<ChatResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/chat', {
        method: http.RequestMethod.POST,
        header: { 'Content-Type': 'application/json' },
        extraData: body,
        connectTimeout: 10000,
        readTimeout: 30000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as ChatResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }

  // ====== 开发板状态 ======

  async getBoardStatus(): Promise<BoardStatusResponse> {
    let httpReq = http.createHttp()
    return new Promise<BoardStatusResponse>((resolve, reject) => {
      httpReq.request(this.baseUrl + '/api/board/status', {
        method: http.RequestMethod.GET,
        connectTimeout: 10000,
        readTimeout: 15000,
      }).then(data => {
        let resp = JSON.parse(data.result as string) as BoardStatusResponse
        httpReq.destroy()
        resolve(resp)
      }).catch((err: Error) => {
        httpReq.destroy()
        reject(err)
      })
    })
  }
}

export const httpUtil = new HttpUtil()
