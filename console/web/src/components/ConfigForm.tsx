import { useState, useEffect } from "react";
import type { Mode, WebConfig, MobileConfig } from "../types";

const API = "/api";

interface Props {
  mode: Mode;
  disabled: boolean;
}

const webFields: { key: keyof WebConfig; label: string; type: string; placeholder?: string }[] = [
  { key: "target_url", label: "演出URL", type: "text", placeholder: "https://detail.damai.cn/item.htm?id=..." },
  { key: "users", label: "观演人（逗号分隔）", type: "text", placeholder: "张三,李四" },
  { key: "city", label: "城市", type: "text", placeholder: "北京" },
  { key: "dates", label: "场次日期（逗号分隔）", type: "text", placeholder: "2026-06-15,2026-06-16" },
  { key: "prices", label: "票价（逗号分隔）", type: "text", placeholder: "480,680" },
  { key: "max_retries", label: "最大重试次数", type: "number" },
];

const mobileFields: { key: keyof MobileConfig; label: string; type: string; placeholder?: string }[] = [
  { key: "server_url", label: "Appium 服务器", type: "text", placeholder: "http://127.0.0.1:4723" },
  { key: "keyword", label: "搜索关键词", type: "text", placeholder: "周杰伦" },
  { key: "users", label: "观演人（逗号分隔）", type: "text", placeholder: "张三,李四" },
  { key: "city", label: "城市", type: "text", placeholder: "北京" },
  { key: "date", label: "日期 (MM.DD)", type: "text", placeholder: "06.15" },
  { key: "price", label: "票面描述", type: "text", placeholder: "内场680元" },
  { key: "price_index", label: "票档序号", type: "number", placeholder: "1" },
];

export default function ConfigForm({ mode, disabled }: Props) {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadConfig();
  }, [mode]);

  const loadConfig = async () => {
    try {
      const r = await fetch(`${API}/config?mode=${mode}`);
      const d = await r.json();
      setConfig(d.config || {});
    } catch {}
  };

  const handleChange = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleBoolChange = (key: string, checked: boolean) => {
    setConfig((prev) => ({ ...prev, [key]: checked }));
    setSaved(false);
  };

  const handleSave = async () => {
    // 处理数组字段
    const data: Record<string, any> = { ...config };
    if (data.users && typeof data.users === "string") data.users = data.users.split(",").map((s: string) => s.trim()).filter(Boolean);
    if (data.dates && typeof data.dates === "string") data.dates = data.dates.split(",").map((s: string) => s.trim()).filter(Boolean);
    if (data.prices && typeof data.prices === "string") data.prices = data.prices.split(",").map((s: string) => s.trim()).filter(Boolean);
    if (data.price_index) data.price_index = Number(data.price_index);
    if (data.max_retries) data.max_retries = Number(data.max_retries);

    try {
      const r = await fetch(`${API}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, config: data }),
      });
      const d = await r.json();
      if (d.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        alert("保存失败: " + (d.errors?.join(", ") || "未知错误"));
      }
    } catch (e) {
      alert("请求失败");
    }
  };

  const handleLoad = () => loadConfig();

  const fields = mode === "web" ? webFields : mobileFields;

  const getDisplayValue = (key: string) => {
    const val = config[key];
    if (Array.isArray(val)) return val.join(", ");
    return val ?? "";
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">⚙️ 配置</h2>
        <div className="flex gap-2">
          <button
            onClick={handleLoad}
            disabled={disabled}
            className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-gray-200"
          >
            刷新
          </button>
          <button
            onClick={handleSave}
            disabled={disabled}
            className={`px-3 py-1 text-xs rounded font-medium transition ${
              saved ? "bg-emerald-600 text-white" : "bg-emerald-700 hover:bg-emerald-600 text-white"
            } disabled:opacity-40`}
          >
            {saved ? "✓ 已保存" : "保存配置"}
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {fields.map(({ key, label, type, placeholder }) => (
          <div key={key}>
            <label className="block text-xs text-gray-400 mb-1">{label}</label>
            <input
              type={type}
              value={getDisplayValue(key)}
              onChange={(e) => handleChange(key, e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-emerald-500 disabled:opacity-50 transition"
            />
          </div>
        ))}

        {/* Booleans */}
        <div className="flex items-center gap-4 pt-2">
          {mode === "web" && (
            <>
              <label className="flex items-center gap-2 text-xs text-gray-400">
                <input
                  type="checkbox"
                  checked={!!config.if_listen}
                  onChange={(e) => handleBoolChange("if_listen", e.target.checked)}
                  disabled={disabled}
                  className="accent-emerald-600"
                />
                监听开票
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-400">
                <input
                  type="checkbox"
                  checked={!!config.fast_mode}
                  onChange={(e) => handleBoolChange("fast_mode", e.target.checked)}
                  disabled={disabled}
                  className="accent-emerald-600"
                />
                快速模式
              </label>
            </>
          )}
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={!!config.if_commit_order}
              onChange={(e) => handleBoolChange("if_commit_order", e.target.checked)}
              disabled={disabled}
              className="accent-emerald-600"
            />
            自动下单
          </label>
        </div>
      </div>
    </div>
  );
}
