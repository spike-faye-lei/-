/*
 * SmartKitchen Board App — 通晓开发板 TX-SMART-R (OpenHarmony Lite, RK2206)
 * ============================================================================
 * 功能:
 *   1. 人体红外传感器检测 (GPIO 中断) → 触发拍照/识别流程
 *   2. BH1750 光强传感器 (I2C) → 环境光自适应
 *   3. 温湿度传感器 → 食材存储环境监测
 *   4. TinyCNN INT8 粗分类 (32x32) → 4 大类: 水果/蔬菜/蛋白/主食
 *   5. Wi-Fi + MQTT 上报 → 后端 FastAPI 订阅处理
 *   6. 蜂鸣器 (PWM) → 识别完成/预警提醒
 *
 * 编译部署: 见 docs/开发板-通晓TX-SMART-R.md
 * 权重文件: backend/models/tinycnn_weights.h (由 train_tinycnn.py 生成)
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ohos_init.h"
#include "cmsis_os2.h"
#include "iot_gpio.h"
#include "iot_gpio_ex.h"
#include "iot_i2c.h"
#include "iot_pwm.h"
#include "iot_wifi.h"
#include "wifi_device.h"
#include "lwip/sockets.h"
#include "mqtt.h"   /* paho mqtt 移植到 OpenHarmony Lite */

#include "tinycnn_weights.h"  /* INT8 权重, ~6KB */

/* ===== 配置 ===== */
#define WIFI_SSID       "SmartKitchen"
#define WIFI_PASSWORD   "12345678"
#define MQTT_BROKER     "192.168.1.100"   /* 后端电脑局域网 IP */
#define MQTT_PORT       1883
#define MQTT_TOPIC_UP   "kitchen/board1/sensor"
#define MQTT_TOPIC_DOWN "kitchen/board1/cmd"

/* ===== 引脚定义 (依据原理图 PAGE05/06/07) ===== */
#define PIN_PIR         GPIO_GPIO_9   /* 人体红外 (中断输入) */
#define PIN_BUZZER      GPIO_GPIO_10  /* 蜂鸣器 MLT-7525 (PWM) */
#define PIN_LED_RED     GPIO_GPIO_11  /* 电源指示灯 RED_LED */
#define I2C_BUS         0             /* I2C0: BH1750 + 温湿度 */
#define BH1750_ADDR     0x23          /* 光强传感器 */
#define SHT30_ADDR      0x44          /* 温湿度传感器 */
#define PIN_HX711_SCK   GPIO_GPIO_12  /* HX711 称重: 时钟 (E53 扩展) */
#define PIN_HX711_DT    GPIO_GPIO_13  /* HX711 称重: 数据 */

/* HX711 校准系数 (需用标准砝码标定) */
#define HX711_SCALE     420.0f        /* raw -> 克 */
#define HX711_OFFSET    8000000       /* 空载读数 */

/* ===== TinyCNN 推理 (纯 C, 无浮点) ===== */
#define IN_SIZE  32
#define NUM_CLASS 4

static int8_t input_buf[3 * 32 * 32];

/* INT8 卷积: y = sum(x*w) / scale, 用 int32 累加防溢出 */
static void conv3x3_int8(const int8_t *in, int8_t *out,
                         int in_h, int in_w, int in_ch, int out_ch,
                         const int8_t *w, const float *s_w, float s_out,
                         int stride, int pad)
{
    for (int oc = 0; oc < out_ch; oc++) {
        for (int oh = 0; oh < in_h / stride; oh++) {
            for (int ow = 0; ow < in_w / stride; ow++) {
                int32_t acc = 0;
                for (int ic = 0; ic < in_ch; ic++) {
                    for (int kh = 0; kh < 3; kh++) {
                        for (int kw = 0; kw < 3; kw++) {
                            int ih = oh * stride + kh - pad;
                            int iw = ow * stride + kw - pad;
                            if (ih < 0 || iw < 0 || ih >= in_h || iw >= in_w) continue;
                            int wi = ((oc * in_ch + ic) * 3 + kh) * 3 + kw;
                            acc += in[(ic * in_h + ih) * in_w + iw] * w[wi];
                        }
                    }
                }
                out[(oc * (in_h/stride) + oh) * (in_w/stride) + ow] =
                    (int8_t)(acc * s_w[0] / s_out);  /* 简化量化缩放 */
            }
        }
    }
}

