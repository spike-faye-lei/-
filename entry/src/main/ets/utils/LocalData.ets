// ============================================
// 离线预载数据模块
// 数据来源：中国食物成分表 / 中国居民膳食指南(2022) / USDA FoodData Central
// 后端未启动时各页面 fallback 到这里的本地数据，保证 App 可离线浏览
// ============================================
import { FoodItem, NutritionDetail, RecipeItem, RecipeIngredient, RecipeNutrition,
  GuidelineResponse, GuidelineTarget, PagodaItem, MacroRatio } from './DataModels';

// —— 内置食物营养库（每 100g，serving_g 为典型食用量）——
interface LocalFood {
  key: string;
  name: string;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  fiber: number;
  category: string;
  serving_g: number;
}

const FOODS: LocalFood[] = [
  // ===== 水果 =====
  { key: 'apple', name: '苹果', calories: 52, protein: 0.3, fat: 0.2, carbs: 14.0, fiber: 2.4, category: '水果', serving_g: 200 },
  { key: 'banana', name: '香蕉', calories: 89, protein: 1.1, fat: 0.3, carbs: 22.8, fiber: 2.6, category: '水果', serving_g: 120 },
  { key: 'orange', name: '橙子', calories: 47, protein: 0.9, fat: 0.1, carbs: 11.8, fiber: 2.4, category: '水果', serving_g: 200 },
  { key: 'grape', name: '葡萄', calories: 69, protein: 0.7, fat: 0.2, carbs: 18.1, fiber: 0.9, category: '水果', serving_g: 150 },
  { key: 'pear', name: '梨', calories: 50, protein: 0.4, fat: 0.1, carbs: 13.1, fiber: 3.1, category: '水果', serving_g: 200 },
  { key: 'peach', name: '桃', calories: 42, protein: 0.9, fat: 0.1, carbs: 10.1, fiber: 1.3, category: '水果', serving_g: 150 },
  { key: 'strawberry', name: '草莓', calories: 32, protein: 0.7, fat: 0.3, carbs: 7.7, fiber: 2.0, category: '水果', serving_g: 150 },
  { key: 'watermelon', name: '西瓜', calories: 30, protein: 0.6, fat: 0.2, carbs: 7.6, fiber: 0.4, category: '水果', serving_g: 300 },
  { key: 'kiwi', name: '猕猴桃', calories: 61, protein: 1.1, fat: 0.5, carbs: 14.7, fiber: 2.6, category: '水果', serving_g: 100 },
  { key: 'mango', name: '芒果', calories: 60, protein: 0.8, fat: 0.4, carbs: 15.0, fiber: 1.6, category: '水果', serving_g: 150 },
  { key: 'grapefruit', name: '柚子', calories: 42, protein: 0.8, fat: 0.2, carbs: 9.6, fiber: 1.2, category: '水果', serving_g: 200 },
  { key: 'dragonfruit', name: '火龙果', calories: 55, protein: 1.1, fat: 0.2, carbs: 13.3, fiber: 2.9, category: '水果', serving_g: 200 },
  { key: 'pineapple', name: '菠萝', calories: 50, protein: 0.5, fat: 0.1, carbs: 13.1, fiber: 1.4, category: '水果', serving_g: 150 },
  { key: 'blueberry', name: '蓝莓', calories: 57, protein: 0.7, fat: 0.3, carbs: 14.5, fiber: 2.4, category: '水果', serving_g: 100 },
  { key: 'cantaloupe', name: '哈密瓜', calories: 34, protein: 0.8, fat: 0.2, carbs: 8.2, fiber: 0.8, category: '水果', serving_g: 200 },
  // ===== 蔬菜 =====
  { key: 'tomato', name: '西红柿', calories: 18, protein: 0.9, fat: 0.2, carbs: 3.9, fiber: 1.2, category: '蔬菜', serving_g: 150 },
  { key: 'cucumber', name: '黄瓜', calories: 15, protein: 0.7, fat: 0.1, carbs: 3.6, fiber: 0.5, category: '蔬菜', serving_g: 150 },
  { key: 'carrot', name: '胡萝卜', calories: 41, protein: 0.9, fat: 0.2, carbs: 9.6, fiber: 2.8, category: '蔬菜', serving_g: 100 },
  { key: 'potato', name: '土豆', calories: 77, protein: 2.0, fat: 0.1, carbs: 17.5, fiber: 2.2, category: '蔬菜', serving_g: 100 },
  { key: 'broccoli', name: '西兰花', calories: 34, protein: 2.8, fat: 0.4, carbs: 6.6, fiber: 2.6, category: '蔬菜', serving_g: 150 },
  { key: 'spinach', name: '菠菜', calories: 28, protein: 2.6, fat: 0.3, carbs: 4.5, fiber: 2.2, category: '蔬菜', serving_g: 150 },
  { key: 'lettuce', name: '生菜', calories: 15, protein: 1.4, fat: 0.2, carbs: 2.9, fiber: 1.3, category: '蔬菜', serving_g: 100 },
  { key: 'cabbage', name: '大白菜', calories: 18, protein: 1.5, fat: 0.1, carbs: 3.4, fiber: 1.1, category: '蔬菜', serving_g: 200 },
  { key: 'sweet_potato', name: '红薯', calories: 86, protein: 1.6, fat: 0.1, carbs: 20.1, fiber: 3.0, category: '蔬菜', serving_g: 150 },
  { key: 'corn', name: '玉米', calories: 112, protein: 4.0, fat: 1.2, carbs: 22.8, fiber: 2.9, category: '蔬菜', serving_g: 100 },
  { key: 'bell_pepper', name: '青椒', calories: 22, protein: 1.0, fat: 0.2, carbs: 5.4, fiber: 1.9, category: '蔬菜', serving_g: 100 },
  { key: 'eggplant', name: '茄子', calories: 23, protein: 1.1, fat: 0.2, carbs: 4.9, fiber: 1.9, category: '蔬菜', serving_g: 150 },
  { key: 'pumpkin', name: '南瓜', calories: 22, protein: 0.7, fat: 0.1, carbs: 5.3, fiber: 0.8, category: '蔬菜', serving_g: 200 },
  { key: 'onion', name: '洋葱', calories: 40, protein: 1.1, fat: 0.2, carbs: 9.0, fiber: 1.7, category: '蔬菜', serving_g: 100 },
  { key: 'celery', name: '芹菜', calories: 16, protein: 0.7, fat: 0.2, carbs: 3.3, fiber: 1.4, category: '蔬菜', serving_g: 150 },
  { key: 'shiitake', name: '香菇', calories: 26, protein: 2.2, fat: 0.3, carbs: 5.2, fiber: 3.3, category: '蔬菜', serving_g: 100 },
  { key: 'enoki', name: '金针菇', calories: 26, protein: 2.4, fat: 0.4, carbs: 6.0, fiber: 2.7, category: '蔬菜', serving_g: 100 },
  // ===== 蛋白质 =====
  { key: 'chicken_breast', name: '鸡胸肉', calories: 165, protein: 31.0, fat: 3.6, carbs: 0.0, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'beef', name: '瘦牛肉', calories: 125, protein: 20.2, fat: 4.2, carbs: 0.0, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'pork_lean', name: '瘦猪肉', calories: 143, protein: 20.3, fat: 6.2, carbs: 1.5, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'lamb', name: '羊肉', calories: 118, protein: 20.5, fat: 3.9, carbs: 0.0, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'salmon', name: '三文鱼', calories: 208, protein: 20.4, fat: 13.4, carbs: 0.0, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'shrimp', name: '虾', calories: 93, protein: 18.6, fat: 0.8, carbs: 2.8, fiber: 0.0, category: '肉类', serving_g: 100 },
  { key: 'egg', name: '鸡蛋', calories: 155, protein: 13.0, fat: 11.0, carbs: 1.1, fiber: 0.0, category: '蛋类', serving_g: 50 },
  { key: 'milk', name: '牛奶', calories: 66, protein: 3.2, fat: 3.6, carbs: 4.8, fiber: 0.0, category: '乳制品', serving_g: 250 },
  { key: 'yogurt', name: '酸奶', calories: 72, protein: 2.5, fat: 2.7, carbs: 9.3, fiber: 0.0, category: '乳制品', serving_g: 150 },
  { key: 'soy_milk', name: '豆浆', calories: 31, protein: 3.0, fat: 1.6, carbs: 1.2, fiber: 0.4, category: '豆制品', serving_g: 250 },
  { key: 'tofu', name: '豆腐', calories: 76, protein: 8.0, fat: 4.8, carbs: 1.9, fiber: 0.3, category: '豆制品', serving_g: 100 },
  // ===== 主食 =====
  { key: 'rice', name: '米饭', calories: 116, protein: 2.6, fat: 0.3, carbs: 25.9, fiber: 0.3, category: '主食', serving_g: 150 },
  { key: 'noodles', name: '面条', calories: 138, protein: 4.5, fat: 2.1, carbs: 25.0, fiber: 1.0, category: '主食', serving_g: 150 },
  { key: 'steamed_bun', name: '馒头', calories: 223, protein: 7.0, fat: 1.1, carbs: 47.0, fiber: 1.3, category: '主食', serving_g: 100 },
  { key: 'whole_wheat_bread', name: '全麦面包', calories: 246, protein: 10.7, fat: 3.4, carbs: 41.9, fiber: 7.0, category: '主食', serving_g: 60 },
  { key: 'bread', name: '面包', calories: 266, protein: 8.8, fat: 3.3, carbs: 49.0, fiber: 2.7, category: '主食', serving_g: 80 },
  { key: 'oats', name: '燕麦', calories: 367, protein: 15.0, fat: 6.7, carbs: 61.0, fiber: 10.6, category: '主食', serving_g: 40 },
  { key: 'millet_porridge', name: '小米粥', calories: 46, protein: 1.4, fat: 0.7, carbs: 8.4, fiber: 0.3, category: '主食', serving_g: 300 },
  { key: 'brown_rice', name: '糙米', calories: 111, protein: 2.6, fat: 0.9, carbs: 23.0, fiber: 1.8, category: '主食', serving_g: 150 },
  // ===== 坚果豆类 =====
  { key: 'peanut', name: '花生', calories: 567, protein: 25.8, fat: 49.2, carbs: 16.1, fiber: 8.5, category: '坚果', serving_g: 30 },
  { key: 'walnut', name: '核桃', calories: 646, protein: 14.9, fat: 58.8, carbs: 19.1, fiber: 9.5, category: '坚果', serving_g: 30 },
  { key: 'almond', name: '杏仁', calories: 579, protein: 21.2, fat: 50.0, carbs: 21.6, fiber: 12.5, category: '坚果', serving_g: 30 },
  { key: 'black_bean', name: '黑豆', calories: 401, protein: 36.0, fat: 15.9, carbs: 33.6, fiber: 10.2, category: '豆类', serving_g: 50 },
  { key: 'red_bean', name: '红豆', calories: 324, protein: 20.2, fat: 0.6, carbs: 63.4, fiber: 7.7, category: '豆类', serving_g: 50 }
];

