# 3D 科普视频生成管线

基于 **Remotion + Three.js** 的可复用 3D 科普视频生成管线。LLM 作为"动画程序员"生成代码,渲染引擎负责出像素。

## 特性

- 🎬 **配置驱动**:每个视频 = 一个 `config.ts`,零框架改动即可新增主题
- 🎨 **抽象科技风**:深空黑 + 氖青主色 + 玻璃态材质 + 粒子系统
- 🧩 **6 个通用场景**:Hook / 网络图 / 文字碎裂 / 玻璃穿梭 / 粒子汇聚 / Outro
- 🔧 **5 个视觉原语**:可跨场景复用,支持参数化
- 📐 **横屏 16:9**:1920×1080 @ 60fps,H.264 MP4 输出
- 🎯 **多平台兼容**:B 站 / 抖音 / 快手 / 视频号 / YouTube 通用

## 快速开始

### 安装

```bash
cd remotion
pnpm install
```

### 预览

```bash
pnpm studio
# 浏览器打开 http://localhost:3000,选择 composition 预览
```

### 渲染

```bash
# 默认渲染 llm-thinking
pnpm render

# 渲染指定视频
VIDEO_ID=scenes-showcase pnpm render

# 草稿模式(低分辨率,快速验证)
pnpm render:draft
```

输出在 `video-generation/build/<video-id>/<video-id>.mp4`（成片统一目录，封面自动生成到同目录 `<video-id>_cover.png`，由 `remotion.config.ts` / `scripts/render.ts` 动态定位项目根；旧 `video-generation/out/` 已弃用）。口播 mp3 静态资源在 `video-generation/narration/`。内容视频实例在 `video-generation/remotion-videos/<id>/`，通过 webpack alias `@videos/` 引用。

## 架构

```
remotion/
├── src/
│   ├── core/                     # 框架层(跨视频稳定)
│   │   ├── types.ts              # VideoConfig / SceneConfig 接口
│   │   ├── theme.ts              # 默认 theme token(可被视频覆盖)
│   │   ├── VideoComposition.tsx  # 通用 composition,按 config 装配场景
│   │   └── SubtitleOverlay.tsx   # 通用字幕叠加层
│   ├── primitives/               # 视觉原子(跨场景复用)
│   │   ├── ParticleField.tsx     # 3D 粒子系统
│   │   ├── GlassPanel.tsx        # 玻璃态平面
│   │   ├── NeonText.tsx          # 霓虹发光文字
│   │   ├── Scanline.tsx          # 扫描线特效
│   │   └── CameraPath.tsx        # 摄像机路径动画
│   ├── scenes/                   # 通用场景库(参数化)
│   │   ├── HookTitle.tsx         # 开场 Hook(标题飞入)
│   │   ├── NetworkGraph.tsx      # 3D 网络图
│   │   ├── TextShatter.tsx       # 文字碎裂成 token
│   │   ├── GlassFlythrough.tsx   # 摄像机穿梭玻璃层
│   │   ├── ParticleCollapse.tsx  # 粒子汇聚成文字
│   │   ├── Outro.tsx             # 结尾 CTA
│   │   └── registry.ts           # 场景注册表
│   └── videos/                   # 视频实例(每视频一个目录)
│       ├── llm-thinking/         # "LLM 是怎么思考的" 30 秒
│       ├── scenes-showcase/      # 6 个场景展示
│       ├── dummy-2/              # 可复用性验证(紫色主题)
│       └── ...
└── scripts/
    └── render.ts                 # 渲染脚本(支持 VIDEO_ID 切换)
```

## 新增视频(关键!)

**加新视频 = 加一个 config 文件,不改框架代码。**

### 步骤

1. **创建视频目录**:`src/videos/<your-video>/`
2. **创建 config.ts**:

