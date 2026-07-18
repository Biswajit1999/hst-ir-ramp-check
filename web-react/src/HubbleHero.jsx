import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef, useState } from 'react';

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  return reduced;
}

function FrameTicker({ reducedMotion }) {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (reducedMotion) {
      invalidate();
      return undefined;
    }

    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') invalidate();
    }, 1000 / 24);
    return () => window.clearInterval(timer);
  }, [invalidate, reducedMotion]);

  return null;
}

function SolarPanel({ position }) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[0.12, 2.3, 0.9]} />
        <meshStandardMaterial color="#253f55" metalness={0.35} roughness={0.62} />
      </mesh>
      {[-0.74, 0, 0.74].map((y) => (
        <mesh key={y} position={[0.065, y, 0]}>
          <boxGeometry args={[0.012, 0.035, 0.86]} />
          <meshBasicMaterial color="#d69a59" />
        </mesh>
      ))}
    </group>
  );
}

function TelescopeModel({ reducedMotion }) {
  const model = useRef();

  useFrame((state, delta) => {
    if (!model.current || reducedMotion) return;
    model.current.rotation.y += delta * 0.16;
    model.current.position.y = Math.sin(state.clock.elapsedTime * 0.55) * 0.08;
  });

  return (
    <group ref={model} rotation={[-0.18, -0.55, 0.18]}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.48, 0.58, 2.25, 12]} />
        <meshStandardMaterial color="#a87451" metalness={0.72} roughness={0.32} />
      </mesh>
      <mesh position={[1.13, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.48, 0.08, 8, 20]} />
        <meshStandardMaterial color="#e2c3a1" metalness={0.7} roughness={0.25} />
      </mesh>
      <mesh position={[1.11, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <circleGeometry args={[0.4, 20]} />
        <meshStandardMaterial color="#33221c" metalness={0.2} roughness={0.72} />
      </mesh>
      <mesh position={[-1.28, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.2, 0.34, 0.44, 8]} />
        <meshStandardMaterial color="#d3b18d" metalness={0.55} roughness={0.4} />
      </mesh>
      <mesh position={[-1.53, 0, 0]}>
        <boxGeometry args={[0.36, 0.3, 0.3]} />
        <meshStandardMaterial color="#8e5b3c" metalness={0.45} roughness={0.48} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[0.26, 1.05, 1.05]} />
        <meshStandardMaterial color="#c9a784" metalness={0.5} roughness={0.42} />
      </mesh>
      <SolarPanel position={[0, 1.72, 0]} />
      <SolarPanel position={[0, -1.72, 0]} />
    </group>
  );
}

export default function HubbleHero() {
  const reducedMotion = useReducedMotion();

  return (
    <figure className="hero-visual overflow-hidden rounded-[2rem] border border-[#f0b879]/20 bg-[#120a07]/55 shadow-2xl shadow-black/25">
      <div className="h-[20rem] md:h-[23rem]" aria-label="Animated stylized Hubble-like telescope illustration">
        <Canvas
          camera={{ position: [0, 0.15, 6.4], fov: 42 }}
          dpr={[1, 1.5]}
          frameloop="demand"
          gl={{ antialias: true, powerPreference: 'low-power' }}
        >
          <color attach="background" args={['#120a07']} />
          <ambientLight intensity={1.25} />
          <directionalLight position={[4, 5, 4]} intensity={3.2} color="#ffd7a8" />
          <directionalLight position={[-3, -2, 2]} intensity={1.5} color="#8aa9c8" />
          <FrameTicker reducedMotion={reducedMotion} />
          <TelescopeModel reducedMotion={reducedMotion} />
        </Canvas>
      </div>
      <figcaption className="flex items-center gap-2 border-t border-[#f0b879]/15 px-4 py-3 text-xs text-[#caa98c]">
        <span className="h-1.5 w-1.5 rounded-full bg-[#e49a57]" aria-hidden="true" />
        Stylized illustration, not flight data
      </figcaption>
    </figure>
  );
}
