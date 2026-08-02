# 通晓开发板（TX-SMART-R）开发指南

> 本指南根据官方《通晓开发板原理图》与《OpenHarmony初识开发板》整理，
> 用于 SmartKitchen 开发板端（OpenHarmony Lite）的开发与调试。

---

## 1. 开发板概述

- **型号**：TX-SMART-R（软通教育 通晓系列）
- **主控**：国产芯片 RK2206（瑞芯微），预装 **OpenHarmony Lite** 轻量级系统
- **尺寸**：100 × 135 mm，一体化紧凑设计
- **联网**：Wi-Fi 无线连接，支持 **MQTT 协议**，可对接物联网平台
- **适用**：OpenHarmony 学习研究、高校课程教学、创新创业竞赛

### 板载资源

| 类型 | 外设 | 说明 |
|------|------|------|
| 传感器 | 温湿度传感器 | 环境温湿度采集 |
| 传感器 | 加速度传感器 | 姿态/运动检测 |
| 传感器 | 人体红外传感器 | 人体接近检测 |
| 传感器 | 光强传感器 BH1750FVI | I2C 接口，环境光强度 |
| 可控外设 | 显示屏 | 状态/结果展示 |
| 可控外设 | 蜂鸣器 MLT-7525 | S8050 三极管驱动 |
| 可控外设 | 电机 | 运动控制 |
| 接口 | USB-C | 供电 + 烧录 |
| 接口 | E53 SPI 接口 | 扩展传感器/外设 |
| 接口 | NFC NT3H1201W0FHK | 近场通信标签 |

### 原理图页结构（官方 7 页）

```
PAGE01 POWER          电源电路（3V3 LDO，MAX 1A，LED 指示）
PAGE02 MODULE         NFC 模块（NT3H1201W0FHK）+ 绿 LED
PAGE03 INTERFACE 1    E53 SPI 扩展接口（SPI1_CLK/MOSI/MISO）
PAGE04 INTERFACE 2    USB-C 接口（CC/DP/DN，ESD 保护）
PAGE05 INPUT SENSOR 1 光强传感器 BH1750FVI（I2C，S8050 驱动）
PAGE06 INPUT SENSOR 2 传感器电路（分压/滤波）
PAGE07 OUTPUT SENSOR  蜂鸣器 MLT-7525（S8050 驱动，1N5819 保护）
```

---

## 2. 系统烧录

### 2.1 安装驱动

双击安装（OpenHarmony 源码 device 目录下）：

```
device/rockchip/tools/windows/DriverAssitant/DriverInstall.exe
```

### 2.2 烧录固件

1. USB 线连接开发板**烧写端口**
2. 打开烧写工具：`device/rockchip/tools/windows/RKDevTool.exe`
3. **按住 mask 按键 → 按一下 reset 按键** → 松开，进入烧写模式
4. 烧写工具提示"发现一个 MASKROM 设备"即成功
5. 选择固件并烧录

### 2.3 查看运行日志

1. 安装 CH340 驱动（USB 转串口）
2. 打开 **MobaXterm**：`Session → Serial`
3. 选择对应 COM 口，**波特率 115200**
4. 打开 session 即可查看系统日志

---

## 3. Hello World（OpenHarmony Lite C 开发）

### 3.1 创建工程目录

在 OpenHarmony 源码 `vendor` 目录创建 `hello` 文件夹，内含：

```
vendor/isoftstone/rk2206/samples/hello/
├── hello.c
└── BUILD.gn
```

### 3.2 hello.c

```c
#include "ohos_init.h"

int hello_example()
{
    printf("Hello World!\n");
    return 0;
}

APP_FEATURE_INIT(hello_example);
```

### 3.3 BUILD.gn

```gn
static_library("hello") {
    sources = [
        "hello.c",
    ]
    include_dirs = [
        ".",
    ]
}
```

### 3.4 修改上层 BUILD.gn

在 `vendor/isoftstone/rk2206/samples/BUILD.gn` 中引入 `hello` 子目标，然后编译烧录。

---

## 4. 与 SmartKitchen 的结合（扩展方向）

开发板作为**厨房端感知节点**，与 SmartKitchen 后端（FastAPI）联动：

| 开发板能力 | 厨房场景 |
|-----------|---------|
| 人体红外传感器 | 检测人进入厨房 → 触发拍照识别 |
| 光强传感器 BH1750 | 环境光照自适应（弱光自动补光提示） |
| 温湿度传感器 | 食材存储环境监测（湿度预警） |
| Wi-Fi + MQTT | 将识别结果/传感器数据上报后端 |
| 蜂鸣器 | 识别完成/营养超标提醒 |
| 显示屏 | 本地显示识别结果与营养数据 |

> 通信建议：开发板通过 MQTT 连接局域网 Broker（如 EMQX），
> 后端订阅主题 `/kitchen/{board_id}/sensor` 与 `/kitchen/{board_id}/recognize`。
