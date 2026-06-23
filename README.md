# 无人车数据中台

一期项目包含 FastAPI 后端、Vue 管理后台、MySQL 数据库和 MQTT Broker，
用于接入新石器、九识无人车数据，并向成都市智能网联汽车监管平台按 TCP/TLS 二进制协议上报。

## 目录

- `backend/`：FastAPI 服务、数据库模型、厂商适配器、标准化处理、成都市协议编码。
- `frontend/`：Vue 管理后台。
- `database/schema.sql`：MySQL 建表脚本和成都市平台初始配置。
- `docs/无人车数据中台需求文档.md`：需求文档。
- `mqtt/`：MQTT Broker 配置（九识数据推送入口）。

## 快速启动

### 1. 启动基础设施（MySQL + MQTT Broker）

```bash
docker compose up -d mysql mqtt
```

- MySQL：`localhost:3306`，库 `vehicle_data_hub`，root 密码 `password`
- MQTT  Broker：`localhost:1883`，用户名 `jiushi_user` / `hub_client`

> **MQTT Broker 密码需要修改**：将 `mqtt/passwd` 中的默认密码替换为实际密码，然后执行：
> ```bash
> docker exec vehicle-data-hub-mqtt mosquitto_passwd -b /mosquitto/config/passwd <username> <new_password>
> ```

### 2. 启动后端

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档地址：`http://127.0.0.1:8000/docs`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

管理后台地址：`http://127.0.0.1:5173`  
默认登录：`admin / change-me`（生产环境请修改 `.env` 中的 `SECRET_KEY`）

## 厂商对接指南

### 新石器（HTTP 拉取模式）

向新石器获取以下信息，填入管理后台「厂商接入」：
- `client_id`、`client_secret`（API 鉴权）
- `base_url`（测试/生产环境地址）

### 九识（MQTT 推送模式，模式 B）

```
┌──────────┐  推送数据    ┌──────────────┐  订阅消费   ┌──────────┐
│  九识     │ ─────────→ │ 企业 MQTT     │ ←──────── │  数据中台  │
│ (发布者)  │            │ Broker       │            │ (订阅者)  │
└──────────┘            └──────────────┘            └──────────┘
```

1. **企业**搭建 MQTT Broker（项目已内置 Mosquitto，`docker compose up -d mqtt`）
2. **企业**将 Broker 的 `host/port/username/password` 提供给**九识**
3. **九识**提供 `organizationCode`，配置后将车辆数据推送到企业 Broker
4. **中台**作为 MQTT 客户端连接自有 Broker，订阅 `{orgCode}/vehicle/+/realtime/push`

在管理后台「厂商接入」填入：
```json
公开配置:
{
  "organization_code": "九识提供的企业编码",
  "mqtt_host": "127.0.0.1",
  "mqtt_port": 1883
}
敏感配置:
{
  "mqtt_username": "jiushi_user",
  "mqtt_password": "你的MQTT密码"
}
```

## 已实现的一期能力

- 厂商账号配置：新石器 HTTP、九识 MQTT 推送（模式 B）。
- 监管平台配置：成都市平台地址、坐标系、上报频率。
- 车辆档案管理：车辆主档、监管车辆编号绑定。
- 证书上传接口：车辆 TLS 证书、私钥、CA 文件元数据管理。
- 标准化模型：统一车辆位置、运动、控制、能源、车身、故障和数据质量字段。
- 新石器适配器：Token、签名、车辆列表、批量实时信息接口封装。
- 九识适配器：MQTT Broker 连接、topic 订阅、实时/业务数据标准化。
- 成都市协议：准静态参数(0x34)、运行状态(0x15)、故障状态(0x5c) 二进制编码与解码。
- 上报状态机：TLS 握手→0x34→等待0x35确认→周期上报，自动重连（指数退避）。
- 频率补齐：strict / repeat / linear 三种策略，数据质量标记。
- 告警系统：厂商断连、TLS握手失败、证书缺失/过期、数据超时自动告警（带去重）。
- 认证系统：Token 认证，登录/登出。
- 管理后台：概览、厂商、监管平台、车辆、证书、实时状态、上报监控、告警、映射配置。

## 需要联调确认

- 新石器接口真实限流和实时刷新频率。
- 九识推送数据的实际 topic 格式和字段映射。
- 成都市监管平台是否允许源数据低频时复用最近值补齐 10Hz。
- 每车 TLS 证书和监管车辆编号的实际发放流程。

