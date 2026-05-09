import { memo } from "react";
import { motion, useReducedMotion } from "framer-motion";

type AnimatedGridBackgroundProps = {
  active: boolean;
};

const particles = [
  { x: 8, y: 22, delay: 0.2, drift: 18 },
  { x: 18, y: 72, delay: 1.6, drift: -12 },
  { x: 29, y: 36, delay: 0.8, drift: 14 },
  { x: 42, y: 82, delay: 2.2, drift: -18 },
  { x: 58, y: 24, delay: 1.1, drift: 16 },
  { x: 68, y: 66, delay: 2.8, drift: -14 },
  { x: 79, y: 38, delay: 0.5, drift: 12 },
  { x: 90, y: 74, delay: 1.9, drift: -16 },
  { x: 94, y: 18, delay: 3.2, drift: 10 },
];

const AnimatedGridBackgroundComponent = ({ active }: AnimatedGridBackgroundProps) => {
  const reducedMotion = useReducedMotion();
  const shouldAnimate = active && !reducedMotion;

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[#020617]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(0,217,255,0.18),transparent_34rem),radial-gradient(circle_at_85%_42%,rgba(59,130,246,0.12),transparent_28rem),radial-gradient(circle_at_15%_88%,rgba(16,185,129,0.08),transparent_24rem)]" />
      <div className="absolute inset-0 opacity-[0.16] [background-image:linear-gradient(rgba(125,211,252,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(125,211,252,0.08)_1px,transparent_1px)] [background-size:4rem_4rem]" />
      <div className="absolute inset-0 opacity-[0.08] [background-image:linear-gradient(120deg,transparent_0%,rgba(0,217,255,0.32)_42%,transparent_68%)] [background-size:28rem_28rem]" />

      <motion.div
        animate={shouldAnimate ? { y: ["-20%", "115%"], opacity: [0, 0.55, 0] } : false}
        className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-transparent via-accent/20 to-transparent blur-sm"
        transition={{ duration: 6.5, ease: "linear", repeat: Infinity, repeatDelay: 1.4 }}
      />

      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.04),transparent_1px)] [background-size:100%_3px] opacity-[0.06]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle,rgba(255,255,255,0.18)_1px,transparent_1px)] [background-size:18px_18px] opacity-[0.035]" />

      {particles.map((particle) => (
        <motion.span
          animate={
            shouldAnimate
              ? {
                  opacity: [0.12, 0.85, 0.18],
                  x: [0, particle.drift, 0],
                  y: [0, particle.drift * -0.6, 0],
                }
              : { opacity: 0.24 }
          }
          className="absolute h-1 w-1 rounded-full bg-accent shadow-[0_0_14px_rgba(0,217,255,0.85)]"
          key={`${particle.x}-${particle.y}`}
          style={{ left: `${particle.x}%`, top: `${particle.y}%` }}
          transition={{
            delay: particle.delay,
            duration: 7.5,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        />
      ))}

      <div className="absolute inset-0 bg-gradient-to-b from-[#020617]/0 via-[#020617]/18 to-[#020617]/82" />
    </div>
  );
};

export const AnimatedGridBackground = memo(AnimatedGridBackgroundComponent);
