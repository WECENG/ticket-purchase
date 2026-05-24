import { useState, useEffect, useCallback } from "react";
import type { Mode, WebConfig, MobileConfig, StatusData, LogEntry } from "./types";
import ConfigForm from "./components/ConfigForm";
import ControlBar from "./components/ControlBar";
import LogViewer from "./components/LogViewer";

const API = "/api";

export default function App() {
  const [mode, setMode] = useState<Mode>("web");
  const [status, setStatus] = useState<StatusData>({ running: false, mode: "", pid: null, startTime: null, elapsed: 0 });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [checkResult, setCheckResult] = useState<{ success: boolean; output: string[] } | null>(null);
  const [checking, setChecking] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  // WebSocket 连接
  const connectWs = useCallback(() => {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${location.host}/ws/logs`);
    socket.onmessage = (e) => {
      const msg: LogEntry = JSON.parse(e.data);
      if (msg.type === "status") { setStatus(msg.data as StatusData);
      } else {
        setLogs((prev) => [...prev.slice(-500), msg]);
      }
    };
    socket.onclose = () => setTimeout(connectWs, 2000);
    socket.onerror = () => socket.close();
    setWs(socket);
    return socket;
  }, []);

  useEffect(() => {
    const s = connectWs();
    fetchStatus();
    loadConfig();
    return () => s.close();
  }, []);

  const fetchStatus = async () => {
    try {
      const r = await fetch(`${API}/status`);
      const d = await r.json();
      setStatus(d);
    } catch {}
  };

  const loadConfig = async () => {
    try {
      const r = await fetch(`${API}/config?mode=${mode}`);
      const d = await r.json();
      return d.config;
    } catch {
      return null;
    }
  };

  const handleModeChange = (m: Mode) => {
    setMode(m);
    fetchStatus();
  };

  const handleStart = async () => {
    if (status.running) return;
    try {
      const r = await fetch(`${API}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const d = await r.json();
      if (!d.success) alert("启动失败: " + (d.error || "未知错误"));
      await fetchStatus();
    } catch (e) {
      alert("请求失败");
    }
  };

  const handleStop = async () => {
    if (!status.running) return;
    try {
      const r = await fetch(`${API}/stop`, {
        method: "POST",
      });
      const d = await r.json();
      if (!d.success) alert("停止失败");
      await fetchStatus();
    } catch (e) {
      alert("请求失败");
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    setCheckResult(null);
    try {
      const r = await fetch(`${API}/check`, { method: "POST" });
      const d = await r.json();
      setCheckResult(d);
    } catch (e) {
      setCheckResult({ success: false, output: ["请求失败"] });
    }
    setChecking(false);
  };

  const handleClearLogs = () => setLogs([]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-2xl mr-2">🎫</span>
            大麦抢票控制台
          </h1>
          {/* Mode Toggle */}
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => handleModeChange("web")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                mode === "web" ? "bg-emerald-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              🌐 Web端
            </button>
            <button
              onClick={() => handleModeChange("mobile")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                mode === "mobile" ? "bg-emerald-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              📱 移动端
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Config + Controls */}
          <div className="space-y-4">
            <ConfigForm mode={mode} disabled={status.running} />
            <ControlBar
              status={status}
              checking={checking}
              onStart={handleStart}
              onStop={handleStop}
              onCheck={handleCheck}
            />
            {checkResult && (
              <div className={`rounded-lg border p-4 ${
                checkResult.success ? "border-emerald-700 bg-emerald-900/20" : "border-red-700 bg-red-900/20"
              }`}>
                <div className="font-bold mb-2 text-sm">
                  {checkResult.success ? "✅ 环境检查通过" : "❌ 环境检查未通过"}
                </div>
                {checkResult.output?.map((line, i) => (
                  <div key={i} className="text-xs font-mono text-gray-300 whitespace-pre-wrap">{line}</div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Log Viewer */}
          <LogViewer logs={logs} onClear={handleClearLogs} />
        </div>
      </main>
    </div>
  );
}
