# SmartKitchen — 智能AI家庭健康厨房助手

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5-red)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![HarmonyOS](https://img.shields.io/badge/HarmonyOS-NEXT-orange)](https://developer.huawei.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

基于 CLIP 多模态预训练模型与知识蒸馏的智能食材识别系统，面向 HarmonyOS 移动端部署。

**🎯 核心指标：CLIP + Fruits 360 验证准确率 92.69%（15类食材）**  
**📱 端侧部署：MobileNetV3-Small 蒸馏模型 90.83%（仅 6MB）**

---

## ✨ 特性

- 🥕 **高精度食材识别** — CLIP ViT-B/32 迁移学习，15 类中国常见食材
- 📊 **6 组模型对比** — MobileNetV2 → EfficientNet → CLIP → 多模态 → 知识蒸馏
- 🗜️ **100 倍模型压缩** — 知识蒸馏 605MB → 6MB，准确率仅损失 1.86%
- 🔗 **多模态融合** — 图像特征 + 营养文本特征联合分类
- 👤 **人脸识别** — MediaPipe 面部特征点检测，家庭成员管理
- 📱 **HarmonyOS 前端** — ArkTS + ArkUI，7 页面完整 App
- 🍽️ **营养分析 + 菜谱推荐** — 基于 USDA / 中国食物成分表

---

## 📁 项目结构

```
SmartKitchen/
├── backend/
│   ├── api/              # 7个API模块（识别/营养/菜谱/记录/成员/指南）
│   ├── models/           # 模型文件（CLIP/DINOv2/蒸馏Student）
│   ├── modules/          # 人脸识别模块 (MediaPipe)
│   ├── app.py            # FastAPI 主服务 (端口8686)
│   └── database.py       # SQLite 数据库
├── data_train_final/     # 训练集 4339张 (15类)
├── data_val_final/       # 验证集 1080张 (15类)
├── train_clip.py         # CLIP 迁移学习训练脚本
├── train_distill.py      # 知识蒸馏训练脚本（Teacher→Student）
├── train_multimodal.py   # 多模态融合训练脚本
├── download_fruits_retry.py  # Fruits 360 自动续传下载
├── requirements.txt
└── A11451411/            # HarmonyOS 前端项目（DevEco Studio）
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- PyTorch 2.0+
- CUDA（可选，CPU 也能跑）
- DevEco Studio（仅编译前端需要）

### 1. 安装依赖

```bash
cd SmartKitchen
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python -m backend.app
# 服务运行在 http://localhost:8686
# 访问 http://localhost:8686 确认启动成功
```

### 3. 训练模型（可选，预训练权重已提供）

```bash
# CLIP 迁移学习（推荐）
python train_clip.py

# 知识蒸馏（轻量化）
python train_distill.py

# 多模态融合
python train_multimodal.py
```

### 4. 编译前端（需要 DevEco Studio）

用 DevEco Studio 打开 `A11451411/` 目录，Sync 后 Build。

---

## 📊 实验对比

| 序号 | 模型 | 验证准确率 | 模型大小 |
|:---:|------|:---------:|:-------:|
| 1 | MobileNetV2 (基线) | 68.24% | 12MB |
| 2 | EfficientNet-B0 + MixUp | 70.97% | 19MB |
| 3 | CLIP 冻结 + 旧数据 | 83.36% | 605MB |
| 4 | 多模态融合 (图文) | 88.15% | 605MB+ |
| 5 | **CLIP + Fruits 360** | **92.69%** | 605MB+ |
| 6 | **知识蒸馏 Student** | **90.83%** | **6MB** |

逐类准确率详见 [桌面/1-逐类评估.txt](桌面/1-逐类评估.txt)。

---

## 🗂️ 数据集

本项目的训练数据由两部分组成：

| 来源 | 说明 | 数量 |
|------|------|:---:|
| Bing 搜索引擎爬取 | 15 类中国常见食材 | 2835张 |
| Kaggle Fruits 360 | 7 类水果蔬菜高质量白底图 | ~3500张 |
| **合计** | | **5419张** |

15 个类别：apple, banana, orange, tomato, cucumber, carrot, potato,
chicken_breast, egg, milk, tofu, broccoli, rice, noodles, bread

---

## 🙏 致谢 / Acknowledgments

本项目受益于以下优秀开源项目：

| 项目 | 用途 | 许可证 |
|------|------|:---:|
| [OpenAI CLIP](https://github.com/openai/CLIP) | 视觉-语言预训练模型 | MIT |
| [PyTorch](https://pytorch.org) | 深度学习框架 | BSD |
| [FastAPI](https://github.com/tiangolo/fastapi) | Web 框架 | MIT |
| [HuggingFace Transformers](https://github.com/huggingface/transformers) | 预训练模型 | Apache 2.0 |
| [Kaggle Fruits 360](https://www.kaggle.com/moltean/fruits) | 果蔬数据集 | CC0 |
| [MediaPipe](https://github.com/google/mediapipe) | 人脸特征点检测 | Apache 2.0 |
| [CountBot](https://github.com/countbot-ai/CountBot) | 人脸识别模块参考 | MIT |

感谢所有开源贡献者 ❤️

---

## 📄 许可证

本项目代码采用 [MIT License](LICENSE)。

项目中使用到的第三方模型和数据集遵循各自的原始许可证。

---

## 👨‍💻 作者

- 上海建桥学院 计算机科学与技术 2026届毕设
- 联系方式：GitHub Issues
