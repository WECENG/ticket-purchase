import { useEffect, useRef } from "react";
import type { LogEntry } from "../types";

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

export default function LogViewer({ logs, onClear }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const formatTime = (t: number) => {
    const d = new Date(t * 1000);
    return d.toLocaleTimeString("zh-CN", { hour12: false });
  };

  const getLineColor = (type: string) => {
    switch (type) {
      case "error": return "text-red-400";
      case "exit": return "text-yellow-400";
      case "status": return "text-blue-400";
      default: return "text-gray-300";
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 flex flex-col h-[600px]">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">📡 实时日志</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{logs.length} 条</span>
          <button
            onClick={onClear}
            className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
          >
            清空
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed space-y-0.5">
        {logs.length === 0 && (
          <div className="text-gray-600 text-center mt-8">
            等待日志输出...
          </div>
        )}
        {logs.map((entry, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-gray-600 shrink-0">{formatTime(entry.time)}</span>
            <span className={getLineColor(entry.type)}>{entry.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
