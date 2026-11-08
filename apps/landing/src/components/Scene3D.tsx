import { Float, MeshDistortMaterial, Sparkles } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useRef, useState } from "react";
import type { Mesh } from "three";

// A tasteful, cheap 3D hero — one low-poly distorted blob (stands in for
// "the model thinking/generating") plus a thin sparkle field for depth.
// Kept deliberately light (low geometry detail, no postprocessing) so it
// doesn't tank first paint on a phone, and the whole canvas is skipped
// entirely for prefers-reduced-motion (see LandingScene below).
function Blob() {
  const mesh = useRef<Mesh>(null);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });

  useFrame((state, delta) => {
    if (!mesh.current) return;
    mesh.current.rotation.x += delta * 0.08;
    mesh.current.rotation.y += delta * 0.12;
    // Gentle parallax toward the pointer, not a hard snap.
    mesh.current.rotation.x += (pointer.y * 0.15 - mesh.current.rotation.x * 0.01) * 0.02;
    mesh.current.rotation.y += (pointer.x * 0.15 - mesh.current.rotation.y * 0.01) * 0.02;
    void state;
  });

  return (
    <Float speed={1.4} rotationIntensity={0.3} floatIntensity={0.6}>
      <mesh
        ref={mesh}
        onPointerMove={(e) => setPointer({ x: e.pointer.x, y: e.pointer.y })}
        scale={1.6}
      >
        <icosahedronGeometry args={[1, 4]} />
        <MeshDistortMaterial
          color="#7c3aed"
          attach="material"
          distort={0.45}
          speed={1.6}
          roughness={0.15}
          metalness={0.4}
          emissive="#4c1d95"
          emissiveIntensity={0.35}
        />
      </mesh>
    </Float>
  );
}

export function Scene3D({ className }: { className?: string }) {
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  if (prefersReducedMotion) {
    // Static glow stand-in — same visual weight, zero animation.
    return (
      <div
        className={className}
        aria-hidden
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(124,58,237,0.55), transparent 65%)",
        }}
      />
    );
  }

  return (
    <div className={className} aria-hidden>
      <Canvas camera={{ position: [0, 0, 4.5], fov: 45 }} dpr={[1, 1.5]}>
        <Suspense fallback={null}>
          <ambientLight intensity={0.6} />
          <pointLight position={[3, 3, 3]} intensity={60} color="#a78bfa" />
          <pointLight position={[-3, -2, -2]} intensity={25} color="#4c1d95" />
          <Blob />
          <Sparkles count={60} scale={6} size={2} speed={0.3} color="#a78bfa" opacity={0.5} />
        </Suspense>
      </Canvas>
    </div>
  );
}
