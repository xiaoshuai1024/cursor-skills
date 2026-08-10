import React from "react";

/**
 * MockProductPage - 模拟电商 H5 页面(375 视口)。
 * 用于 PixelDiff 的"原型 vs 实现"对比。
 *
 * 通过 props 制造差异:
 * - shifted: 实现版按钮位置偏移(样式偏差)
 * - extraBlock: 实现版多了功能区(内容演进)
 * - grayImages: 图片拦截成灰块(只比布局)
 */

interface MockProductPageProps {
  shifted?: boolean;
  extraBlock?: boolean;
  grayImages?: boolean;
}

const imgBg = (grayImages?: boolean, color = "#e2e8f0") =>
  grayImages ? "#e0e0e0" : color;

export const MockProductPage: React.FC<MockProductPageProps> = ({
  shifted = false,
  extraBlock = false,
  grayImages = false,
}) => {
  return (
    <div style={{ width: "100%", height: "100%", backgroundColor: "#f8fafc", fontFamily: "-apple-system, sans-serif", color: "#0f172a" }}>
      {/* 顶部导航 */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 14px", backgroundColor: "#fff", borderBottom: "1px solid #e2e8f0",
      }}>
        <span style={{ fontSize: 18 }}>‹</span>
        <span style={{ fontSize: 14, fontWeight: 600 }}>商品详情</span>
        <span style={{ fontSize: 18 }}>⋯</span>
      </div>

      {/* 商品主图 */}
      <div style={{ width: "100%", height: 180, backgroundColor: imgBg(grayImages, "#fef3c7"), display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 13, color: "#94a3b8" }}>{grayImages ? "图片已拦截" : "主图"}</span>
      </div>

      {/* 标题 + 价格 */}
      <div style={{ padding: "12px 14px", backgroundColor: "#fff" }}>
        <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.3 }}>商品标题文字示例</div>
        <div style={{ marginTop: 8, display: "flex", alignItems: "baseline", gap: 8 }}>
          <span style={{ fontSize: 22, color: "#dc2626", fontWeight: 800 }}>¥99</span>
          <span style={{ fontSize: 12, color: "#94a3b8", textDecoration: "line-through" }}>¥199</span>
        </div>
      </div>

      {/* 规格选择 */}
      <div style={{ padding: "10px 14px", backgroundColor: "#fff", marginTop: 8, display: "flex", gap: 8 }}>
        {["规格A", "规格B", "规格C"].map((s) => (
          <span key={s} style={{ fontSize: 12, padding: "4px 10px", border: "1px solid #cbd5e1", borderRadius: 4 }}>{s}</span>
        ))}
      </div>

      {/* 实现版多出的功能区(内容演进) */}
      {extraBlock && (
        <div style={{ margin: "8px 14px", padding: 14, backgroundColor: "#dbeafe", borderRadius: 6, border: "1px dashed #2563eb" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#1e40af" }}>新功能:搭配推荐</div>
          <div style={{ fontSize: 11, color: "#3b82f6", marginTop: 4 }}>买了这个的人还买了…</div>
        </div>
      )}

      {/* 底部购物车栏 */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        display: "flex", alignItems: "center", gap: 12,
        padding: "10px 14px", backgroundColor: "#fff", borderTop: "1px solid #e2e8f0",
        // shifted: 制造按钮偏移
        paddingLeft: shifted ? 30 : 14,
      }}>
        <div style={{ position: "relative" }}>
          <div style={{ fontSize: 22 }}>🛒</div>
          {/* 红色角标(会被 vision 误认成客服按钮) */}
          <span style={{
            position: "absolute", top: -4, right: -6,
            backgroundColor: "#dc2626", color: "#fff",
            fontSize: 10, fontWeight: 700,
            borderRadius: 8, padding: "1px 5px",
          }}>3</span>
        </div>
        <div style={{
          flex: 1, height: 36, borderRadius: 18,
          backgroundColor: "#16a34a", color: "#fff",
          fontSize: 14, fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          立即购买
        </div>
      </div>
    </div>
  );
};