// —— 内置菜谱（食材 key 对应上方营养库，营养值运行时计算）——
interface LocalRecipe {
  key: string;
  name: string;
  name_en: string;
  meal_type: string;
  cook_time: number;
  difficulty: string;
  ingredients: RecipeIngredient[];
  steps?: string[];
  bvideo?: string;
  bvideoAuthor?: string;
}

const RECIPES: LocalRecipe[] = [
  { key: 'tomato_egg_rice', name: '西红柿鸡蛋盖饭', name_en: 'Tomato Egg Rice Bowl', meal_type: 'lunch', cook_time: 15, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1SW4y1f7Tc', bvideoAuthor: '超子美食',
    ingredients: [{ food: 'tomato', grams: 150 }, { food: 'egg', grams: 100 }, { food: 'rice', grams: 200 }], steps: ['鸡蛋打散炒熟盛出', '番茄切块下锅炒出汤汁', '倒入鸡蛋翻炒均匀，盖在米饭上'] },
  { key: 'chicken_broccoli', name: '西兰花炒鸡胸肉', name_en: 'Chicken & Broccoli Stir-fry', meal_type: 'lunch', cook_time: 20, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1BLFPzZEXe', bvideoAuthor: '火焰魔法师gogo',
    ingredients: [{ food: 'chicken_breast', grams: 150 }, { food: 'broccoli', grams: 200 }, { food: 'rice', grams: 150 }], steps: ['西兰花焯水 1 分钟捞出', '鸡胸肉切片，热锅少油炒至变色', '倒入西兰花翻炒，加少许盐出锅配米饭'] },
  { key: 'tofu_veg_rice', name: '家常豆腐饭', name_en: 'Home-style Tofu Rice', meal_type: 'lunch', cook_time: 20, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1wP411G7gX', bvideoAuthor: '饱食料理',
    ingredients: [{ food: 'tofu', grams: 200 }, { food: 'carrot', grams: 80 }, { food: 'broccoli', grams: 100 }, { food: 'rice', grams: 150 }], steps: ['豆腐切块煎至两面金黄', '胡萝卜、西兰花焯水', '一起下锅加少量生抽焖 3 分钟，配米饭'] },
  { key: 'potato_carrot_chicken', name: '土豆胡萝卜炖鸡', name_en: 'Potato Carrot Chicken Stew', meal_type: 'lunch', cook_time: 30, difficulty: 'medium', bvideo: 'https://www.bilibili.com/video/BV1fj41147xY', bvideoAuthor: '亚东家常菜',
    ingredients: [{ food: 'potato', grams: 200 }, { food: 'carrot', grams: 100 }, { food: 'chicken_breast', grams: 150 }, { food: 'rice', grams: 150 }], steps: ['鸡胸肉切块焯水', '土豆胡萝卜切块下锅翻炒', '加水炖 20 分钟至软烂，调味收汁配米饭'] },
  { key: 'beef_noodles', name: '牛肉面', name_en: 'Beef Noodle Soup', meal_type: 'lunch', cook_time: 30, difficulty: 'medium', bvideo: 'https://www.bilibili.com/video/BV13M4y157Gj', bvideoAuthor: '超子美食',
    ingredients: [{ food: 'beef', grams: 120 }, { food: 'noodles', grams: 150 }, { food: 'cabbage', grams: 100 }], steps: ['牛肉切块焯水去沫', '加葱姜炖 40 分钟', '面条煮熟，浇牛肉汤和肉块，加白菜'] },
  { key: 'salmon_rice', name: '香煎三文鱼饭', name_en: 'Pan-seared Salmon Rice', meal_type: 'lunch', cook_time: 25, difficulty: 'medium', bvideo: 'https://www.bilibili.com/video/BV1oC411L7Wi', bvideoAuthor: '克里斯的食谱',
    ingredients: [{ food: 'salmon', grams: 150 }, { food: 'broccoli', grams: 150 }, { food: 'rice', grams: 150 }], steps: ['三文鱼用盐和黑胡椒腌 10 分钟', '平底锅少油煎至两面金黄（每面 3 分钟）', '西兰花焯水，配米饭装盘'] },
  { key: 'egg_noodles', name: '鸡蛋面', name_en: 'Egg Noodle Soup', meal_type: 'breakfast', cook_time: 10, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1DngZ6gEYS', bvideoAuthor: '老叶厨房',
    ingredients: [{ food: 'noodles', grams: 150 }, { food: 'egg', grams: 50 }, { food: 'tomato', grams: 100 }], steps: ['面条煮熟过凉水', '番茄切块炒出汁加水煮开', '打入鸡蛋煮成蛋花，调味浇面'] },
  { key: 'milk_bread_egg', name: '牛奶面包鸡蛋早餐', name_en: 'Milk Bread & Egg Breakfast', meal_type: 'breakfast', cook_time: 5, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1nY411p7x6', bvideoAuthor: 'Helly的美食每刻',
    ingredients: [{ food: 'milk', grams: 250 }, { food: 'bread', grams: 80 }, { food: 'egg', grams: 50 }], steps: ['鸡蛋煮 8 分钟或煎熟', '面包烤热', '搭配牛奶和鸡蛋装盘'] },
  { key: 'fruit_bowl', name: '水果拼盘', name_en: 'Fruit Bowl', meal_type: 'breakfast', cook_time: 5, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV16F4m1j7RN', bvideoAuthor: '花式果盘家林',
    ingredients: [{ food: 'apple', grams: 150 }, { food: 'banana', grams: 100 }, { food: 'orange', grams: 150 }], steps: ['苹果、橙子去皮切块', '香蕉切片', '全部装碗，可加少许酸奶'] },
  { key: 'oat_milk_breakfast', name: '燕麦牛奶粥', name_en: 'Oat Milk Porridge', meal_type: 'breakfast', cook_time: 10, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1FD4y1q7ch', bvideoAuthor: '桔子北琪',
    ingredients: [{ food: 'oats', grams: 40 }, { food: 'milk', grams: 250 }, { food: 'banana', grams: 100 }], steps: ['燕麦加牛奶小火煮 5 分钟', '香蕉切片', '倒入碗中，撒上香蕉即可'] },
  { key: 'banana_milk', name: '香蕉牛奶', name_en: 'Banana Milk', meal_type: 'breakfast', cook_time: 3, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1qW4y1p7yN', bvideoAuthor: '迹录Fount',
    ingredients: [{ food: 'milk', grams: 200 }, { food: 'banana', grams: 100 }, { food: 'bread', grams: 60 }], steps: ['香蕉切段', '牛奶加热', '香蕉和牛奶放入杯中，压碎搅拌'] },
  { key: 'steamed_egg_porridge', name: '小米粥配蒸蛋', name_en: 'Millet Porridge & Steamed Egg', meal_type: 'breakfast', cook_time: 20, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1nt411Q7Uf', bvideoAuthor: '九食九',
    ingredients: [{ food: 'millet_porridge', grams: 300 }, { food: 'egg', grams: 50 }, { food: 'cucumber', grams: 100 }], steps: ['小米粥提前煮好', '鸡蛋打散加温水 1:1，蒸 8 分钟', '黄瓜切条，搭配粥和蒸蛋'] },
  { key: 'cucumber_salad_chicken', name: '凉拌黄瓜鸡丝', name_en: 'Cucumber Chicken Salad', meal_type: 'dinner', cook_time: 15, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1fh4y117EZ', bvideoAuthor: '老东北美食',
    ingredients: [{ food: 'cucumber', grams: 200 }, { food: 'chicken_breast', grams: 100 }, { food: 'bread', grams: 60 }], steps: ['鸡胸肉煮熟撕成丝', '黄瓜切丝', '加蒜末、醋、生抽拌匀，配面包'] },
  { key: 'tomato_tofu_soup', name: '番茄豆腐汤', name_en: 'Tomato Tofu Soup', meal_type: 'dinner', cook_time: 15, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1xe4y1L7Nt', bvideoAuthor: '小石榴爸爸家常菜',
    ingredients: [{ food: 'tomato', grams: 200 }, { food: 'tofu', grams: 150 }, { food: 'egg', grams: 50 }], steps: ['番茄切块炒出汁', '加水煮开，豆腐切块放入', '小火煮 5 分钟，淋蛋液，调味'] },
  { key: 'veggie_noodles', name: '素菜拌面', name_en: 'Vegetable Noodles', meal_type: 'dinner', cook_time: 15, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1F2grzbEo3', bvideoAuthor: '猪小姐的素食记',
    ingredients: [{ food: 'noodles', grams: 150 }, { food: 'cucumber', grams: 100 }, { food: 'carrot', grams: 80 }, { food: 'egg', grams: 50 }], steps: ['面条煮熟过凉水', '黄瓜胡萝卜切丝，鸡蛋煎薄切丝', '加芝麻酱或生抽拌匀'] },
  { key: 'rice_tofu_veg', name: '清淡素食餐', name_en: 'Light Vegan Bowl', meal_type: 'dinner', cook_time: 20, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1vBEq62EtV', bvideoAuthor: '我是姚早早',
    ingredients: [{ food: 'rice', grams: 120 }, { food: 'tofu', grams: 150 }, { food: 'broccoli', grams: 150 }], steps: ['豆腐切块煎香', '西兰花焯水', '配米饭，淋少许酱油'] },
  { key: 'shrimp_broccoli', name: '虾仁炒西兰花', name_en: 'Shrimp & Broccoli Stir-fry', meal_type: 'dinner', cook_time: 15, difficulty: 'medium', bvideo: 'https://www.bilibili.com/video/BV1nv411B78i', bvideoAuthor: '潮州山哥',
    ingredients: [{ food: 'shrimp', grams: 150 }, { food: 'broccoli', grams: 200 }, { food: 'brown_rice', grams: 120 }], steps: ['虾仁用料酒腌 5 分钟', '西兰花焯水', '热锅炒虾仁至变色，加西兰花翻炒调味'] },
  { key: 'mushroom_chicken_porridge', name: '香菇鸡肉粥', name_en: 'Mushroom Chicken Porridge', meal_type: 'dinner', cook_time: 30, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1D64y1T7ab', bvideoAuthor: '一条风味地图',
    ingredients: [{ food: 'shiitake', grams: 80 }, { food: 'chicken_breast', grams: 100 }, { food: 'millet_porridge', grams: 250 }, { food: 'carrot', grams: 50 }], steps: ['鸡胸肉切丁，香菇切片', '粥煮开后加入鸡肉香菇', '煮 10 分钟，加胡萝卜丁和盐调味'] },
  { key: 'pork_cabbage', name: '白菜炒肉片', name_en: 'Pork & Cabbage Stir-fry', meal_type: 'dinner', cook_time: 20, difficulty: 'easy', bvideo: 'https://www.bilibili.com/video/BV1MA41197mC', bvideoAuthor: '老东北美食',
    ingredients: [{ food: 'pork_lean', grams: 120 }, { food: 'cabbage', grams: 200 }, { food: 'rice', grams: 150 }], steps: ['瘦肉切片煸炒出油', '白菜切段下锅翻炒', '加生抽和少量水焖 3 分钟，配米饭'] },
  { key: 'eggplant_tofu', name: '茄子烧豆腐', name_en: 'Eggplant & Tofu Stew', meal_type: 'dinner', cook_time: 25, difficulty: 'medium', bvideo: 'https://www.bilibili.com/video/BV11B4y1t7pP', bvideoAuthor: '家宴美食厨房',
    ingredients: [{ food: 'eggplant', grams: 200 }, { food: 'tofu', grams: 150 }, { food: 'rice', grams: 120 }] }
];

