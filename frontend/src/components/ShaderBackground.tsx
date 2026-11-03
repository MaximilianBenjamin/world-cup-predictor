/**
 * ShaderBackground — a single fullscreen WebGL canvas running one fragment
 * shader: a slow, domain-warped navy/orange/teal flow. No libraries (~raw GL).
 * Renders at devicePixelRatio*0.5, pauses when the tab is hidden, and does not
 * mount at all under reduced-motion or on touch/no-hover devices — where the
 * existing `.aurora` CSS background stays as the fallback.
 */
import { useEffect, useRef } from "react";

const canHover =
  typeof window !== "undefined" &&
  window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;

const prefersReduced =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const VERT = `attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`;

const FRAG = `
precision mediump float;
uniform vec2  u_res;
uniform float u_time;

// cheap value-noise + fbm ----------------------------------------------------
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash(i+vec2(0,0)), hash(i+vec2(1,0)), u.x),
             mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for(int i=0;i<4;i++){ v += a*noise(p); p *= 2.0; a *= 0.5; }
  return v;
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = uv * 2.4;
  p.x *= u_res.x / u_res.y;               // aspect-correct
  float t = u_time * 0.045;

  // domain warp — noise driving the lookup of more noise -> organic flow
  vec2 q = vec2(fbm(p + vec2(0.0, t)), fbm(p + vec2(5.2, -t)));
  vec2 r = vec2(fbm(p + 1.8*q + vec2(1.7, 9.2) + 0.15*t),
                fbm(p + 1.8*q + vec2(8.3, 2.8) - 0.12*t));
  float f = fbm(p + 2.0*r);

  vec3 navy   = vec3(0.055, 0.078, 0.212);
  vec3 deep   = vec3(0.090, 0.137, 0.353);
  vec3 orange = vec3(0.945, 0.376, 0.051);
  vec3 teal   = vec3(0.314, 0.647, 0.694);

  vec3 col = mix(navy, deep, clamp(f*1.4, 0.0, 1.0));
  col = mix(col, orange, clamp(pow(r.x, 2.2) * 0.55, 0.0, 1.0));
  col = mix(col, teal,   clamp(pow(q.y, 2.6) * 0.40, 0.0, 1.0));

  // gentle top-down vignette so the header/content stays legible
  col *= 0.82 + 0.30 * (1.0 - uv.y);
  gl_FragColor = vec4(col, 1.0);
}
`;

function compile(gl: WebGLRenderingContext, type: number, src: string) {
  const s = gl.createShader(type)!;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    console.warn("shader compile failed:", gl.getShaderInfoLog(s));
    gl.deleteShader(s);
    return null;
  }
  return s;
}

export default function ShaderBackground() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", {
      antialias: false,
      alpha: false,
      depth: false,
      powerPreference: "low-power",
    });
    if (!gl) return; // no WebGL -> aurora fallback shows (canvas stays hidden)

    const vs = compile(gl, gl.VERTEX_SHADER, VERT);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return;
    const prog = gl.createProgram()!;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
    gl.useProgram(prog);

    // fullscreen triangle
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(prog, "u_res");
    const uTime = gl.getUniformLocation(prog, "u_time");
    const dpr = Math.min(window.devicePixelRatio || 1, 2) * 0.5;

    const resize = () => {
      const w = Math.max(1, Math.floor(window.innerWidth * dpr));
      const h = Math.max(1, Math.floor(window.innerHeight * dpr));
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    };
    resize();
    window.addEventListener("resize", resize);

    let raf = 0;
    let running = true;
    let elapsed = 0;
    let start = performance.now();

    const frame = () => {
      if (!running) return;
      elapsed = performance.now() - start;
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, elapsed * 0.001);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      raf = requestAnimationFrame(frame);
    };

    const onVis = () => {
      if (document.hidden) {
        running = false;
        cancelAnimationFrame(raf);
      } else if (!running) {
        running = true;
        start = performance.now() - elapsed; // resume without a time jump
        frame();
      }
    };
    document.addEventListener("visibilitychange", onVis);
    frame();

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVis);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, []);

  // Touch / reduced-motion: don't mount — the CSS .aurora background stays.
  if (prefersReduced || !canHover) return null;
  return <canvas ref={ref} className="fixed inset-0 -z-10 h-full w-full" aria-hidden />;
}
