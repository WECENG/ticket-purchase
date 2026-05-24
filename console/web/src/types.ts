// 类型定义

export type Mode = "web" | "mobile";

export interface WebConfig {
  index_url: string;
  login_url: string;
  target_url: string;
  users: string[];
  city: string;
  dates: string[];
  prices: string[];
  if_listen: boolean;
  if_commit_order: boolean;
  max_retries: number;
  fast_mode: boolean;
  page_load_delay: number;
}

export interface MobileConfig {
  server_url: string;
  keyword: string;
  users: string[];
  city: string;
  date: string;
  price: string;
  price_index: number;
  if_commit_order: boolean;
  platform_version: string;
  device_name: string;
}

export type AppConfig = WebConfig | MobileConfig;

export interface StatusData {
  running: boolean;
  mode: string;
  pid: number | null;
  startTime: number | null;
  elapsed: number;
}

export interface LogEntry {
  data?: StatusData;
  type: "log" | "error" | "exit" | "status";
  text: string;
  time: number;
  code?: number;
}
