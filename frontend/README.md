# 文档审查系统 - 前端项目

> 装备软件智能测试一体化解决方案 - 文档审查模块前端

## 📋 项目简介

本项目是**装备软件智能测试一体化解决方案**中"文档审查"模块的前端实现，基于"单元测试"模块的工程规范提取和改造而成。系统专注于对符合 **GJB 438C 标准**的软件文档进行智能审查和验证。

### 核心功能

#### 1. 文档上传
- 支持多种文档格式：PDF、DOC、DOCX、TXT 等
- 支持 GJB 438C 标准文档类型选择（附录 A-T，共 20 种文档类型）
- 当前版本重点支持：**软件需求规格说明**（附录 J）

#### 2. 需求分析
- 基于 GJB 438C 标准自动解析文档结构
- 构建三级需求树：文档标题 → 一级标题 → 二级标题 → 叶子节点（具体需求）
- 树形结构展示，类似 Word 导航窗格的文档大纲视图
- 实时验证每个需求节点的合规性状态

#### 3. 需求补全
- 智能识别文档中不合规或缺失的需求条目
- 基于 GJB 438C 标准提供补全建议
- 支持逐条审核补全建议（接受/拒绝）
- 白名单机制：拒绝的补全建议不会在迭代中重复出现

#### 4. 迭代验证
- 将补全后的文档重新进行合规性验证
- 确保文档最终符合 GJB 438C 标准要求

#### 5. 需求导出
- 支持导出分条的 JSON 格式需求树
- 完整保留需求层级关系和验证状态

### 支持的文档类型（GJB 438C）

| 附录 | 文档类型 | 当前支持 |
|------|----------|----------|
| 附录 A | 软件开发计划 | 规划中 |
| 附录 B | 软件安装计划 | 规划中 |
| 附录 C | 软件移交计划 | 规划中 |
| 附录 D | 软件测试计划 | 规划中 |
| 附录 E | 运行方案说明 | 规划中 |
| 附录 F | 系统/子系统规格说明 | 规划中 |
| 附录 G | 接口需求规格说明 | 规划中 |
| 附录 H | 系统/子系统设计说明 | 规划中 |
| 附录 I | 接口设计说明 | 规划中 |
| **附录 J** | **软件需求规格说明** | ✅ **已支持** |
| 附录 K | 软件设计说明 | 规划中 |
| 附录 L | 数据库设计说明 | 规划中 |
| 附录 M | 软件测试说明 | 规划中 |
| 附录 N | 软件测试报告 | 规划中 |
| 附录 O | 软件产品规格说明 | 规划中 |
| 附录 P | 软件版本说明 | 规划中 |
| 附录 Q | 软件用户手册 | 规划中 |
| 附录 R | 计算机编程手册 | 规划中 |
| 附录 S | 固件保障手册 | 规划中 |
| 附录 T | 软件研制总结报告 | 规划中 |

## 🚀 技术栈

- **Vue 3.3.11** - 渐进式 JavaScript 框架（Composition API + `<script setup>`）
- **Vite 5.0.8** - 下一代前端构建工具
- **Vue Router 4.2.5** - 官方路由管理
- **Pinia 2.1.7** - 官方状态管理库
- **Tailwind CSS 3.3.6** - 原子化 CSS 框架
- **Element Plus 2.13.2** - Vue 3 组件库（用于树形控件等复杂组件）
- **Axios 1.6.2** - HTTP 客户端
- **Lucide Vue Next 0.294.0** - 轻量级图标库
- **Highlight.js 11.9.0** - 代码高亮

## 📦 快速开始

### 前置要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

开发服务器将在 http://localhost:5173 启动

**开发模式特性**：
- 开发模式下路由守卫自动跳过，可直接访问任意页面进行开发调试
- 热模块替换（HMR）已配置，代码修改即时生效

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

## 📁 项目结构