// —— 内置膳食指南（数据来源：中国居民膳食指南 2022 / WHO-FAO NRV）——
const GUIDELINE_TARGETS: Record<string, GuidelineTarget> = {
  'maintain': { calories: 2000, protein_g: 60, fat_g: 55, carbs_g: 300, fiber_g: 25 },
  'lose': { calories: 1500, protein_g: 70, fat_g: 40, carbs_g: 200, fiber_g: 30 },
  'gain': { calories: 2500, protein_g: 90, fat_g: 70, carbs_g: 375, fiber_g: 30 }
};

const MEAL_RATIOS: Record<string, number> = { 'breakfast': 0.30, 'lunch': 0.40, 'dinner': 0.30 };

const PAGODA: Record<string, PagodaItem> = {
  '主食': { min: 250, max: 400, unit: 'g' },
  '蔬菜': { min: 300, max: 500, unit: 'g' },
  '水果': { min: 200, max: 350, unit: 'g' },
  '肉类': { min: 40, max: 75, unit: 'g' },
  '蛋类': { min: 40, max: 50, unit: 'g' },
  '乳制品': { min: 300, max: 300, unit: 'g' },
  '豆制品': { min: 25, max: 25, unit: 'g' }
};

// —— 平衡膳食八准则（膳食指南 2022 核心建议）——
export const DIETARY_PRINCIPLES: string[] = [
  '食物多样，合理搭配：每天摄入 12 种以上食物，每周 25 种以上',
  '吃动平衡，健康体重：保持能量摄入与消耗平衡',
  '多吃蔬果、奶类、全谷、大豆：餐餐有蔬菜，天天吃水果',
  '适量吃鱼、禽、蛋、瘦肉：优先选择鱼和禽类',
  '少盐少油，控糖限酒：每日食盐不超过 5g，烹调油 25~30g',
  '规律进餐，足量饮水：每日饮水 1500~1700ml',
  '会烹会选，会看标签：学习烹饪，学会阅读食品标签',
  '公筷分餐，杜绝浪费：文明餐饮，注意食品卫生'
];