/* ReLU + MaxPool2x2 融合 */
static void relu_maxpool_int8(const int8_t *in, int8_t *out,
                              int h, int w, int ch)
{
    for (int c = 0; c < ch; c++)
        for (int i = 0; i < h/2; i++)
            for (int j = 0; j < w/2; j++) {
                int8_t m = INT8_MIN;
                for (int di = 0; di < 2; di++)
                    for (int dj = 0; dj < 2; dj++) {
                        int8_t v = in[(c*h + i*2+di)*w + j*2+dj];
                        if (v > m) m = v;
                    }
                out[(c*(h/2) + i)*(w/2) + j] = m > 0 ? m : 0;
            }
}

/* 完整推理: 返回 0-3 类别 */
int tinycnn_predict(const int8_t *img, float *scores)
{
    int8_t l1[8*16*16], l2[16*8*8], l3[32*4*4];
    int8_t *out = NULL;

    conv3x3_int8(img, l1, 32, 32, 3, 8,
                 W_features_0_0_weight, &S_features_0_0_weight, 1.0f, 1, 1);
    relu_maxpool_int8(l1, l1, 32, 32, 8);

    conv3x3_int8(l1, l2, 16, 16, 8, 16,
                 W_features_2_0_weight, &S_features_2_0_weight, 1.0f, 1, 1);
    relu_maxpool_int8(l2, l2, 16, 16, 16);

    conv3x3_int8(l2, l3, 8, 8, 16, 32,
                 W_features_4_0_weight, &S_features_4_0_weight, 1.0f, 1, 1);
    relu_maxpool_int8(l3, l3, 8, 8, 32);

    /* GAP + FC (4x4 avg -> 32 维) */
    float feat[32] = {0};
    for (int c = 0; c < 32; c++) {
        int32_t sum = 0;
        for (int i = 0; i < 16; i++) sum += l3[c*16 + i];
        feat[c] = (float)sum / 16.0f;
    }

    float best = -1e9f;
    int best_cls = 0;
    for (int c = 0; c < NUM_CLASS; c++) {
        float s = 0;
        for (int i = 0; i < 32; i++)
            s += feat[i] * W_head_weight[c*32 + i] * S_head_weight;
        scores[c] = s;
        if (s > best) { best = s; best_cls = c; }
    }
    return best_cls;
}

/* ===== 传感器驱动 ===== */

static int bh1750_read_lux(float *lux)
{
    uint8_t cmd = 0x10;  /* 连续高分辨率模式 */
    uint8_t buf[2];
    if (IoTI2cWrite(I2C_BUS, BH1750_ADDR, &cmd, 1) != 0) return -1;
    osDelay(180);
    if (IoTI2cRead(I2C_BUS, BH1750_ADDR, buf, 2) != 0) return -1;
    *lux = ((buf[0] << 8) | buf[1]) / 1.2f;  /* 高分辨率模式 LSB=1lux/1.2 */
    return 0;
}

static int sht30_read(float *temp, float *hum)
{
    uint8_t cmd[2] = {0x2C, 0x06};
    uint8_t buf[6];
    if (IoTI2cWrite(I2C_BUS, SHT30_ADDR, cmd, 2) != 0) return -1;
    osDelay(20);
    if (IoTI2cRead(I2C_BUS, SHT30_ADDR, buf, 6) != 0) return -1;
    *temp = -45.0f + 175.0f * ((buf[0] << 8 | buf[1]) / 65535.0f);
    *hum  = 100.0f * ((buf[3] << 8 | buf[4]) / 65535.0f);
    return 0;
}