```
CR_frontend/
├── src/
│   ├── components/          # 可复用组件
│   │   └── NavBar.vue      # 顶部导航栏（步骤进度指示器）
│   ├── views/              # 页面视图组件
│   │   ├── UploadView.vue  # 文档上传页面
│   │   ├── ParseView.vue   # 需求分析页面（树形结构展示）
│   │   ├── ReviewView.vue  # 需求补全页面（审查与补全建议）
│   │   └── ReportView.vue  # 需求导出页面（最终结果确认）
│   ├── router/
│   │   └── index.js        # 路由配置（含路由守卫）
│   ├── store/
│   │   └── index.js        # Pinia 全局状态管理（含 localStorage 持久化）
│   ├── api/
│   │   └── index.js        # API 接口封装（Axios 实例和接口方法）
│   ├── App.vue             # 根组件（布局和路由视图）
│   ├── main.js             # 应用入口文件
│   └── style.css           # 全局样式（Tailwind 指令）
├── 工程规范文档.md           # 前端工程规范（可复用于其他模块）
├── 开发设计文档.md           # 功能设计和页面逻辑说明
├── example.json            # 需求树数据结构示例
├── index.html              # HTML 入口模板
├── package.json            # 项目配置和依赖
├── vite.config.js          # Vite 构建配置（含代理和优化）
├── tailwind.config.js      # Tailwind CSS 自定义配置
├── postcss.config.js       # PostCSS 配置
└── README.md               # 项目文档（本文件）
```

## 🔧 配置说明

### API 代理配置

在 [vite.config.js](vite.config.js) 中配置后端 API 地址：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // 修改为实际后端地址
      changeOrigin: true,
    }
  }
}
```

### 开发服务器配置

```javascript
server: {
  host: '0.0.0.0',        // 监听所有网卡（支持容器/远程访问）
  port: 5173,             // 固定端口
  strictPort: true,       // 端口被占用时退出而非切换
  hmr: {
    clientPort: 5173,     // HMR 使用标准端口
  }
}
```

### 构建优化配置

项目已配置代码分割策略：
- `vendor` chunk: 核心框架（Vue、Vue Router、Pinia）
- `icons` chunk: 图标库（Lucide Vue Next）
- 自动 tree-shaking 优化

### 主题色配置

在 [tailwind.config.js](tailwind.config.js) 中自定义主色调：

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        900: '#1e3a8a',  // 主要使用的深蓝色
      }
    }
  }
}
```

## 📱 路由与页面流程

### 路由配置

项目采用 4 个主要页面，遵循非线性但有逻辑依赖的流程：

| 路由 | 组件 | 页面名称 | 依赖条件 | 说明 |
|------|------|----------|----------|------|
| `/` | UploadView | 文档上传 | 无 | 入口页面，选择文档类型并上传 |
| `/parse` | ParseView | 需求分析 | 需要 `documentId` | 展示需求树和验证状态 |
| `/review` | ReviewView | 需求补全 | 需要 `parseId` | 审查不合规需求，提供补全建议 |
| `/report` | ReportView | 需求导出 | 需要 `reviewId` | 确认最终需求树并导出 JSON |

### 路由守卫机制

**开发模式**：路由守卫自动跳过，方便开发调试各个页面

**生产模式**：严格的路由守卫确保用户按正确流程操作
- 访问 `/parse` 需要先完成文档上传
- 访问 `/review` 需要先完成需求分析
- 访问 `/report` 需要先完成需求补全

### 页面跳转流程

```
[文档上传] ──(上传成功)──→ [需求分析]
                              ↓
                         (分析完成)
                              ↓
                        [需求补全]
                          ↙     ↘
                    (迭代)     (确认导出)
                      ↓           ↓
                  [需求分析]  [需求导出]
```

**迭代机制**：
- 在需求补全页面，用户可选择"迭代"或"导出"
- 迭代：将补全后的需求树返回需求分析页面重新验证
- 导出：跳转到需求导出页面，生成最终 JSON 文件

## 💾 状态管理

使用 Pinia 管理全局状态，主要状态包括：

### State 定义

```javascript
state: {
  documentId: null,      // 上传的文档 ID
  documentName: null,    // 上传的文档名称
  parseId: null,         // 需求分析结果 ID
  reviewId: null,        // 需求补全结果 ID
  currentStep: 0,        // 当前步骤（用于导航栏高亮）
}
```

### 持久化机制

- 使用 `localStorage` 持久化 `documentId`、`documentName`、`parseId`、`reviewId`
- 页面刷新后状态自动恢复
- 提供 `clearAll()` 方法清除所有状态

### Getters

```javascript
getters: {
  hasDocument: (state) => state.documentId !== null,
  hasParsed: (state) => state.parseId !== null,
  hasReviewed: (state) => state.reviewId !== null,
}
```

### Actions

- `setDocument(id, name)` - 设置文档信息（自动清空依赖的 parseId 和 reviewId）
- `setParse(id)` - 设置解析结果（自动清空 reviewId）
- `setReview(id)` - 设置审查结果
- `clearAll()` - 清除所有状态

## 📊 数据结构

### 需求树结构

后端返回的需求树数据结构（参考 [example.json](example.json)）：

