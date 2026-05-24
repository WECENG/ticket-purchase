import type { StatusData } from "../types";

interface Props {
  status: StatusData;
  checking: boolean;
  onStart: () => void;
  onStop: () => void;
  onCheck: () => void;
}

export default function ControlBar({ status, checking, onStart, onStop, onCheck }: Props) {
  const running = status.running;
  const elapsed = status.elapsed > 0 ? Math.floor(status.elapsed) : 0;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">🎮 控制</h2>

      <div className="flex items-center gap-4">
        {/* Status indicator */}
        <div className="flex items-center gap-2 flex-1">
          <div className={`w-3 h-3 rounded-full ${running ? "bg-emerald-500 animate-pulse" : "bg-gray-600"}`} />
          <span className="text-sm font-medium">
            {running ? (
              <span className="text-emerald-400">
                运行中 {elapsed > 0 && `(${elapsed}s)`}
                {status.mode && ` - ${status.mode === "web" ? "Web端" : "移动端"}`}
              </span>
            ) : (
              <span className="text-gray-500">空闲</span>
            )}
          </span>
        </div>

        {/* Buttons */}
        {!running ? (
          <button
            onClick={onStart}
            className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium text-sm transition disabled:opacity-40"
          >
            ▶ 开始
          </button>
        ) : (
          <button
            onClick={onStop}
            className="px-6 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium text-sm transition animate-pulse"
          >
            ⏹ 停止
          </button>
        )}

        <button
          onClick={onCheck}
          disabled={running || checking}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg text-sm transition disabled:opacity-40"
        >
          {checking ? "⏳ 检查中..." : "🔍 环境检查"}
        </button>
      </div>
    </div>
  );
}
