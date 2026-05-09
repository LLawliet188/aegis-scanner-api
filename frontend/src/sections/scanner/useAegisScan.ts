import { useCallback, useEffect, useRef, useState } from "react";
import {
  createScanSocket,
  startScan,
  type ScanEvent,
  type ScanResult,
  type ScanStatus,
  type ScanSummary,
  type Vulnerability,
} from "../../services/aegisApi";

export type LogLevel = "INFO" | "OPEN" | "WARNING" | "ALERT" | "SUCCESS";

export type ScanLog = {
  level: LogLevel;
  message: string;
};

type ScanState = {
  status: ScanStatus | "idle";
  scanId: string | null;
  target: string;
  logs: ScanLog[];
  progress: number;
  result: ScanResult | null;
  summary: ScanSummary;
  vulnerabilities: Vulnerability[];
  error: string | null;
  isConnected: boolean;
};

const initialState: ScanState = {
  status: "idle",
  scanId: null,
  target: "127.0.0.1",
  logs: [{ level: "INFO", message: "Ready for authorized localhost scan." }],
  progress: 0,
  result: null,
  summary: {},
  vulnerabilities: [],
  error: null,
  isConnected: false,
};

const levelForEvent = (event: ScanEvent): LogLevel => {
  if (event.type === "completed") return "SUCCESS";
  if (event.type === "error") return "ALERT";
  if (event.type === "finding") {
    const severity = event.data?.severity;
    return severity === "critical" || severity === "high" ? "ALERT" : "WARNING";
  }
  if (event.message.toLowerCase().includes("open")) return "OPEN";
  return "INFO";
};

const parseSocketEvent = (message: MessageEvent<string>): ScanEvent => {
  return JSON.parse(message.data) as ScanEvent;
};

export const useAegisScan = () => {
  const [state, setState] = useState<ScanState>(initialState);
  const socketRef = useRef<WebSocket | null>(null);

  const closeSocket = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
  }, []);

  useEffect(() => closeSocket, [closeSocket]);

  const launchScan = useCallback(
    async (target: string) => {
      closeSocket();
      const normalizedTarget = target.trim() || "127.0.0.1";
      setState({
        ...initialState,
        status: "queued",
        target: normalizedTarget,
        logs: [{ level: "INFO", message: `Requesting scan for ${normalizedTarget}` }],
      });

      try {
        const accepted = await startScan(normalizedTarget);
        setState((current) => ({
          ...current,
          scanId: accepted.scan_id,
          status: accepted.status,
          target: accepted.target,
          logs: [...current.logs, { level: "INFO", message: accepted.message }],
        }));

        const socket = createScanSocket(accepted.scan_id);
        socketRef.current = socket;

        socket.onopen = () => {
          setState((current) => ({ ...current, isConnected: true }));
        };

        socket.onmessage = (message) => {
          const event = parseSocketEvent(message);
          const log = { level: levelForEvent(event), message: event.message };

          setState((current) => {
            const eventResult = event.data?.result;
            const eventSummary = eventResult?.summary ?? event.data?.summary ?? current.summary;
            const finding =
              event.type === "finding" && event.data?.title
                ? ({
                    id: String(event.data.id ?? event.data.title),
                    title: event.data.title,
                    severity: event.data.severity ?? "medium",
                    description: String(event.data.description ?? event.message),
                    host: String(event.data.host ?? accepted.target),
                    port: typeof event.data.port === "number" ? event.data.port : null,
                    service: typeof event.data.service === "string" ? event.data.service : null,
                    evidence: typeof event.data.evidence === "string" ? event.data.evidence : null,
                  } satisfies Vulnerability)
                : null;

            return {
              ...current,
              status:
                event.type === "completed"
                  ? "completed"
                  : event.type === "error"
                    ? "failed"
                    : current.status === "queued"
                      ? "running"
                      : current.status,
              logs: [...current.logs, log].slice(-40),
              progress: event.progress ?? current.progress,
              result: eventResult ?? current.result,
              summary: eventSummary,
              vulnerabilities: eventResult?.vulnerabilities ?? (finding ? [...current.vulnerabilities, finding] : current.vulnerabilities),
              error: event.type === "error" ? event.message : current.error,
            };
          });
        };

        socket.onerror = () => {
          setState((current) => ({
            ...current,
            error: "WebSocket connection failed.",
            logs: [...current.logs, { level: "ALERT", message: "WebSocket connection failed." }],
            status: "failed",
            isConnected: false,
          }));
        };

        socket.onclose = () => {
          setState((current) => ({ ...current, isConnected: false }));
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Scan request failed.";
        setState((current) => ({
          ...current,
          error: message,
          logs: [...current.logs, { level: "ALERT", message }],
          status: "failed",
        }));
      }
    },
    [closeSocket],
  );

  return {
    launchScan,
    state,
  };
};