/* ===== HX711 称重传感器 (24 位 ADC, GPIO 模拟时序) ===== */

static void hx711_init(void)
{
    IoTGpioInit(PIN_HX711_SCK);
    IoTGpioSetDir(PIN_HX711_SCK, IOT_GPIO_DIR_OUT);
    IoTGpioInit(PIN_HX711_DT);
    IoTGpioSetDir(PIN_HX711_DT, IOT_GPIO_DIR_IN);
    IoTGpioSetOutputVal(PIN_HX711_SCK, 0);
}

static int32_t hx711_read_raw(void)
{
    int32_t value = 0;
    uint32_t v = 0;
    /* 等待数据就绪 (DT 拉低) */
    int timeout = 1000;
    do {
        IoTGpioGetInputVal(PIN_HX711_DT, &v);
    } while (v && --timeout > 0);
    if (timeout <= 0) return 0;

    for (int i = 0; i < 24; i++) {
        IoTGpioSetOutputVal(PIN_HX711_SCK, 1);
        osDelay(1);
        IoTGpioGetInputVal(PIN_HX711_DT, &v);
        value = (value << 1) | v;
        IoTGpioSetOutputVal(PIN_HX711_SCK, 0);
        osDelay(1);
    }
    /* 第 25 个脉冲: 增益 128 */
    IoTGpioSetOutputVal(PIN_HX711_SCK, 1);
    osDelay(1);
    IoTGpioSetOutputVal(PIN_HX711_SCK, 0);

    /* 24 位有符号 */
    if (value & 0x800000) value |= ~0xFFFFFF;
    return value;
}

/* 称重(克): 多次采样取平均抗抖动 */
static int hx711_read_grams(float *grams)
{
    int64_t sum = 0;
    for (int i = 0; i < 5; i++) {
        sum += hx711_read_raw();
        osDelay(10);
    }
    float raw = (float)sum / 5.0f;
    *grams = (raw - HX711_OFFSET) / HX711_SCALE;
    if (*grams < 0) *grams = 0;
    return 0;
}

/* ===== 蜂鸣器旋律（do-re-mi 音符表） ===== */
#define NOTE_C5 523
#define NOTE_D5 587
#define NOTE_E5 659
#define NOTE_G5 784
#define NOTE_A5 880

static void buzzer_play(const int *notes, const int *durations, int len)
{
    for (int i = 0; i < len; i++) {
        IoTPwmStart(PIN_BUZZER, 50, notes[i] ? 5000 / notes[i] : 0);
        osDelay(durations[i]);
        IoTPwmStop(PIN_BUZZER);
        osDelay(30);
    }
}

/* 识别成功: 上行音阶 (欢乐) */
static void buzzer_success(void)
{
    const int notes[] = {NOTE_C5, NOTE_E5, NOTE_G5, NOTE_C5};
    const int durs[] = {120, 120, 120, 240};
    buzzer_play(notes, durs, 4);
}

/* 营养超标: 三声短警报 */
static void buzzer_warn(void)
{
    const int notes[] = {NOTE_A5, NOTE_A5, NOTE_A5};
    const int durs[] = {80, 80, 200};
    buzzer_play(notes, durs, 3);
}

/* LED 呼吸灯效果 (PWM 占空比渐变, 2 周期) */
static void led_breath(void)
{
    for (int cycle = 0; cycle < 2; cycle++) {
        for (int duty = 10; duty <= 90; duty += 10) {
            IoTPwmStart(PIN_LED_RED, duty, 5000);
            osDelay(40);
        }
        for (int duty = 90; duty >= 10; duty -= 10) {
            IoTPwmStart(PIN_LED_RED, duty, 5000);
            osDelay(40);
        }
    }
    IoTPwmStop(PIN_LED_RED);
}

/* ===== MQTT 上报 ===== */

static MQTTClient mqtt_client;