export class LocalData {
  // —— 食物列表（供营养库页面）——
  static foodList(): FoodItem[] {
    let list: FoodItem[] = []
    FOODS.forEach((f: LocalFood): void => {
      list.push({ key: f.key, name_cn: f.name, category: f.category, calories_per_100g: f.calories })
    })
    return list
  }

  // —— 按 key 查食物中文名（菜谱详情展示用）——
  static foodName(key: string): string {
    for (let i = 0; i < FOODS.length; i++) {
      if (FOODS[i].key === key) {
        return FOODS[i].name
      }
    }
    return key
  }

  // —— 按 key 查营养成分（weight 克）——
  static nutrition(key: string, weight: number): NutritionDetail | null {
    for (let i = 0; i < FOODS.length; i++) {
      let f = FOODS[i]
      if (f.key === key) {
        let w = weight > 0 ? weight : f.serving_g
        let ratio = w / 100
        return {
          name: f.key, name_cn: f.name, category: f.category,
          calories: Math.round(f.calories * ratio),
          protein_g: Math.round(f.protein * ratio * 10) / 10,
          fat_g: Math.round(f.fat * ratio * 10) / 10,
          carbs_g: Math.round(f.carbs * ratio * 10) / 10,
          fiber_g: Math.round(f.fiber * ratio * 10) / 10,
          weight_g: w
        }
      }
    }
    return null
  }