```typescript
// src/videos/my-video/config.ts
import type { VideoConfig } from "../../core/types";

export const myVideoConfig: VideoConfig = {
  id: "my-video",
  title: "我的视频标题",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "HookTitle",
      props: {
        title: "开场标题",
        subtitle: "副标题",
        enterFrom: "depth", // "depth" | "top" | "bottom"
      },
      durationInFrames: 180, // 3 秒 @ 60fps
    },
    // ... 更多场景
    {
      type: "Outro",
      props: { ctaText: "关注,看懂 AI" },
      durationInFrames: 180,
    },
  ],
  subtitles: [
    { text: "字幕文字", startFrame: 30, endFrame: 150 },
    // ...
  ],
  // 可选:覆盖主题色
  themeOverrides: {
    colors: {
      accent: "#a855f7", // 电光紫
      background: "#1a0a29",
    },
  },
};
```

3. **在 Root.tsx 注册**:

```typescript
// src/Root.tsx
import { myVideoConfig } from "./videos/my-video/config";

const allConfigs = [/* ... */, myVideoConfig];
```

4. **渲染**:

```bash
VIDEO_ID=my-video pnpm render
```

### 可选:添加背景音乐

1. 下载 CC0 音乐(推荐 [Pixabay Music](https://pixabay.com/music/) / [YouTube Audio Library](https://studio.youtube.com/channel/UC/music))
2. 放到 `src/videos/<your-video>/assets/bgm.mp3`
3. 在 config 中指定:

```typescript
audioPath: "my-video/assets/bgm.mp3",
```

## 可用场景

| 场景类型 | 用途 | 关键 Props |
|---------|------|-----------|
| `HookTitle` | 开场 3-5 秒 | `title`, `subtitle`, `enterFrom` |
| `NetworkGraph` | 网络/参数/连接可视化 | `nodeCount`, `label` |
| `TextShatter` | 文字碎裂/分词 | `inputText`, `tokenList`, `scatterPattern` |
| `GlassFlythrough` | 多层穿梭/Transformer | `layerCount` |
| `ParticleCollapse` | 汇聚/答案生成 | `targetText`, `collapseDuration`, `transitionTo2D` |
| `Outro` | 结尾 CTA | `logo`, `ctaText` |

## 视觉风格

**默认主题**:抽象科技风

- 背景:深空黑 `#0a0e1a` / 暗蓝 `#0a1929`
- 主色:氖青 `#00d9ff`
- 文字:白 `#ffffff` + 弱化灰 `#94a3b8`
- 字体:思源黑体(中文) / Orbitron(英文) / JetBrains Mono(等宽)

通过 `themeOverrides` 可局部覆盖(参见 `dummy-2` 示例)。

## 许可证

### 代码

MIT

### 字体

- 思源黑体:OFL (SIL Open Font License)
- Orbitron:OFL
- JetBrains Mono:OFL

### 音乐

需用户自行提供 CC0 音乐,本项目不包含音乐文件。

## 故障排查

### 渲染慢

- 使用 `pnpm render:draft` 草稿模式(低分辨率 + 跳帧)
- 或临时改 `config.fps` 为 30

### 3D 元素不显示

- 确认场景在 `ThreeCanvas` 内使用 `primitive`
- 检查摄像机位置是否离内容太远

### 字幕不显示

- 检查 `subtitles` 数组的 `startFrame` / `endFrame` 是否在视频时长范围内
- 确认字幕文字不为空

## 技术栈

- **Remotion 4.x**:React 视频框架
- **@remotion/three**:Three.js 集成
- **Three.js 0.168**:3D 渲染
- **React 19**:UI 框架
- **TypeScript 5.5**:类型安全

## 参考

- [Remotion 文档](https://www.remotion.dev/docs)
- [@remotion/three 文档](https://www.remotion.dev/docs/three)
- [Three.js 文档](https://threejs.org/docs/)

---

**视觉上限由渲染引擎决定,LLM 只是帮你写"给渲染引擎的指令"。**