```javascript
{
  "tree": {
    "id": "root",                    // 唯一标识符（hash 或 req_{{number}}）
    "label": "MEMS陀螺软件需求规格说明",  // 节点显示标题
    "content": null,                 // 具体需求内容（叶子节点非空，非叶子节点为 null）
    "level": 0,                      // 层级：0-根, 1-一级标题, 2-二级标题, 3-叶子节点
    "v_status": true,                // 验证状态：true-合规, false-不合规
    "e_status": "pending",           // 补全状态：pending/pass/fail
    "children": [...]                // 子节点数组（叶子节点为 null）
  }
}
```

**字段说明**：
- `id`: 节点唯一标识，用于前端操作和后端通信
- `label`: 显示在树形控件中的标题
- `content`: 具体需求文本（仅叶子节点有内容）
- `level`: 
  - `0`：根节点（文档标题）
  - `1`：一级标题
  - `2`：二级标题
  - `3`：叶子节点（具体需求条目）
- `v_status`: 验证状态，用于标识是否符合 GJB 438C 标准
- `e_status`: 补全状态（当前版本可能暂不使用）
- `children`: 子节点数组，叶子节点为 `null`

### API 响应格式

**上传文档**
```javascript
POST /api/upload
Response: {
  documentId: "doc_12345",
  documentName: "软件需求规格说明.pdf"
}
```

**需求分析**
```javascript
POST /api/parse
Request: { documentId: "doc_12345" }
Response: {
  parseId: "parse_67890",
  tree: { /* 需求树结构 */ }
}
```

**需求补全**
```javascript
POST /api/review
Request: { 
  parseId: "parse_67890",
  acceptedSuggestions: ["node_1_1", "node_2_3"],
  rejectedSuggestions: ["node_3_1"]
}
Response: {
  reviewId: "review_11111",
  tree: { /* 更新后的需求树 */ }
}
```

**需求导出**
```javascript
GET /api/export/:reviewId
Response: {
  tree: { /* 最终需求树 */ },
  timestamp: "2026-02-22T10:30:00Z"
}
```

## 🎨 设计规范

### 色彩系统

- **主色调**: Primary 蓝色系（`primary-900: #1e3a8a` 为主）
- **中性色**: Slate 系列（用于文本、边框、背景）
- **功能色**: 
  - 成功: `green-500` / `green-600`
  - 错误: `red-500` / `red-600`
  - 警告: `yellow-500` / `yellow-600`
  - 信息: `blue-500` / `blue-600`

### 组件样式规范

- **圆角**: 
  - 小: `rounded-lg` (8px)
  - 中: `rounded-xl` (12px)
  - 圆形: `rounded-full`
- **阴影**: 
  - 轻: `shadow-sm`
  - 中: `shadow-md`
  - 重: `shadow-2xl`
- **间距**: 基于 4px 网格（4, 8, 16, 24, 32, 48, 64）
- **字体粗细**: 
  - 中等: `font-medium` (500)
  - 半粗: `font-semibold` (600)
  - 粗体: `font-bold` (700)

### 动画与交互

```css
/* 通用过渡 */
transition-all duration-200

/* 悬浮效果 */
hover:bg-primary-800 hover:shadow-lg

/* 点击效果 */
active:scale-95 active:shadow-sm

/* 页面切换动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
```

## 🌐 API 接口

本项目使用 Axios 进行 API 调用，所有接口封装在 [src/api/index.js](src/api/index.js) 中。

### 主要接口方法

```javascript
// 文档上传
uploadDocument(formData, docType)

// 需求分析
parseDocument(documentId)

// 需求补全（迭代）
reviewDocument(parseId, {
  acceptedSuggestions: [],
  rejectedSuggestions: []
})

// 获取审查结果
getReviewResult(reviewId)

// 导出需求树
exportRequirements(reviewId)
```

### Axios 实例配置

```javascript
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器（添加 token 等）
apiClient.interceptors.request.use(config => {
  // 可在此添加认证 token
  return config
})

// 响应拦截器（统一错误处理）
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)
```

**注意**: API 接口需要根据实际后端接口进行调整。

## 📖 开发指南

### 在组件中使用状态管理

```vue
<script setup>
import { useAppStore } from '@/store'

const store = useAppStore()

// 读取状态
console.log(store.documentId)
console.log(store.hasDocument) // getter

// 更新状态
store.setDocument('doc_123', 'example.pdf')
</script>
```

### 调用 API 接口