  // —— 菜谱列表（meal 为空返回全部；营养值按食材实时计算）——
  static recipes(meal: string): RecipeItem[] {
    let list: RecipeItem[] = []
    RECIPES.forEach((r: LocalRecipe): void => {
      if (meal && r.meal_type !== meal) return
      list.push({
        key: r.key, name: r.name, name_en: r.name_en,
        meal_type: r.meal_type, cook_time: r.cook_time, difficulty: r.difficulty,
        ingredients: r.ingredients, steps: r.steps,
        bvideo: r.bvideo, bvideoAuthor: r.bvideoAuthor, nutrition: LocalData.calcNutrition(r.ingredients)
      })
    })
    return list
  }

  // —— 智能推荐（按目标热量适配，返回评分排序）——
  static recommendRecipes(goal: string, meal: string): RecipeItem[] {
    let target = GUIDELINE_TARGETS[goal] ? GUIDELINE_TARGETS[goal] : GUIDELINE_TARGETS['maintain']
    let list: RecipeItem[] = LocalData.recipes(meal)
    list.forEach((r: RecipeItem): void => {
      // 匹配度：与目标一餐热量（约 1/3 日目标）的接近程度
      let ideal = target.calories / 3
      let diff = Math.abs(r.nutrition.calories - ideal) / ideal
      r.score = Math.round(Math.max(40, 100 - diff * 200))
    })
    list.sort((a: RecipeItem, b: RecipeItem): number => {
      return (b.score ?? 0) - (a.score ?? 0)
    })
    return list
  }

