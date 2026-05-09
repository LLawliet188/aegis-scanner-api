import { memo } from "react";
import { Network, ShieldAlert } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { premiumEase, revealItem } from "../../utils/animation";

type NetworkVisualizationProps = {
  isActive: boolean;
};

type NodeTone = "cyan" | "blue" | "emerald" | "amber" | "rose";

type Node = {
  id: string;
  label: string;
  x: number;
  y: number;
  radius: number;
  tone: NodeTone;
};

type Link = {
  from: string;
  to: string;
  risk: "low" | "medium" | "high";
};

const nodes: Node[] = [
  { id: "edge", label: "Edge", x: 90, y: 205, radius: 12, tone: "cyan" },
  { id: "gateway", label: "Gateway", x: 230, y: 150, radius: 15, tone: "blue" },
  { id: "api", label: "API", x: 375, y: 94, radius: 11, tone: "emerald" },
  { id: "db", label: "DB", x: 465, y: 205, radius: 13, tone: "amber" },
  { id: "admin", label: "Admin", x: 335, y: 295, radius: 12, tone: "rose" },
  { id: "sensor", label: "Sensor", x: 178, y: 312, radius: 10, tone: "cyan" },
];

const links: Link[] = [
  { from: "edge", to: "gateway", risk: "low" },
  { from: "gateway", to: "api", risk: "low" },
  { from: "api", to: "db", risk: "medium" },
  { from: "gateway", to: "admin", risk: "high" },
  { from: "edge", to: "sensor", risk: "low" },
  { from: "sensor", to: "admin", risk: "medium" },
  { from: "db", to: "admin", risk: "high" },
];

const toneColor: Record<NodeTone, string> = {
  cyan: "#00d9ff",
  blue: "#60a5fa",
  emerald: "#6ee7b7",
  amber: "#fbbf24",
  rose: "#fb7185",
};

const riskColor: Record<Link["risk"], string> = {
  low: "rgba(0,217,255,0.45)",
  medium: "rgba(251,191,36,0.42)",
  high: "rgba(251,113,133,0.5)",
};

const getNode = (id: string) => nodes.find((node) => node.id === id) ?? nodes[0];

const NetworkVisualizationComponent = ({ isActive }: NetworkVisualizationProps) => {
  const reducedMotion = useReducedMotion();
  const shouldAnimate = isActive && !reducedMotion;

  return (
    <motion.div
      className="relative overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] p-5 backdrop-blur-2xl transition hover:border-accent/45 hover:shadow-cyan-sm"
      variants={revealItem}
      whileHover={{ y: -4, transition: { duration: 0.45, ease: premiumEase } }}
    >
      <div className="relative z-10 mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
            attack surface map
          </p>
          <h3 className="mt-2 font-display text-2xl font-semibold text-primary">
            Live topology with threat hotspots
          </h3>
        </div>
        <div className="flex items-center gap-2 rounded border border-rose-300/20 bg-rose-300/10 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-rose-200">
          <ShieldAlert size={13} />
          2 high risk paths
        </div>
      </div>

      <div className="relative min-h-[22rem] overflow-hidden">
        <motion.div
          animate={shouldAnimate ? { rotate: 360 } : { rotate: 0 }}
          className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent/10 bg-[conic-gradient(from_0deg,transparent_0deg,rgba(0,217,255,0.18)_42deg,transparent_78deg)]"
          transition={{ duration: 8.5, ease: "linear", repeat: Infinity }}
        />
        <div className="absolute left-1/2 top-1/2 h-44 w-44 -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent/10" />
        <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent/5" />

        <svg
          aria-label="Animated network topology showing scan paths and threat hotspots"
          className="relative z-10 h-full min-h-[22rem] w-full"
          role="img"
          viewBox="0 0 560 390"
        >
          <defs>
            <filter id="scanner-node-glow" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur result="blur" stdDeviation="6" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {links.map((link, index) => {
            const source = getNode(link.from);
            const target = getNode(link.to);

            return (
              <motion.line
                animate={
                  shouldAnimate
                    ? { opacity: [0.28, 0.72, 0.34], pathLength: 1 }
                    : { opacity: 0.38, pathLength: 1 }
                }
                initial={{ opacity: 0, pathLength: 0 }}
                key={`${link.from}-${link.to}`}
                stroke={riskColor[link.risk]}
                strokeLinecap="round"
                strokeWidth={link.risk === "high" ? 1.8 : 1.2}
                transition={{
                  delay: 0.12 * index,
                  duration: 1.7,
                  ease: premiumEase,
                  repeat: shouldAnimate ? Infinity : 0,
                  repeatDelay: 2.8,
                }}
                x1={source.x}
                x2={target.x}
                y1={source.y}
                y2={target.y}
              />
            );
          })}

          {links.slice(0, 5).map((link, index) => {
            const source = getNode(link.from);
            const target = getNode(link.to);

            return (
              <motion.circle
                animate={
                  shouldAnimate
                    ? {
                        cx: [source.x, target.x],
                        cy: [source.y, target.y],
                        opacity: [0, 0.95, 0],
                      }
                    : { opacity: 0 }
                }
                fill={riskColor[link.risk]}
                key={`${link.from}-${link.to}-pulse`}
                r="3.4"
                transition={{
                  delay: index * 0.55,
                  duration: 2.1,
                  ease: "easeInOut",
                  repeat: Infinity,
                  repeatDelay: 1.6,
                }}
              />
            );
          })}

          {nodes.map((node, index) => (
            <g key={node.id}>
              <motion.circle
                animate={
                  shouldAnimate
                    ? {
                        opacity: [0.14, 0.32, 0.14],
                        r: [node.radius + 5, node.radius + 16, node.radius + 5],
                      }
                    : { opacity: 0.18, r: node.radius + 9 }
                }
                cx={node.x}
                cy={node.y}
                fill={toneColor[node.tone]}
                transition={{
                  delay: index * 0.18,
                  duration: node.tone === "rose" ? 1.8 : 2.7,
                  ease: "easeInOut",
                  repeat: Infinity,
                }}
              />
              <motion.circle
                animate={
                  shouldAnimate
                    ? { scale: [1, 1.08, 1], opacity: [0.88, 1, 0.9] }
                    : { scale: 1, opacity: 0.92 }
                }
                cx={node.x}
                cy={node.y}
                fill="#020617"
                filter="url(#scanner-node-glow)"
                r={node.radius}
                stroke={toneColor[node.tone]}
                strokeWidth="2"
                transition={{
                  delay: index * 0.12,
                  duration: 2.4,
                  ease: "easeInOut",
                  repeat: Infinity,
                }}
              />
              <text
                className="fill-slate-300 font-mono text-[10px] uppercase"
                textAnchor="middle"
                x={node.x}
                y={node.y + node.radius + 22}
              >
                {node.label}
              </text>
            </g>
          ))}
        </svg>
      </div>

      <div className="relative z-10 mt-5 grid gap-3 sm:grid-cols-3">
        {[
          ["Entry Vector", "Exposed SSH"],
          ["Lateral Risk", "Admin subnet"],
          ["Remediation", "Patch + isolate"],
        ].map(([label, value]) => (
          <div className="border-t border-white/10 pt-3" key={label}>
            <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted">
              {label}
            </p>
            <p className="mt-1 font-body text-sm text-primary">{value}</p>
          </div>
        ))}
      </div>

      <Network
        aria-hidden="true"
        className="absolute -right-8 -top-8 text-accent/10"
        size={170}
        strokeWidth={1}
      />
    </motion.div>
  );
};

export const NetworkVisualization = memo(NetworkVisualizationComponent);
