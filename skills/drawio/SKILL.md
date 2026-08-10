---
name: drawio
description: 用 draw.io (mxGraph XML) 画架构图/部署图/数据流/分层架构等规整技术图，并通过 drawio CLI 导出 SVG 放进博客 static/。替代 mermaid 机器图、去 AI 味。概念图/对比图/流程梗图请改用 Excalidraw 手绘风。
---

# draw.io 画图

## 何时用本 skill
- 架构图、部署拓扑、数据流、分层架构、时序图——信息密度高、需要对齐规整
- 概念图、对比图、心智模型、流程梗图 → 用 Excalidraw（手绘风），**不要**用这里

## 核心原则：去 AI 味（这本来就是用 draw.io 替换 mermaid 的全部意义）
mermaid 的机器味来自三点：花花绿绿的填充、对仗式短语标签、所有元素等大等距。draw.io 手画时要反着来：

- **配色克制**：白底为主，最多 1 个主色（推荐 `#2563eb` 蓝 或 `#0f766e` 青绿）+ 深灰文字 `#1e293b`。只有强调框才填色，普通框白底描边。
- **禁止** `fill:#e8f5e8` 这类浅色填充，禁止彩虹配色。
- **字号层级**：主框标题 14px 粗体，子项 12px 常规。
- **留白**：框间距 ≥ 40px，不要挤成一团。
- **箭头统一**：`edgeStyle=orthogonalEdgeStyle`，全图一种样式，不要有的弯有的直。
- **标签说人话**：不要"多端适配，统一交互"这种对仗短语，直接写"PC / H5 / 小程序三端"。

## 工作流
1. 读文章里要配图的段落，确定图类型 + 要表达的关系
2. 生成 draw.io XML（mxGraph 格式）—— 语法权威 reference 见下
3. 写源文件到 `static/diagrams-src/<slug>.drawio`（进版本管理，可二次编辑）
4. 导出 SVG：
   `drawio --export --format svg --embed-diagram --output static/svg/<slug>.svg static/diagrams-src/<slug>.drawio`
   - `--embed-diagram` 让导出的 SVG 内嵌 XML，之后还能在 draw.io 里改
5. 文章里引用：`![<alt 文本>](/svg/<slug>.svg)`
   - 需要带说明/居中/暗色适配时，用 FixIt 的 `{{< image >}}` shortcode

## XML 语法（权威 single source of truth）
完整语法（edge routing、containers/layers、所有 style properties、XML 规范）在官方文档，**画图前先读这一个文件**：
https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-reference.md

## 最小可用骨架
```xml
<mxfile host="app.diagrams.net">
  <diagram name="架构图" id="arch1">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="826" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="client" value="浏览器" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#2563eb;fontColor=#1e293b;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="80" y="80" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="bff" value="BFF (Node)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dbeafe;strokeColor=#2563eb;fontColor=#1e293b;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="320" y="80" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#64748b;fontSize=11;" edge="1" parent="1" source="client" target="bff">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```
要点：每个 vertex/edge 必须有唯一 `id` 且 `parent="1"`；边用 `source`/`target` 引用节点 id；坐标 `x/y/width/height` 手动布局——**draw.io 的"人味"正来自不完美的手工坐标，不要让所有元素等距对齐**。

## 常用 style 速查
- 圆角框：`rounded=1;whiteSpace=wrap;html=1;`
- 数据库：`shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;`
- 容器分组：`container=1;collapsible=0;`（子元素 parent 指向容器 id）
- 直线箭头：`edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#64748b;`
- 云/AWS/Azure/K8s 等图标：用 draw.io 的 shape search 找精确 style 串

## Windows 环境注意
- draw.io Desktop 装好后，CLI 命令是 `drawio`（个别环境是 `draw.io`）
- 若 PATH 没找到，可执行文件一般在 `C:\Program Files\draw.io\draw.io.exe`
- 导出大图可能要几秒，属正常
