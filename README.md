# 🅿️ 智能停车管理系统 (Smart Parking Management System)

基于 AI 视觉识别的智能停车场管理系统，采用 YOLOv8 + PaddleOCR 实现车牌自动识别，支持车辆进出管理、智能计费、数据分析等功能。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Latest-orange)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.0-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 目录

- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [安装部署](#安装部署)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [更新日志](#更新日志)

---

## 🚀 核心功能

### 1️⃣ 车辆进出管理
- ✅ **AI 车牌识别**：基于 YOLOv8 检测 + PaddleOCR 识别
- ✅ **双模式支持**：模拟模式（上传图片）/ 实况模式（摄像头）
- ✅ **识别容错**：识别失败时支持手动输入，无阻塞式交互
- ✅ **实时反馈**：识别结果可视化显示（标注框 + 车牌文字）
- ✅ **重复检测**：自动识别车辆是否已在场

### 2️⃣ 智能计费系统
- 💰 **灵活费率**：按小时计费，支持封顶费用
- 💰 **免费时长**：可配置免费停车时长
- 💰 **VIP 免费**：白名单车辆自动识别并免费放行
- 💰 **自动计算**：出场时自动计算停车时长和费用

### 3️⃣ 数据管理与分析
- 📊 **实时监控**：车位占用率、今日流量、营收统计
- 📊 **数据追溯**：完整的进出记录查询，支持多条件筛选
- 📊 **记录编辑**：管理员可修改记录，操作自动记录日志
- 📊 **数据大屏**：可视化图表展示车流趋势、费用分布等
- 📊 **影像档案**：自动保存进出场抓拍照片

### 4️⃣ 系统管理
- 👥 **账号管理**：多用户、角色权限控制
- 🏷️ **白名单维护**：VIP 车辆管理
- ⚙️ **停车场配置**：费率、车位数、免费时长等参数设置
- 📢 **系统公告**：支持发布和管理系统通知
- 🤖 **AI 助手**：集成 Moonshot AI (Kimi)，实时解答业务问题

### 5️⃣ 操作日志
- 📝 **完整审计**：记录所有管理员操作
- 📝 **数据留痕**：修改前后值对比（JSON 格式）
- 📝 **追溯能力**：操作人、时间、IP 地址完整记录

---

## 🛠 技术栈

### 后端技术
| 技术 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.8 - 3.10 | 推荐 3.8 或 3.9（PaddlePaddle 兼容性最佳） |
| **Flask** | 2.3.3 | 轻量级 Web 框架 |
| **SQLAlchemy** | 2.0.20 | ORM 数据库操作 |
| **SQLite** | 3.x | 嵌入式数据库 |

### AI 引擎
| 技术 | 版本 | 用途 |
|------|------|------|
| **YOLOv8** | 8.0.196 | 车牌区域检测 |
| **PaddleOCR** | 2.7.0 | 车牌文字识别（中文优化） |
| **OpenCV** | 4.8.0 | 图像处理与标注 |

### 前端技术
| 技术 | 版本 | 说明 |
|------|------|------|
| **Bootstrap 5** | 5.3.1 | 响应式 UI 框架 |
| **jQuery** | 3.7.1 | DOM 操作与 AJAX |
| **Chart.js** | 4.4.0 | 数据可视化图表 |
| **Font Awesome** | 6.4.2 | 图标库 |

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端界面 (Web UI)                       │
│  Bootstrap 5 + jQuery + Chart.js + Jinja2 模板引擎           │
└─────────────────────┬───────────────────────────────────────┘
                      │ AJAX / HTTP
┌─────────────────────┴───────────────────────────────────────┐
│                    Flask Web 应用层                          │
│  - 路由控制 (app.py)                                         │
│  - 业务逻辑 (services.py)                                    │
│  - 用户认证 (Flask-Login)                                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
│ AI 识别层 │  │ 数据库层  │  │ 外部集成  │
│           │  │           │  │           │
│ YOLOv8    │  │ SQLite    │  │ Moonshot  │
│ PaddleOCR │  │ SQLAlchemy│  │ AI (Kimi) │
│ OpenCV    │  │           │  │           │
└───────────┘  └───────────┘  └───────────┘
```

---

## 📦 安装部署

### 前置要求
- **Python**: 3.8 / 3.9 / 3.10（推荐 3.8 或 3.9）
- **操作系统**: Windows / Linux / macOS
- **摄像头**（可选）：用于实况模式

### 1. 克隆项目
```bash
git clone <repository-url>
cd licensePlateDetection
```

### 2. 创建虚拟环境（推荐）
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

**⚠️ 注意事项：**
- 如果使用 **Python 3.11+**，PaddleOCR 可能无法正常工作
- Windows 用户可能需要安装 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- 如需 GPU 加速，请安装 `paddlepaddle-gpu` 替代 `paddlepaddle`

### 4. 初始化数据库
```bash
python run.py
```
首次运行会自动创建数据库并初始化：
- 默认管理员账号：`admin`
- 默认密码：`admin123`

### 5. 访问系统
打开浏览器访问：[http://localhost:5000](http://localhost:5000)

---

## 📖 使用指南

### 登录系统
1. 使用默认账号 `admin` / `admin123` 登录
2. 首次登录后建议修改密码

### 车辆入场流程
1. 点击左侧菜单"**车辆入场**"
2. **模拟模式**（推荐测试）：
   - 上传车辆图片
   - 点击"确认入场"
   - 系统自动识别车牌并入库
3. **实况模式**（需摄像头）：
   - 切换到实况模式
   - 系统调用摄像头实时拍摄
   - 点击"确认入场"完成识别

### 车辆出场流程
1. 点击"**车辆出场**"
2. 上传车辆图片或使用摄像头
3. 系统自动：
   - 识别车牌
   - 查询入场记录
   - 计算停车时长和费用
   - 显示应付金额

### 白名单管理
1. 进入"**白名单维护**"
2. 添加 VIP 车牌号
3. VIP 车辆自动免费放行

### AI 助手配置
1. 进入"**AI 助手配置**"
2. 填入 Moonshot AI 的 API Key
3. 设置助手角色和模型参数
4. 点击右下角聊天图标使用

---

## ⚙️ 配置说明

### 停车场配置
路径：**系统管理 → 停车场配置**

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 车位总数 | 停车场总车位数量 | 100 |
| 小时费率 | 每小时停车费（元） | 5.0 |
| 免费时长 | 免费停车时长（分钟） | 30 |
| 封顶费用 | 单日最高费用（元） | 50.0 |

### AI 识别参数
文件：`app/services.py`

```python
# YOLO 检测置信度阈值
results = model(img, conf=0.4)  # 调整 0.4 以改变检测灵敏度

# OCR 重试次数
for attempt in range(3):  # 识别失败时重试 3 次
```

### 摄像头配置
文件：`app/app.py`

```python
# 摄像头 ID 设置
cam_id = 0 if mode == 'entry' else 1
# 入场：摄像头0，出场：摄像头1
```

### AI 助手配置（可选）
路径：**系统管理 → AI 助手配置**

本系统集成了 **Moonshot AI (Kimi)** 智能客服功能。

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **API Key** | Moonshot AI 平台密钥 | `sk-xxxxxxxxxxxxxxxx` |
| **模型版本** | 选择使用的模型 | `moonshot-v1-8k`（推荐） |
| **角色提示** | 自定义 AI 行为 | "你是一个专业的停车助手..." |

**配置步骤**：
1. 访问 [Moonshot AI 开放平台](https://platform.moonshot.cn/) 注册账号
2. 在控制台创建 API Key
3. 在系统的"AI 助手配置"页面填写 API Key
4. 点击"测试连接"验证配置是否正确

**详细文档**：
- 📚 [AI 配置指南](docs/AI_CONFIG.md)
- 🔧 [故障排查手册](docs/AI_TROUBLESHOOTING.md)

---

## 📁 项目结构

```
licensePlateDetection/
├── app/                          # 主应用目录
│   ├── __init__.py
│   ├── app.py                    # Flask 主程序、路由定义
│   ├── models.py                 # 数据库模型（ORM）
│   ├── services.py               # 业务逻辑（车辆进出处理）
│   ├── static/                   # 静态资源
│   │   ├── css/
│   │   │   └── style.css         # 自定义样式
│   │   └── uploads/              # 上传的图片文件
│   └── templates/                # HTML 模板
│       ├── base.html             # 基础模板（导航栏、模态框）
│       ├── index.html            # 仪表盘
│       ├── login.html            # 登录页面
│       ├── admin/                # 管理页面
│       │   ├── garage.html       # 停车场配置
│       │   ├── whitelist.html    # 白名单管理
│       │   ├── users.html        # 用户管理
│       │   ├── notices.html      # 系统公告管理
│       │   └── ai_settings.html  # AI 助手配置
│       └── data/                 # 数据页面
│           ├── history.html      # 数据追溯
│           └── analysis.html     # 数据大屏
├── utils/                        # 工具模块
│   ├── __init__.py
│   └── plate_ocr_paddle.py       # PaddleOCR 封装
├── runs/                         # YOLO 训练输出
│   └── train/yolov8n/weights/
│       └── best.pt               # 训练好的 YOLO 模型
├── datasets/                     # 训练数据集（可选）
├── tests/                        # 单元测试
├── requirements.txt              # Python 依赖清单
├── run.py                        # 启动脚本
├── parking_system.db             # SQLite 数据库文件
└── README.md                     # 本文档
```

---

## ❓ 常见问题

### 1. PaddleOCR 初始化失败
**错误信息**：`cannot import name 'libpaddle'`

**解决方案**：
- 确保使用 Python 3.8 - 3.10
- 卸载并重新安装 PaddleOCR：
  ```bash
  pip uninstall paddlepaddle paddleocr
  pip install paddlepaddle==2.5.1
  pip install paddleocr==2.7.0
  ```

### 2. 识别循环失败（成功→失败→成功）
**原因**：PaddleOCR 连续调用时内部状态问题

**解决方案**：
- 已在 `utils/plate_ocr_paddle.py` 中添加强制重新初始化机制
- 识别失败后会自动重置 OCR 引擎

### 3. 摄像头无法打开
**错误信息**：`could not grab frame`

**解决方案**：
- 确保摄像头未被其他程序占用
- 检查摄像头 ID 是否正确（通常为 0）
- Windows 用户检查摄像头权限设置

### 4. 识别速度慢
**优化建议**：
- 使用 GPU 版本的 PaddlePaddle
- 降低 YOLO 置信度阈值（`conf=0.3`）
- 减少 OCR 重试次数

### 5. AI 助手不可用
**错误信息**：`AI 服务暂时不可用，请检查网络或 API Key`

**常见原因**：
- 未配置 Moonshot AI API Key
- API Key 无效或已过期
- 网络连接问题
- API 调用配额不足

**解决方案**：
1. 进入"AI 助手配置"页面配置 API Key
2. 点击"测试连接"按钮验证配置
3. 查看详细的错误提示信息
4. 参考 [AI 故障排查手册](docs/AI_TROUBLESHOOTING.md)

---

## 📝 更新日志

### v2.0.0 (2025-12-04)
- ✨ 新增：非阻塞式手动输入，实况模式更流畅
- ✨ 新增：数据追溯支持编辑记录功能
- ✨ 新增：操作日志系统，完整审计追溯
- ✨ 新增：系统公告管理模块
- 🐛 修复：PaddleOCR 连续调用失败问题
- 🐛 修复：识别结果循环失败的状态问题
- ⚡ 优化：OCR 重试机制（3次 + 强制重新初始化）
- ⚡ 优化：图像裁剪边界智能扩展
- ⚡ 优化：首页布局，新增全局输入模式切换
- 📚 文档：完善 README 和依赖清单

### v1.0.0 (Initial Release)
- 🎉 基础车辆进出管理功能
- 🎉 YOLOv8 + PaddleOCR 车牌识别
- 🎉 智能计费系统
- 🎉 数据分析与可视化
- 🎉 用户权限管理

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 📮 GitHub Issues
- 📧 Email: [1491354106@qq.com]
---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给个 Star！⭐**

Made with ❤️ by [于宪森]


</div>


