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
  steps?: string[]
  bvideo?: string
  bvideoAuthor?: string
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
  memberPH: string; recipes: string; assistant: string; me: string
  settings: string; boardStatus: string; darkMode: string; fontSize: string; language: string
  singleFood: string; mealAnalysis: string
  healthScore: string; todayCalories: string; emptyRecord: string; foodDetail: string; recipeSquare: string; guidelines: string
  eatWell: string; eatWellDesc: string; askNutritionist: string; chatDesc: string; tryAsking: string
  faceRecognition: string; boardDesc: string; historyDesc: string; guidelinesDesc: string; membersDesc: string; faceDesc: string; settingsDesc: string; aboutDesc: string
  browseByMeal: string; pagodaDesc: string; startChat: string; q1: string; q2: string; q3: string
  aiNutritionist: string; loseWeight: string; dinnerIdea: string; thinking: string; chatPlaceholder: string; send: string
  noKeyHint: string; welcomeMsg: string
  recipeTitle: string; smartRecommend: string; allRecipes: string; loadingRecipes: string; noRecipes: string
  matchScore: string; diffEasy: string; diffMedium: string; diffHard: string
  guidelinesTitle: string; dailyIntake: string; macroRatio: string; mealDistribution: string; pagodaTitle: string
  dataSource: string; loadingGuidelines: string
  cancel: string; confirmAdd: string; delete: string; defaultNotDeletable: string; selectCurrent: string
  memberHint: string; loadingMembers: string; noMembers: string; addSuccess: string; addFailed: string
  deleteSuccess: string; deleteFailed: string; currentMember: string
  enterMemberName: string; registeredMembers: string
  faceTitle: string; registerThis: string; registered: string; recognitionResult: string; faceHint: string
  boardTitle: string; online: string; offline: string; light: string; temperature: string; humidity: string
  foodWeight: string; refresh: string; boardAuto: string; weighFlow: string; weighFlowDesc: string
  deviceModel: string; chip: string; os: string; comm: string; lastReport: string
  appearance: string; followSystem: string; followSystemDesc: string; darkModeDesc: string; fontSizeDesc: string
  fontPreview: string; languageDesc: string; about: string; settingsAutoSave: string
  fontSmall: string; fontStandard: string; fontLarge: string; fontXLarge: string; complete: string; all: string
  bodyData: string; bodyTitle: string; height: string; bodyWeight: string; age: string; gender: string; male: string; female: string
  bmi: string; bodyFatRate: string; level: string; suggestion: string
  underweight: string; normal: string; overweight: string; obese: string
  sugUnder: string; sugNormal: string; sugOver: string; sugObese: string; bodyDataDesc: string; cm: string; kg: string
  currentMemberLabel: string; dietPlan: string; calorieTarget: string; mealsPlan: string; foodRec: string
  exerciseRec: string; applyGoal: string; goalApplied: string
  calUnder: string; calNormal: string; calOver: string; calObese: string
  mealsUnder: string; mealsNormal: string; mealsOver: string; mealsObese: string
  foodsUnder: string; foodsNormal: string; foodsOver: string; foodsObese: string
  exUnder: string; exNormal: string; exOver: string; exObese: string
  ageGroup: string; ageUnit: string
  eatWhat: string; eatHowMuch: string; noProfile: string
  ingredients: string; steps: string
  weeklyTrend: string
  watchTutorial: string
  logToHistory: string; logFail: string; leaderboard: string; days: string; rankLabel: string
  styleMode: string; styleDesc: string; glassStyle: string; minimalStyle: string
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

// ====== 开发板 ======

export interface BoardSensorData {
  board: string
  lux: number
  temp: number
  hum: number
  weight_g: number
  _time: string
}

export interface BoardStatusResponse {
  success: boolean
  online: boolean
  data: BoardSensorData | null
  message: string
}

export class AppStorage {
  static lastRecognizeResult: RecognizeResult | null = null
  static lastNutrition: NutritionInfo | null = null
  // 修改为你的电脑局域网IP（ipconfig查看），手机和电脑连同一WiFi
  static backendUrl: string = 'http://<YOUR_PC_IP>:8686'
  static currentMember: string = 'default'
}