  // —— 膳食指南（按目标）——
  static guidelines(goal: string): GuidelineResponse {
    let target = GUIDELINE_TARGETS[goal] ? GUIDELINE_TARGETS[goal] : GUIDELINE_TARGETS['maintain']
    let meals: Record<string, GuidelineTarget> = {}
    let keys: string[] = ['breakfast', 'lunch', 'dinner']
    keys.forEach((m: string): void => {
      let ratio = MEAL_RATIOS[m]
      meals[m] = {
        calories: Math.round(target.calories * ratio),
        protein_g: Math.round(target.protein_g * ratio * 10) / 10,
        fat_g: Math.round(target.fat_g * ratio * 10) / 10,
        carbs_g: Math.round(target.carbs_g * ratio * 10) / 10,
        fiber_g: Math.round(target.fiber_g * ratio * 10) / 10
      }
    })
    let macro: MacroRatio = {
      protein_pct: Math.round(target.protein_g * 4 / target.calories * 1000) / 10,
      fat_pct: Math.round(target.fat_g * 9 / target.calories * 1000) / 10,
      carbs_pct: Math.round(target.carbs_g * 4 / target.calories * 1000) / 10
    }
    return {
      goal: goal, daily: target, meals: meals,
      pagoda: PAGODA, macro_ratio: macro,
      source: '中国居民膳食指南2022 / WHO-FAO NRV（离线内置）'
    }
  }