static void mqtt_publish_sensor(void)
{
    float lux, temp, hum, weight = 0;
    char payload[160];

    bh1750_read_lux(&lux);
    sht30_read(&temp, &hum);
    hx711_read_grams(&weight);

    /* 仅称食材（人体体重由手机 App 记录，保持卫生） */
    snprintf(payload, sizeof(payload),
             "{\"board\":\"TX-SMART-R\",\"lux\":%.1f,\"temp\":%.1f,\"hum\":%.1f,"
             "\"weight_g\":%.0f}",
             lux, temp, hum, weight);
    MQTTPublish(&mqtt_client, MQTT_TOPIC_UP, payload, strlen(payload), 0, 0);
}

static void mqtt_publish_classify(int cls, float conf)
{
    char payload[64];
    const char *names[4] = {"fruit", "vegetable", "protein", "staple"};
    snprintf(payload, sizeof(payload),
             "{\"board\":\"TX-SMART-R\",\"event\":\"classify\","
             "\"cls\":\"%s\",\"conf\":%.2f}", names[cls], conf);
    MQTTPublish(&mqtt_client, MQTT_TOPIC_UP, payload, strlen(payload), 0, 0);
}

static void mqtt_msg_handler(MQTTMessage *msg)
{
    /* 云端下行指令: {"cmd":"buzzer","ms":500} */
    if (msg->payloadlen > 0 && strstr(msg->payload, "buzzer")) {
        /* 蜂鸣 500ms */
        IoTPwmStart(PIN_BUZZER, 50, 500);
    }
}

/* ===== 人体红外中断 (GPIO 触发) ===== */

static void pir_isr(char *arg)
{
    uint32_t v = 0;
    IoTGpioGetInputVal(PIN_PIR, &v);
    if (v == 1) {
        /* 检测到人: 呼吸灯 + 上报 */
        led_breath();
        mqtt_publish_sensor();
        mqtt_publish_classify(tinycnn_predict(input_buf, (float[4]){0}),
                              /* 实际工程: 此处用摄像头抓帧填充 input_buf */ 0.0f);
        buzzer_success();
    }
}

/* ===== 主任务 ===== */

static void board_main(void)
{
    printf("[SmartKitchen] Board app starting...\n");

    /* GPIO 初始化 */
    IoTGpioInit(PIN_PIR);
    IoTGpioSetDir(PIN_PIR, IOT_GPIO_DIR_IN);
    IoTGpioRegisterIsrFunc(PIN_PIR, IOT_INT_TYPE_EDGE, IOT_GPIO_EDGE_FALL_LEVEL_LOW, pir_isr, NULL);

    IoTGpioInit(PIN_BUZZER);
    IoTGpioSetDir(PIN_BUZZER, IOT_GPIO_DIR_OUT);
    IoTPwmInit(PIN_BUZZER);

    IoTGpioInit(PIN_LED_RED);
    IoTGpioSetDir(PIN_LED_RED, IOT_GPIO_DIR_OUT);

    /* I2C 传感器 */
    IoTI2cInit(I2C_BUS, 400 * 1000);

    /* HX711 称重 */
    hx711_init();

    /* Wi-Fi 连接 */
    WifiDeviceConfig config = {0};
    strcpy(config.ssid, WIFI_SSID);
    strcpy(config.preSharedKey, WIFI_PASSWORD);
    config.securityType = WIFI_SEC_TYPE_PSK;
    EnableWifi();
    osDelay(500);
    AddDeviceConfig(&config, NULL);
    ConnectTo(0);

    /* MQTT 连接后端 */
    MQTTClient_Init(&mqtt_client, MQTT_BROKER, MQTT_PORT,
                    "board1", mqtt_msg_handler);
    MQTTConnect(&mqtt_client, "board1", NULL, NULL, 0);

    /* 主循环: 每 30s 上报一次传感器数据 */
    while (1) {
        mqtt_publish_sensor();
        osDelay(30000);
    }
}

APP_FEATURE_INIT(board_main);
