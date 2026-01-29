import { useEffect, useRef } from 'react';
import * as THREE from 'three';

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`;

// Subtle nebula background - no distracting moving elements
const fragmentShader = `
  uniform float uTime;
  uniform vec2 uResolution;
  uniform float uMemoryCount;
  varying vec2 vUv;

  // Noise functions
  vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
             dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return fract(sin(p) * 43758.5453);
  }

  float noise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float n = mix(
      mix(
        mix(dot(hash3(i + vec3(0.0, 0.0, 0.0)), f - vec3(0.0, 0.0, 0.0)),
            dot(hash3(i + vec3(1.0, 0.0, 0.0)), f - vec3(1.0, 0.0, 0.0)), f.x),
        mix(dot(hash3(i + vec3(0.0, 1.0, 0.0)), f - vec3(0.0, 1.0, 0.0)),
            dot(hash3(i + vec3(1.0, 1.0, 0.0)), f - vec3(1.0, 1.0, 0.0)), f.x),
        f.y
      ),
      mix(
        mix(dot(hash3(i + vec3(0.0, 0.0, 1.0)), f - vec3(0.0, 0.0, 1.0)),
            dot(hash3(i + vec3(1.0, 0.0, 1.0)), f - vec3(1.0, 0.0, 1.0)), f.x),
        mix(dot(hash3(i + vec3(0.0, 1.0, 1.0)), f - vec3(0.0, 1.0, 1.0)),
            dot(hash3(i + vec3(1.0, 1.0, 1.0)), f - vec3(1.0, 1.0, 1.0)), f.x),
        f.y
      ),
      f.z
    );
    return n;
  }

  float fbm(vec3 p) {
    float v = 0.0;
    float a = 0.5;
    vec3 shift = vec3(100.0);
    for (int i = 0; i < 4; i++) {
      v += a * noise(p);
      p = p * 2.0 + shift;
      a *= 0.5;
    }
    return v;
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / uResolution.xy;

    // Base color - deep obsidian
    vec3 col = vec3(0.02, 0.02, 0.025);

    // Very slow, subtle nebula movement
    float slowTime = uTime * 0.02;

    // Layer 1: Deep nebula base
    float nebula1 = fbm(vec3(uv * 2.0, slowTime * 0.5));
    vec3 emeraldDeep = vec3(0.05, 0.15, 0.1);
    col += emeraldDeep * nebula1 * 0.3;

    // Layer 2: Lighter accent in corner
    float nebula2 = fbm(vec3(uv * 3.0 + 100.0, slowTime * 0.3));
    vec3 emeraldLight = vec3(0.1, 0.25, 0.15);

    // Gradient from bottom-left corner
    float cornerGradient = smoothstep(0.0, 1.5, length(uv - vec2(0.0, 0.0)));
    col += emeraldLight * nebula2 * (1.0 - cornerGradient) * 0.2;

    // Layer 3: Very subtle top-right glow
    float topRightGlow = smoothstep(1.5, 0.5, length(uv - vec2(1.0, 1.0)));
    col += vec3(0.03, 0.08, 0.05) * topRightGlow * 0.15;

    // Subtle vignette
    float vignette = 1.0 - length((uv - 0.5) * 1.2);
    vignette = smoothstep(0.0, 0.7, vignette);
    col *= 0.7 + vignette * 0.3;

    // Very faint particle sparkle (static, not moving)
    float sparkle = noise(vec3(uv * 50.0, 0.0));
    sparkle = pow(sparkle, 8.0);
    col += vec3(0.2, 0.4, 0.3) * sparkle * 0.02;

    gl_FragColor = vec4(col, 1.0);
  }
`;

interface ThreeBackgroundProps {
  memoryCount?: number;
}

export function ThreeBackground({ memoryCount = 0 }: ThreeBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const frameIdRef = useRef<number>(0);

  useEffect(() => {
    if (!containerRef.current) return;

    // Setup
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Orthographic camera
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: 'low-power'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Shader material
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uResolution: { value: new THREE.Vector2(width, height) },
        uMemoryCount: { value: memoryCount }
      }
    });
    materialRef.current = material;

    // Fullscreen plane
    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Animation loop - slower update rate for subtle background
    let lastTime = 0;
    const animate = (time: number) => {
      frameIdRef.current = requestAnimationFrame(animate);

      // Throttle to ~30fps for background
      if (time - lastTime < 33) return;
      lastTime = time;

      if (materialRef.current) {
        materialRef.current.uniforms.uTime.value = time * 0.001;
      }

      renderer.render(scene, camera);
    };
    animate(0);

    // Resize handler
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !materialRef.current) return;

      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;

      rendererRef.current.setSize(w, h);
      materialRef.current.uniforms.uResolution.value.set(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(frameIdRef.current);

      if (rendererRef.current && containerRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement);
      }

      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  // Update memory count uniform
  useEffect(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.uMemoryCount.value = memoryCount;
    }
  }, [memoryCount]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 z-0"
      style={{ background: '#050505' }}
    />
  );
}

export default ThreeBackground;