  // —— 离线营养知识问答（后端 AI 不可用时兜底，关键词匹配）——
  static ask(question: string): string {
    let q = question
    let answers: string[][] = [
      ['蛋白质', '蛋白质是身体修复和生长的重要营养素。推荐每日摄入：成年人约 60~90g，来源包括鸡胸肉(31g/100g)、鸡蛋(13g/个)、豆腐(8g/100g)、牛奶(3.2g/100ml)。'],
      ['减脂', '减脂核心是热量缺口：建议每日约 1500kcal，蛋白质提高到 70g 以上，主食选粗粮（燕麦、糙米），少油少盐，配合每周 150 分钟运动。'],
      ['增肌', '增肌需要热量盈余：每日约 2500kcal，蛋白质 90g 以上，三餐规律，训练后补充蛋白质（鸡胸肉、三文鱼、鸡蛋）。'],
      ['热量', '每 100g 常见食物热量：米饭 116kcal、鸡胸肉 165kcal、鸡蛋 155kcal、苹果 52kcal、西兰花 34kcal。想控制热量就多选蔬菜水果。'],
      ['早餐', '推荐早餐搭配：全谷物主食 + 优质蛋白 + 水果/蔬菜，例如燕麦牛奶粥配香蕉，或鸡蛋面加西红柿。'],
      ['喝水', '中国居民膳食指南(2022)建议每日饮水 1500~1700ml，少量多次，白开水最佳。'],
      ['膳食指南', '中国居民膳食指南(2022)八大准则：食物多样合理搭配、吃动平衡、多吃蔬果奶类全谷大豆、适量吃鱼禽蛋瘦肉、少盐少油控糖限酒、规律进餐足量饮水、会烹会选会看标签、公筷分餐杜绝浪费。'],
      ['蔬菜', '每日建议摄入蔬菜 300~500g、水果 200~350g，深色蔬菜（西兰花、菠菜）应占一半以上。'],
      ['盐', '中国居民膳食指南建议每日食盐不超过 5g，烹调油 25~30g，控糖限酒。']
    ]
    for (let i = 0; i < answers.length; i++) {
      if (q.indexOf(answers[i][0]) >= 0) {
        return answers[i][1]
      }
    }
    return '我是离线知识库，暂时无法连接后端 AI。你可以问我：蛋白质、减脂、增肌、热量、早餐、喝水、膳食指南、蔬菜 等问题。'
  }

  // —— 计算菜谱营养（按食材克数）——
  private static calcNutrition(ingredients: RecipeIngredient[]): RecipeNutrition {
    let cal = 0, protein = 0, fat = 0, carbs = 0, fiber = 0
    ingredients.forEach((ing: RecipeIngredient): void => {
      for (let i = 0; i < FOODS.length; i++) {
        let f = FOODS[i]
        if (f.key === ing.food) {
          let ratio = ing.grams / 100
          cal += f.calories * ratio
          protein += f.protein * ratio
          fat += f.fat * ratio
          carbs += f.carbs * ratio
          fiber += f.fiber * ratio
          break
        }
      }
    })
    return {
      calories: Math.round(cal),
      protein: Math.round(protein * 10) / 10,
      fat: Math.round(fat * 10) / 10,
      carbs: Math.round(carbs * 10) / 10,
      fiber: Math.round(fiber * 10) / 10
    }
  }
}