```vue
<script setup>
import { ref } from 'vue'
import { uploadDocument } from '@/api'

const isLoading = ref(false)
const error = ref(null)

const handleUpload = async (formData) => {
  isLoading.value = true
  error.value = null
  
  try {
    const result = await uploadDocument(formData, 'appendix_j')
    console.log('上传成功:', result)
    // 更新状态并跳转...
  } catch (err) {
    error.value = err.message
    console.error('上传失败:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
```

### 添加新页面

1. 在 `src/views/` 创建新的 Vue 组件
2. 在 `src/router/index.js` 添加路由：
   ```javascript
   {
     path: '/new-page',
     name: 'newPage',
     component: () => import('../views/NewPageView.vue'),
     meta: { title: '新页面' },
     beforeEnter: (to, from, next) => {
       // 添加路由守卫逻辑
       next()
     }
   }
   ```
3. 在 `src/components/NavBar.vue` 更新步骤导航
4. 根据需要在 `src/store/index.js` 添加状态

### 使用 Element Plus 组件

项目已集成 Element Plus，可直接使用其组件（如 Tree 树形控件）：

```vue
<script setup>
import { ElTree } from 'element-plus'
import 'element-plus/es/components/tree/style/css'

const treeData = ref([...])
</script>

<template>
  <el-tree :data="treeData" :props="treeProps" />
</template>
```

### 开发模式调试

开发模式下可以直接访问任意路由进行调试，无需完成前置步骤：

```bash
# 直接访问需求分析页面
http://localhost:5173/parse

# 直接访问需求补全页面
http://localhost:5173/review
```

## 🔄 适配其他模块

本脚手架可轻松适配其他模块（如需求理解、代码分析、单元测试等）。

### 需要修改的文件

1. **[package.json](package.json)** - 修改项目名称和描述
2. **[index.html](index.html)** - 修改页面标题
3. **[src/components/NavBar.vue](src/components/NavBar.vue)** - 修改 Logo 和步骤定义
4. **[src/router/index.js](src/router/index.js)** - 修改路由配置和守卫逻辑
5. **[src/store/index.js](src/store/index.js)** - 修改状态字段
6. **[src/api/index.js](src/api/index.js)** - 修改 API 接口
7. **[src/views/](src/views/)** - 创建对应的视图组件

### 保持不变的部分

✅ 项目整体结构  
✅ 配置文件（vite、tailwind、postcss）  
✅ 设计系统（颜色、字体、间距）  
✅ 组件样式风格  
✅ 路由守卫模式  
✅ 状态管理模式  
✅ API 封装模式  

### 复用工程规范

详细的工程规范参见 [工程规范文档.md](工程规范文档.md)，包括：
- 完整的技术栈说明
- 项目结构最佳实践
- 组件开发规范
- 代码风格指南
- 性能优化建议

## 🐛 已知问题与注意事项

### 开发阶段

- ⚠️ API 接口需要根据实际后端进行调整
- ⚠️ 需求补全功能依赖大模型，后端可能需要异步处理（前端需考虑轮询或 WebSocket）
- ⚠️ 当前版本仅支持附录 J（软件需求规格说明），其他附录尚在规划中

### 性能优化

- ✅ 已配置代码分割（vendor、icons chunk）
- ✅ 已开启 keep-alive 缓存（UploadView、ParseView）
- ✅ Element Plus 按需引入以减小打包体积
- 🔧 大型需求树展示可能需要虚拟滚动优化

### 兼容性

- 现代浏览器（Chrome、Firefox、Edge、Safari 最新版）
- 不支持 IE 11 及以下版本

## 📝 Git 提交规范（建议）

```
feat:     新功能
fix:      修复 bug
docs:     文档更新
style:    代码格式调整（不影响功能）
refactor: 代码重构
perf:     性能优化
test:     测试相关
chore:    构建/工具配置
```

**示例**：
```bash
git commit -m "feat: 添加需求树虚拟滚动支持"
git commit -m "fix: 修复路由守卫在生产环境的判断逻辑"
git commit -m "docs: 更新 API 接口文档"
```

## 📚 相关文档

- [工程规范文档.md](工程规范文档.md) - 前端工程规范（可复用于其他模块）
- [开发设计文档.md](开发设计文档.md) - 功能设计和页面逻辑详细说明
- [example.json](example.json) - 需求树数据结构示例
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [Vite 官方文档](https://cn.vitejs.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Element Plus 文档](https://element-plus.org/zh-CN/)

## 📄 许可证

本项目仅供内部使用。

---

## 👥 联系方式

如有问题或建议，请联系前端开发团队。

---

**最后更新**: 2026-02-22  
**版本**: v1.0.1  
**维护者**: 装备软件智能测试一体化解决方案团队
