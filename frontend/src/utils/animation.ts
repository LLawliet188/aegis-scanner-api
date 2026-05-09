import type { Variants } from "framer-motion";

export const premiumEase: [number, number, number, number] = [0.16, 1, 0.3, 1];

export const revealContainer: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.09,
      delayChildren: 0.05,
    },
  },
};

export const revealItem: Variants = {
  hidden: {
    opacity: 0,
    y: 22,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.72,
      ease: premiumEase,
    },
  },
};
