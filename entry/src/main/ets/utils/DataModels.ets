export interface RecognizeResult {
  name: string
  name_cn: string
  confidence: number
  class_index: number
}

export interface RecognizeTopK {
  name: string
  confidence: number
}

export interface RecognizeResponse {
  success: boolean
  prediction: RecognizeResult
  top3: RecognizeTopK[]
  filename: string
}

export interface NutritionInfo {
  name: string
  name_en: string
  weight_g: number
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
  category: string
}

export interface FoodLogItem {
  id: number
  food_name: string
  food_name_cn: string
  weight_g: number
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  confidence: number
  created_at: string
}

export interface FoodLogResponse {
  records: FoodLogItem[]
  count: number
}

export interface SummaryItem {
  day: string
  total_cal: number
  total_protein: number
  total_fat: number
  total_carbs: number
  count: number
}

// ====== 菜谱 ======

export interface RecipeIngredient {
  food: string
  grams: number
}

export interface RecipeNutrition {
  calories: number
  protein: number
  fat: number
  carbs: number
  fiber: number
}

export interface RecipeItem {
  key: string
  name: string
  name_en: string
  meal_type: string
  cook_time: number
  difficulty: string
  ingredients: RecipeIngredient[]
  nutrition: RecipeNutrition
  score?: number
}

export interface RecipeListResponse {
  recipes: RecipeItem[]
  target_cal?: number
  goal?: string
}

// ====== 膳食指南 ======

export interface MacroRatio {
  protein_pct: number
  fat_pct: number
  carbs_pct: number
}

export interface GuidelineTarget {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
}

export interface PagodaItem {
  min: number
  max: number
  unit: string
}

export interface GuidelineResponse {
  goal: string
  daily: GuidelineTarget
  meals: Record<string, GuidelineTarget>
  pagoda: Record<string, PagodaItem>
  macro_ratio: MacroRatio
  source: string
}

// ====== 家庭成员 ======

export interface MemberItem {
  id: number
  name: string
  health_goal: string
  created_at: string
}

export interface MemberListResponse {
  members: MemberItem[]
}

// ====== 人脸识别 ======

export interface FaceStatusResponse {
  enrolled_users: string[]
}

export interface FaceVerifyResponse {
  success: boolean
  identified: boolean
  username?: string
  confidence?: number
  message?: string
}

export interface FaceEnrollResponse {
  success: boolean
  message?: string
}

// ====== 国际化 ======

export interface I18nDict {
  appName: string; tagline: string; camera: string; manualInput: string
  nutritionDB: string; dietHistory: string; home: string; nutrition: string
  history: string; lightTheme: string; darkTheme: string; langZh: string; langEn: string
  takePhoto: string; recognize: string; weight: string; weightG: string; portion: string
  calories: string; protein: string; fat: string; carbs: string; fiber: string
  kcal: string; per100g: string; searchFood: string; searchFoodHint: string
  noResults: string; loading: string; analyze: string; logFood: string; logSuccess: string
  editWeight: string; back: string; reload: string; noRecords: string; noRecordsHint: string
  recognized: string; recognizing: string; sendToServer: string; recognitionFailed: string
  foodName: string; category: string; created: string; cameraNotAvailable: string
  manualInputTitle: string; manualInputDesc: string; cameraTitle: string; cameraDesc: string
  dailyCalories: string; nutritionDetail: string; weightSample: string
  healthGoal: string; goalMaintain: string; goalLose: string; goalGain: string
  recommendTitle: string; recommendSub: string; recommendTotal: string
  recommendStaple: string; recommendProtein: string; recommendVeg: string
  memberTitle: string; addMember: string; memberName: string; memberGoal: string
  deleteMember: string; mealBreakfast: string; mealLunch: string; mealDinner: string
  memberPH: string
}

// ====== 营养数据库 ======

export interface FoodItem {
  key: string
  name_cn: string
  category: string
  calories_per_100g: number
}

export interface NutritionDetail {
  name: string
  name_cn: string
  category: string
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
  weight_g: number
}

export interface FoodListResponse {
  foods: FoodItem[]
}

// ====== 历史记录 ======

export interface HistoryRecord {
  id: number
  food_name: string
  food_name_cn: string
  weight_g: number
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  member: string
  created_at: string
}

export interface HistoryResponse {
  records: HistoryRecord[]
}

// ====== 整餐分析 ======

export interface MealFood {
  name: string
  confidence: number
  cells: number
}

export interface MealSummary {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export interface MealResponse {
  success: boolean
  message: string
  foods: MealFood[]
  summary: MealSummary | null
}

// ====== 健康评分 ======

export interface ScoreDimension {
  score: number
  value: number
  target: number
  full: number
}

export interface HealthScoreResponse {
  success: boolean
  member: string
  score: number | null
  level: string
  dimensions: Record<string, ScoreDimension>
  message: string
}

export interface RankItem {
  member: string
  score: number
  days: number
  rank: number
}

export interface LeaderboardResponse {
  success: boolean
  days: number
  ranking: RankItem[]
}

// ====== AI 对话 ======

export interface ChatResponse {
  success: boolean
  reply: string
  configured: boolean
}

export class AppStorage {
  static lastRecognizeResult: RecognizeResult | null = null
  static lastNutrition: NutritionInfo | null = null
  // 修改为你的电脑局域网IP（ipconfig查看），手机和电脑连同一WiFi
  static backendUrl: string = 'http://<YOUR_PC_IP>:8686'
  static currentMember: string = 'default'
}
