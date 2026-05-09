import { memo, useEffect, useMemo, useState, type ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { Activity, AlertTriangle, Gauge, Radio, Server } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { premiumEase, revealItem } from "../../utils/animation";
import type { ScanSummary } from "../../services/aegisApi";

type Metric = {
  label: string;
  value: number;
  detail: string;
  icon: ComponentType<LucideProps>;
  decimals?: number;
  formatter?: (value: number) => string;
};

type ThreatMetricsProps = {
  isActive: boolean;
  summary: ScanSummary;
};

const value = (summary: ScanSummary, key: keyof ScanSummary) => summary[key] ?? 0;

const buildMetrics = (summary: ScanSummary): Metric[] => {
  const weightedScore = Math.min(
    100,
    value(summary, "critical") * 25 +
      value(summary, "high") * 15 +
      value(summary, "medium") * 8 +
      value(summary, "low") * 3 +
      value(summary, "info"),
  );

  return [
    {
      label: "Open Ports Detected",
      value: value(summary, "open_ports"),
      detail: "Live count from backend scan result",
      icon: Server,
    },
    {
      label: "Findings",
      value: value(summary, "vulnerabilities"),
      detail: "Heuristic and Nmap script findings",
      icon: AlertTriangle,
    },
    {
      label: "Threat Score",
      value: weightedScore,
      detail: "Weighted by severity and exposure",
      icon: Gauge,
      formatter: (metricValue) => `${Math.round(metricValue)}/100`,
    },
    {
      label: "Hosts Up",
      value: value(summary, "hosts_up"),
      detail: "Reachable hosts in accepted scope",
      icon: Activity,
    },
    {
      label: "Services Sampled",
      value: value(summary, "open_ports"),
      detail: "Services available for enrichment",
      icon: Radio,
    },
  ];
};

const formatMetricValue = (metric: Metric, metricValue: number) => {
  if (metric.formatter) return metric.formatter(metricValue);
  return metricValue.toFixed(metric.decimals ?? 0);
};

const AnimatedMetricValue = memo(({ metric, isActive }: { metric: Metric; isActive: boolean }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (!isActive) return;

    if (reducedMotion) {
      const timeoutId = window.setTimeout(() => setDisplayValue(metric.value), 0);
      return () => window.clearTimeout(timeoutId);
    }

    const start = Date.now();
    const duration = 900;

    const tick = () => {
      const progress = Math.min((Date.now() - start) / duration, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(metric.value * easedProgress);
    };

    tick();
    const intervalId = window.setInterval(tick, 32);
    const completionId = window.setTimeout(() => {
      window.clearInterval(intervalId);
      setDisplayValue(metric.value);
    }, duration + 48);

    return () => {
      window.clearInterval(intervalId);
      window.clearTimeout(completionId);
    };
  }, [isActive, metric.value, reducedMotion]);

  return <>{formatMetricValue(metric, displayValue)}</>;
});

const ThreatMetricsComponent = ({ isActive, summary }: ThreatMetricsProps) => {
  const metrics = useMemo(() => buildMetrics(summary), [summary]);

  return (
    <motion.div
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: 0.06,
          },
        },
      }}
    >
      {metrics.map((metric) => {
        const Icon = metric.icon;

        return (
          <motion.article
            className="group relative overflow-hidden rounded-lg border border-white/10 bg-white/[0.045] p-4 backdrop-blur-2xl transition hover:border-accent/60 hover:bg-white/[0.065] hover:shadow-cyan-sm sm:p-5"
            key={metric.label}
            variants={revealItem}
            whileHover={{
              y: -6,
              transition: { duration: 0.42, ease: premiumEase },
            }}
          >
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/0 to-transparent transition group-hover:via-accent/80" />
            <div className="mb-5 flex items-center justify-between gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-md border border-white/10 bg-[#020617]/70 text-accent transition group-hover:border-accent/50">
                <Icon size={17} />
              </div>
              <motion.span
                animate={isActive ? { opacity: [0.35, 1, 0.35] } : { opacity: 0.35 }}
                className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.85)]"
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              />
            </div>
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">
              {metric.label}
            </p>
            <p className="mt-2 font-display text-2xl font-semibold tracking-normal text-primary sm:text-3xl">
              <AnimatedMetricValue isActive={isActive} metric={metric} />
            </p>
            <p className="mt-3 min-h-10 font-body text-xs leading-5 text-secondary">
              {metric.detail}
            </p>
          </motion.article>
        );
      })}
    </motion.div>
  );
};

export const ThreatMetrics = memo(ThreatMetricsComponent);
