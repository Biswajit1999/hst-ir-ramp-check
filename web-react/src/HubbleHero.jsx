import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_URL = `${import.meta.env.BASE_URL}models/Hubble-1.glb`;

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

function ModelPlaceholder() {
  return (
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[0.8, 0.035, 8, 48]} />
      <meshBasicMaterial color="#876342" transparent opacity={0.55} />
    </mesh>
  );
}

function HubbleModel({ reducedMotion }) {
  const gltf = useLoader(GLTFLoader, MODEL_URL);
  const model = useRef();
  const normalized = useMemo(() => {
    const scene = gltf.scene.clone(true);
    const bounds = new Box3().setFromObject(scene);
    const center = bounds.getCenter(new Vector3());
    const size = bounds.getSize(new Vector3());
    const scale = 4.45 / Math.max(size.x, size.y, size.z);
    return { scene, position: center.multiplyScalar(-1), scale };
  }, [gltf.scene]);

  useFrame((state, delta) => {
    if (!model.current || reducedMotion) return;
    model.current.rotation.y += delta * 0.11;
    model.current.position.y = Math.sin(state.clock.elapsedTime * 0.42) * 0.06;
  });

  return (
    <group ref={model} rotation={[0.08, -0.44, -Math.PI / 2]}>
      <group scale={normalized.scale}>
        <primitive object={normalized.scene} position={normalized.position} />
      </group>
    </group>
  );
}

useLoader.preload(GLTFLoader, MODEL_URL);

export default function HubbleHero() {
  const reducedMotion = useReducedMotion();

  return (
    <figure className="hero-visual overflow-hidden rounded-[2rem] border border-[#f0b879]/20 bg-[#120a07]/55 shadow-2xl shadow-black/25">
      <div
        className="h-[20rem] md:h-[23rem]"
        role="img"
        aria-label="Animated three-dimensional model of the Hubble Space Telescope"
      >
        <Canvas
          camera={{ position: [0, 0.15, 6.4], fov: 42 }}
          dpr={[1, 1.5]}
          frameloop="demand"
          gl={{ antialias: true, powerPreference: 'low-power' }}
        >
          <color attach="background" args={['#120a07']} />
          <ambientLight intensity={1.35} />
          <directionalLight position={[4, 5, 4]} intensity={3.4} color="#ffe2bd" />
          <directionalLight position={[-3, -2, 2]} intensity={1.8} color="#89a8c8" />
          <FrameTicker reducedMotion={reducedMotion} />
          <Suspense fallback={<ModelPlaceholder />}>
            <HubbleModel reducedMotion={reducedMotion} />
          </Suspense>
        </Canvas>
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-[#f0b879]/15 px-4 py-3 text-xs text-[#caa98c]">
        <span className="h-1.5 w-1.5 rounded-full bg-[#e49a57]" aria-hidden="true" />
        <span>Hubble Space Telescope 3D model</span>
        <span aria-hidden="true">·</span>
        <a
          className="text-[#f0c99e] underline decoration-[#f0b879]/40 underline-offset-4 hover:text-white"
          href="https://science.nasa.gov/3d-resources/"
          target="_blank"
          rel="noreferrer"
        >
          NASA 3D Resources
        </a>
        <span aria-hidden="true">·</span>
        <span>visual context, not analysis data</span>
      </figcaption>
    </figure>
  );
}
