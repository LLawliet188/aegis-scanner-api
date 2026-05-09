import { memo, useMemo } from "react";
import { Cpu, LockKeyhole, Terminal } from "lucide-react";
import { motion } from "framer-motion";
import { premiumEase, revealItem } from "../../utils/animation";
import type { LogLevel, ScanLog } from "./useAegisScan";

type ScannerTerminalProps = {
  isActive: boolean;
  isConnected: boolean;
  logs: ScanLog[];
  progress: number;
  scanId: string | null;
  status: "idle" | "queued" | "running" | "completed" | "failed";
  target: string;
};

const levelStyles: Record<LogLevel, string> = {
  INFO: "text-sky-200",
  OPEN: "text-emerald-300",
  WARNING: "text-amber-200",
  ALERT: "text-rose-300",
  SUCCESS: "text-accent",
};

const ScannerTerminalComponent = ({
  isActive,
  isConnected,
  logs,
  progress,
  scanId,
  status,
  target,
}: ScannerTerminalProps) => {
  const visibleLogs = useMemo(() => logs.slice(-9), [logs]);
  const statusLabel =
    status === "completed"
      ? "Report Ready"
      : status === "failed"
        ? "Scan Failed"
        : status === "idle"
          ? "Ready"
          : "Scanning";
  const telemetry = [
    { label: "Target", value: target },
    { label: "Mode", value: "Safe Nmap" },
    { label: "Stream", value: isConnected ? "Connected" : scanId ? "Closed" : "Idle" },
  ];

  return (
    <motion.div
      className="group relative overflow-hidden rounded-lg border border-white/10 bg-[#030712]/88 shadow-2xl shadow-cyan-950/40 backdrop-blur-2xl transition hover:border-accent/45"
      id="scanner-terminal"
      variants={revealItem}
      whileHover={{ y: -5, transition: { duration: 0.45, ease: premiumEase } }}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/70 to-transparent opacity-70" />
      <motion.div
        animate={isActive ? { opacity: [0.08, 0.16, 0.08] } : { opacity: 0.08 }}
        className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(0,217,255,0.09)_50%,transparent_100%)] [background-size:100%_6px]"
        transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative border-b border-white/10 bg-white/[0.035] px-4 py-4 sm:px-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex gap-2" aria-hidden="true">
              <span className="h-3 w-3 rounded-full bg-[#FF5F57]" />
              <span className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
              <span className="h-3 w-3 rounded-full bg-[#28C840]" />
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                deep-scan://scanner
              </p>
              <p className="mt-1 font-body text-xs text-secondary">
                live infrastructure analysis
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded border border-accent/20 bg-accent/10 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-accent">
            <Cpu size={13} />
            {statusLabel}
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {telemetry.map((item) => (
            <div
              className="rounded-md border border-white/10 bg-[#020617]/60 px-3 py-2"
              key={item.label}
            >
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted">
                {item.label}
              </p>
              <p className="mt-1 truncate font-mono text-[11px] text-primary">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="relative px-4 py-5 sm:px-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">
            <Terminal className="text-accent" size={14} />
            scan stream
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">
            <LockKeyhole className="text-emerald-300" size={13} />
            sandboxed
          </div>
        </div>

        <div
          aria-label="Live network vulnerability scanner log"
          aria-live="polite"
          className="terminal-scroll min-h-[19rem] overflow-hidden font-mono text-xs leading-6 text-secondary sm:text-sm"
          role="log"
        >
          {visibleLogs.map((log, index) => (
            <p className="flex gap-3" key={`${log.level}-${log.message}-${index}`}>
              <span className={levelStyles[log.level]}>[{log.level}]</span>
              <span className="text-secondary">{log.message}</span>
            </p>
          ))}
          {status === "running" || status === "queued" ? (
            <p className="flex gap-3 text-primary">
              <span className="text-accent">[LIVE]</span>
              <span>
                awaiting scanner event
                <span className="terminal-cursor ml-1 inline-block h-4 w-2 translate-y-0.5 bg-accent shadow-[0_0_16px_rgba(0,217,255,0.75)]" />
              </span>
            </p>
          ) : null}
        </div>

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-secondary">
            <span>scan progress</span>
            <span className="text-accent">{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full border border-white/10 bg-white/[0.04]">
            <motion.div
              animate={{ width: `${progress}%` }}
              className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-accent to-emerald-300 shadow-[0_0_22px_rgba(0,217,255,0.65)]"
              transition={{ duration: 0.38, ease: premiumEase }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export const ScannerTerminal = memo(ScannerTerminalComponent);
