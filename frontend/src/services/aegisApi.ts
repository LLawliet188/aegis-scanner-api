const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? API_BASE_URL.replace(/^http/, "ws");

export type ScanStatus = "queued" | "running" | "completed" | "failed";

export type ScanSummary = {
  hosts_total?: number;
  hosts_up?: number;
  open_ports?: number;
  vulnerabilities?: number;
  critical?: number;
  high?: number;
  medium?: number;
  low?: number;
  info?: number;
};

export type Vulnerability = {
  id: string;
  title: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  description: string;
  host: string;
  port?: number | null;
  service?: string | null;
  evidence?: string | null;
};

export type ScanResult = {
  scan_id: string;
  target: string;
  status: ScanStatus;
  command_profile: string;
  summary: ScanSummary;
  vulnerabilities: Vulnerability[];
};

export type ScanAcceptedResponse = {
  scan_id: string;
  status: ScanStatus;
  target: string;
  websocket_url: string;
  message: string;
};

export type ScanEvent = {
  type: "queued" | "log" | "progress" | "finding" | "completed" | "error";
  scan_id: string;
  timestamp?: string;
  message: string;
  progress?: number | null;
  data?: {
    result?: ScanResult;
    summary?: ScanSummary;
    severity?: Vulnerability["severity"];
    title?: string;
    host?: string;
    port?: number | null;
    service?: string | null;
    [key: string]: unknown;
  } | null;
};

export const startScan = async (target: string): Promise<ScanAcceptedResponse> => {
  const response = await fetch(`${API_BASE_URL}/scan`, {
    body: JSON.stringify({
      target,
      options: {
        top_ports: 100,
        service_detection: true,
        os_detection: false,
        vuln_scripts: false,
        intensity: "standard",
      },
    }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Scan request failed with ${response.status}`);
  }

  return response.json() as Promise<ScanAcceptedResponse>;
};

export const createScanSocket = (scanId: string) => {
  return new WebSocket(`${WS_BASE_URL}/ws/scan/${scanId}`);
};

