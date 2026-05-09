import { memo, useEffect, useRef } from "react";
import { Mesh, Program, Renderer, Triangle, Vec2 } from "ogl";

type RaysOrigin =
  | "top-left"
  | "top-center"
  | "top-right"
  | "center"
  | "bottom-left"
  | "bottom-center"
  | "bottom-right";

type LightRaysProps = {
  raysOrigin?: RaysOrigin;
  raysColor?: string;
  raysSpeed?: number;
  lightSpread?: number;
  rayLength?: number;
  followMouse?: boolean;
  mouseInfluence?: number;
  noiseAmount?: number;
  distortion?: number;
  className?: string;
};

const originMap: Record<RaysOrigin, [number, number]> = {
  "top-left": [0, 1],
  "top-center": [0.5, 1],
  "top-right": [1, 1],
  center: [0.5, 0.5],
  "bottom-left": [0, 0],
  "bottom-center": [0.5, 0],
  "bottom-right": [1, 0],
};

const vertex = `
attribute vec2 position;
attribute vec2 uv;
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const fragment = `
precision highp float;

uniform vec2 uResolution;
uniform vec2 uMouse;
uniform vec2 uOrigin;
uniform vec3 uColor;
uniform float uTime;
uniform float uSpeed;
uniform float uSpread;
uniform float uRayLength;
uniform float uFollowMouse;
uniform float uMouseInfluence;
uniform float uNoiseAmount;
uniform float uDistortion;

varying vec2 vUv;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution.xy;
  vec2 mouseOrigin = mix(uOrigin, uMouse, uFollowMouse * uMouseInfluence);
  float aspect = uResolution.x / uResolution.y;

  float n = noise(uv * 6.0 + uTime * 0.05);
  uv += (n - 0.5) * uDistortion;

  vec2 dir = uv - mouseOrigin;
  dir.x *= aspect;

  float dist = length(dir);
  float angle = atan(dir.x, -dir.y);
  float cone = smoothstep(uSpread, 0.0, abs(angle));
  float falloff = exp(-dist * (1.85 / max(uRayLength, 0.001)));
  float beamNoise = noise(vec2(angle * 4.0, dist * 7.0 - uTime * uSpeed));
  float beams = pow(abs(sin(angle * 18.0 + beamNoise * 4.0 + uTime * uSpeed)), 5.0);
  float softCore = smoothstep(0.9, 0.0, dist);
  float intensity = cone * falloff * (0.22 + beams * 0.78) * (0.72 + n * uNoiseAmount * 8.0);
  intensity += softCore * 0.035;

  vec3 color = uColor * intensity;
  gl_FragColor = vec4(color, intensity * 0.58);
}
`;

const hexToRgb = (hex: string): [number, number, number] => {
  const sanitized = hex.replace("#", "");
  const value = Number.parseInt(sanitized, 16);
  return [
    ((value >> 16) & 255) / 255,
    ((value >> 8) & 255) / 255,
    (value & 255) / 255,
  ];
};

const LightRaysComponent = ({
  raysOrigin = "top-center",
  raysColor = "#00d9ff",
  raysSpeed = 1.2,
  lightSpread = 1.1,
  rayLength = 1.8,
  followMouse = true,
  mouseInfluence = 0.18,
  noiseAmount = 0.025,
  distortion = 0.06,
  className = "",
}: LightRaysProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new Renderer({
      alpha: true,
      antialias: true,
      dpr: Math.min(window.devicePixelRatio, 2),
    });

    const gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);
    container.appendChild(gl.canvas);
    gl.canvas.className = "h-full w-full";

    const uniforms = {
      uResolution: { value: new Vec2(1, 1) },
      uMouse: { value: new Vec2(0.5, 0.92) },
      uOrigin: { value: new Vec2(...originMap[raysOrigin]) },
      uColor: { value: hexToRgb(raysColor) },
      uTime: { value: 0 },
      uSpeed: { value: raysSpeed },
      uSpread: { value: lightSpread },
      uRayLength: { value: rayLength },
      uFollowMouse: { value: followMouse ? 1 : 0 },
      uMouseInfluence: { value: mouseInfluence },
      uNoiseAmount: { value: noiseAmount },
      uDistortion: { value: distortion },
    };

    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex,
      fragment,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      uniforms,
    });
    const mesh = new Mesh(gl, { geometry, program });

    const resize = () => {
      const width = container.clientWidth || window.innerWidth;
      const height = container.clientHeight || window.innerHeight;
      renderer.setSize(width, height);
      uniforms.uResolution.value.set(width, height);
    };

    const handlePointerMove = (event: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const x = (event.clientX - rect.left) / rect.width;
      const y = 1 - (event.clientY - rect.top) / rect.height;
      uniforms.uMouse.value.set(
        Math.min(Math.max(x, 0), 1),
        Math.min(Math.max(y, 0), 1),
      );
    };

    let frameId = 0;
    const startTime = performance.now();

    const update = () => {
      uniforms.uTime.value = (performance.now() - startTime) / 1000;
      renderer.render({ scene: mesh });
      frameId = window.requestAnimationFrame(update);
    };

    resize();
    update();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", handlePointerMove, { passive: true });

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", handlePointerMove);
      mesh.geometry.remove();
      program.remove();
      gl.getExtension("WEBGL_lose_context")?.loseContext();
      gl.canvas.remove();
    };
  }, [
    distortion,
    followMouse,
    lightSpread,
    mouseInfluence,
    noiseAmount,
    rayLength,
    raysColor,
    raysOrigin,
    raysSpeed,
  ]);

  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 mix-blend-screen opacity-80 ${className}`}
      ref={containerRef}
    />
  );
};

export const LightRays = memo(LightRaysComponent);
