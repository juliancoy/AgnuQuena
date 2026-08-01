import * as THREE from "three";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/loaders/STLLoader.js";

const SPEC = {
  acousticLength: 398.6945166303481,
  boreDiameter: 17.5,
  outerDiameter: 19.9,
  wall: 0.8,
  cornerRatio: 0.28,
  notch: { width: 8.0, radius: 4.8, angle: 45.0, centerX: 9.5, centerZ: 0.3, length: 15.0 },
  holes: [
    { name: "A", note: "A4", target: 440.0, z: 302.0, angle: -12.0, diameter: 7.90, width: 7.249379617961712 },
    { name: "B", note: "B4", target: 493.8833, z: 272.0, angle: 12.0, diameter: 10.30, width: 9.45172279303869 },
    { name: "C", note: "C5", target: 523.2511, z: 242.0, angle: 0.0, diameter: 7.98, width: 7.322791057130945 },
    { name: "D", note: "D5", target: 587.3295, z: 207.162838899, angle: 5.0, diameter: 8.95, width: 8.212904757057888 },
    { name: "E", note: "E5", target: 659.2551, z: 177.719458261, angle: -5.0, diameter: 9.42, width: 8.64419696217713 },
    { name: "F#", note: "F#5", target: 739.9888, z: 150.028548432, angle: 0.0, diameter: 9.37, width: 8.598314812696358 },
  ],
};

const CELL_MM = 1.0;
const CELL_M = CELL_MM / 1000;
const NX = 48;
const NY = 48;
const NZ = 424;
const Z_ORIGIN_MM = -12;
const CELL_COUNT = NX * NY * NZ;
const AIR_DENSITY = 1.204;
const SOUND_SPEED = 343;
const SOUND_SPEED2 = SOUND_SPEED ** 2;
const KINEMATIC_VISCOSITY = 1.5e-5;
const COURANT = 0.28;
const DT_SECONDS = COURANT * CELL_M / (SOUND_SPEED + 20);
const SMAGORINSKY = 0.17;
const SPONGE_RATE = 16000;

const ui = {
  gpuBadge: document.querySelector("#gpuBadge"),
  canvas: document.querySelector("#pressureCanvas"),
  productionCanvas: document.querySelector("#productionCanvas"),
  productionRevision: document.querySelector("#productionRevision"),
  productionProof: document.querySelector("#productionProof"),
  volumeStatus: document.querySelector("#volumeStatus"),
  volumeOverlayToggle: document.querySelector("#volumeOverlayToggle"),
  pressureOverlayToggle: document.querySelector("#pressureOverlayToggle"),
  note: document.querySelector("#noteSelect"),
  field: document.querySelector("#fieldSelect"),
  sliceAngle: document.querySelector("#sliceAngle"),
  sliceAngleValue: document.querySelector("#sliceAngleValue"),
  title: document.querySelector("#simulationTitle"),
  profileTitle: document.querySelector("#profileTitle"),
  target: document.querySelector("#targetMetric"),
  diameter: document.querySelector("#diameterMetric"),
  profile: document.querySelector("#profileMetric"),
  position: document.querySelector("#positionMetric"),
  profileShape: document.querySelector("#profileShape"),
  profileWidth: document.querySelector("#profileWidth"),
  toggle: document.querySelector("#toggleRun"),
  reset: document.querySelector("#resetSimulation"),
  speed: document.querySelector("#speed"),
  speedValue: document.querySelector("#speedValue"),
  jetSpeed: document.querySelector("#jetSpeed"),
  jetSpeedValue: document.querySelector("#jetSpeedValue"),
  turbulence: document.querySelector("#turbulence"),
  turbulenceValue: document.querySelector("#turbulenceValue"),
  reynolds: document.querySelector("#reynoldsMetric"),
  simTime: document.querySelector("#simTime"),
  truth: document.querySelector("#truthText"),
};

const boundaryMode = "exact";
let selectedHole = SPEC.holes[0];
let running = false;
let stepCount = 0;
let gpu = null;
let gpuWorkPending = false;
let renderDirty = true;
let fallbackMask = null;
let productionSolidMask = null;
let productionMetadata = null;
let productionPressurePlane = null;
let productionVolume = null;
let volumeSampleLayout = null;
let volumeReadPending = false;
let lastVolumeSampleAt = 0;
let pressureTextureDirty = true;

function createVolumeSampleLayout() {
  const indices = [];
  const positions = [];
  const centerX = (NX - 1) / 2;
  const centerY = (NY - 1) / 2;
  const stride = 4;
  for (let z = 0; z < NZ; z += stride) {
    const zMeters = (Z_ORIGIN_MM + (z + 0.5) * CELL_MM) / 1000;
    for (let y = 1; y < NY; y += stride) {
      const yMeters = ((y - centerY) * CELL_MM) / 1000;
      for (let x = 1; x < NX; x += stride) {
        const cell = index3(x, y, z);
        if (productionSolidMask[cell] === 1) continue;
        indices.push(cell);
        positions.push(
          ((x - centerX) * CELL_MM) / 1000,
          yMeters,
          zMeters,
        );
      }
    }
  }
  return {
    indices: new Uint32Array(indices),
    positions: new Float32Array(positions),
  };
}

async function loadProductionAssets() {
  const metadataResponse = await fetch("./assets/QuenaProductionCFD.json");
  if (!metadataResponse.ok) throw new Error("Production CFD metadata is unavailable");
  productionMetadata = await metadataResponse.json();

  const [maskResponse, assemblyResponse] = await Promise.all([
    fetch(`./assets/${productionMetadata.solver_mask.file}`),
    fetch(`./assets/${productionMetadata.assembly.file}`),
  ]);
  if (!maskResponse.ok || !assemblyResponse.ok) {
    throw new Error("Validated production CFD assets are unavailable");
  }

  const [maskBuffer, assemblyBuffer] = await Promise.all([
    maskResponse.arrayBuffer(),
    assemblyResponse.arrayBuffer(),
  ]);
  const expectedGrid = productionMetadata.solver_mask.grid;
  if (
    expectedGrid[0] !== NX
    || expectedGrid[1] !== NY
    || expectedGrid[2] !== NZ
    || maskBuffer.byteLength !== CELL_COUNT
  ) {
    throw new Error("Production STL mask does not match the CFD grid");
  }
  productionSolidMask = new Uint8Array(maskBuffer);

  const shortHash = productionMetadata.assembly.sha256.slice(0, 12);
  ui.productionRevision.textContent = `STL sha256 ${shortHash}`;
  ui.productionProof.textContent = (
    `${productionMetadata.design_id} · ${productionMetadata.assembly.faces.toLocaleString()} STL faces`
  );
  initProductionViewer(assemblyBuffer);
}

function initProductionViewer(assemblyBuffer) {
  const renderer = new THREE.WebGLRenderer({
    canvas: ui.productionCanvas,
    antialias: true,
    alpha: true,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.01, 3);
  camera.position.set(0.024, -0.07, -0.28);

  const controls = new OrbitControls(camera, ui.productionCanvas);
  controls.target.set(0.024, 0, 0);
  controls.enableDamping = true;
  controls.minDistance = 0.06;
  controls.maxDistance = 1.4;

  scene.add(new THREE.HemisphereLight(0xe8fff7, 0x04100d, 2.8));
  const key = new THREE.DirectionalLight(0xffddba, 4.0);
  key.position.set(-0.25, -0.5, -0.45);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x63e2b2, 3.0);
  rim.position.set(0.35, 0.25, 0.5);
  scene.add(rim);

  const geometry = new STLLoader().parse(assemblyBuffer);
  geometry.computeVertexNormals();
  geometry.scale(0.001, 0.001, 0.001);
  const assemblyGroup = new THREE.Group();
  assemblyGroup.rotation.y = Math.PI / 2;
  assemblyGroup.position.x = -0.20235;
  scene.add(assemblyGroup);
  const fluteMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xa9d6c4,
    roughness: 0.28,
    metalness: 0.02,
    clearcoat: 0.42,
    clearcoatRoughness: 0.32,
  });
  const mesh = new THREE.Mesh(geometry, fluteMaterial);
  mesh.renderOrder = 2;
  assemblyGroup.add(mesh);

  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry, 24),
    new THREE.LineBasicMaterial({ color: 0x09251f, transparent: true, opacity: 0.24 }),
  );
  edges.renderOrder = 3;
  assemblyGroup.add(edges);

  const pressureTexture = new THREE.CanvasTexture(ui.canvas);
  pressureTexture.colorSpace = THREE.SRGBColorSpace;
  pressureTexture.minFilter = THREE.LinearFilter;
  pressureTexture.magFilter = THREE.LinearFilter;
  const planeGeometry = new THREE.BufferGeometry();
  planeGeometry.setAttribute("position", new THREE.Float32BufferAttribute([
    -0.024, 0, -0.012,
     0.024, 0, -0.012,
     0.024, 0,  0.412,
    -0.024, 0,  0.412,
  ], 3));
  planeGeometry.setAttribute("uv", new THREE.Float32BufferAttribute([
    0, 1,
    0, 0,
    1, 0,
    1, 1,
  ], 2));
  planeGeometry.setIndex([0, 1, 2, 0, 2, 3]);
  productionPressurePlane = new THREE.Mesh(
    planeGeometry,
    new THREE.MeshBasicMaterial({
      map: pressureTexture,
      transparent: true,
      opacity: 0.92,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  productionPressurePlane.renderOrder = 1;
  productionPressurePlane.visible = false;
  assemblyGroup.add(productionPressurePlane);

  volumeSampleLayout = createVolumeSampleLayout();
  const volumeGeometry = new THREE.BufferGeometry();
  volumeGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(volumeSampleLayout.positions, 3),
  );
  const volumeColors = new Float32Array(volumeSampleLayout.indices.length * 3);
  const volumeStrengths = new Float32Array(volumeSampleLayout.indices.length);
  for (let i = 0; i < volumeStrengths.length; i += 1) {
    volumeStrengths[i] = 0.035;
    volumeColors[i * 3] = 0.12;
    volumeColors[i * 3 + 1] = 0.30;
    volumeColors[i * 3 + 2] = 0.25;
  }
  volumeGeometry.setAttribute("color", new THREE.BufferAttribute(volumeColors, 3));
  volumeGeometry.setAttribute("strength", new THREE.BufferAttribute(volumeStrengths, 1));
  const volumeMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    vertexColors: true,
    uniforms: {
      pixelRatio: { value: renderer.getPixelRatio() },
    },
    vertexShader: `
      attribute float strength;
      varying vec3 pointColor;
      varying float pointStrength;
      uniform float pixelRatio;
      void main() {
        pointColor = color;
        pointStrength = strength;
        vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * viewPosition;
        gl_PointSize = pixelRatio * (1.0 + 3.6 * strength);
      }
    `,
    fragmentShader: `
      varying vec3 pointColor;
      varying float pointStrength;
      void main() {
        float radius = length(gl_PointCoord - vec2(0.5));
        if (radius > 0.5 || pointStrength < 0.025) discard;
        float edge = 1.0 - smoothstep(0.30, 0.50, radius);
        gl_FragColor = vec4(pointColor, edge * (0.12 + 0.78 * pointStrength));
      }
    `,
  });
  const volumePoints = new THREE.Points(volumeGeometry, volumeMaterial);
  volumePoints.frustumCulled = false;
  volumePoints.renderOrder = 4;
  assemblyGroup.add(volumePoints);
  productionVolume = {
    points: volumePoints,
    colors: volumeColors,
    strengths: volumeStrengths,
    updates: 0,
  };
  window.__agnuquena3D = {
    ready: true,
    pointCount: volumeSampleLayout.indices.length,
    updates: 0,
    visible: true,
    source: "live WebGPU 3D solver state",
  };

  function syncFluteMaterial() {
    const showVolume = productionVolume.points.visible;
    const showPlane = productionPressurePlane.visible;
    fluteMaterial.transparent = showVolume || showPlane;
    fluteMaterial.opacity = showVolume ? (showPlane ? 0.12 : 0.24) : (showPlane ? 0.30 : 1);
    fluteMaterial.depthWrite = !(showVolume || showPlane);
    fluteMaterial.needsUpdate = true;
  }
  syncFluteMaterial();

  const cameraViews = {
    full: {
      position: new THREE.Vector3(0, -0.16, -0.68),
      target: new THREE.Vector3(0, 0, 0),
    },
    holes: {
      position: new THREE.Vector3(0.024, -0.07, -0.28),
      target: new THREE.Vector3(0.024, 0, 0),
    },
    mouth: {
      position: new THREE.Vector3(-0.184, -0.03, -0.13),
      target: new THREE.Vector3(-0.184, 0, 0),
    },
  };
  for (const button of document.querySelectorAll("[data-production-view]")) {
    button.addEventListener("click", () => {
      const view = cameraViews[button.dataset.productionView];
      camera.position.copy(view.position);
      controls.target.copy(view.target);
      controls.update();
    });
  }

  ui.pressureOverlayToggle.addEventListener("click", () => {
    const showPressure = !productionPressurePlane.visible;
    productionPressurePlane.visible = showPressure;
    syncFluteMaterial();
    ui.pressureOverlayToggle.textContent = showPressure
      ? "Hide pressure plane"
      : "Show pressure plane";
  });
  ui.volumeOverlayToggle.addEventListener("click", () => {
    const showVolume = !productionVolume.points.visible;
    productionVolume.points.visible = showVolume;
    window.__agnuquena3D.visible = showVolume;
    syncFluteMaterial();
    ui.volumeOverlayToggle.textContent = showVolume
      ? "Hide 3D flow"
      : "Show 3D flow";
    if (showVolume) requestVolumeSample();
  });

  let lastPressureTextureUpdate = 0;
  function renderProduction(now) {
    const width = Math.max(1, ui.productionCanvas.clientWidth);
    const height = Math.max(1, ui.productionCanvas.clientHeight);
    if (ui.productionCanvas.width !== Math.round(width * renderer.getPixelRatio())
      || ui.productionCanvas.height !== Math.round(height * renderer.getPixelRatio())) {
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      volumeMaterial.uniforms.pixelRatio.value = renderer.getPixelRatio();
    }
    if (
      pressureTextureDirty
      && !gpuWorkPending
      && now - lastPressureTextureUpdate >= 500
    ) {
      pressureTexture.needsUpdate = true;
      pressureTextureDirty = false;
      lastPressureTextureUpdate = now;
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(renderProduction);
  }
  requestAnimationFrame(renderProduction);
}

for (const hole of SPEC.holes) {
  const option = document.createElement("option");
  option.value = hole.name;
  option.textContent = `${hole.note} · hole ${hole.name}`;
  ui.note.append(option);
}

function index3(x, y, z) {
  return x + NX * (y + NY * z);
}

function roundedSquareContains(a, b, side, radius) {
  const half = side / 2;
  const inner = half - radius;
  const aa = Math.abs(a);
  const bb = Math.abs(b);
  if (aa > half || bb > half) return false;
  if (aa <= inner || bb <= inner) return true;
  return (aa - inner) ** 2 + (bb - inner) ** 2 <= radius ** 2;
}

function notchContains(x, y, z) {
  const angle = SPEC.notch.angle * Math.PI / 180;
  const dx = x - SPEC.notch.centerX;
  const dz = z - SPEC.notch.centerZ;
  const axial = dx * Math.sin(angle) + dz * Math.cos(angle);
  const perpendicular = dx * Math.cos(angle) - dz * Math.sin(angle);
  return Math.abs(axial) <= SPEC.notch.length / 2
    && Math.hypot(perpendicular, y) <= SPEC.notch.radius;
}

function buildMask(activeHole, mode) {
  const mask = new Uint32Array(CELL_COUNT);
  const boreR = SPEC.boreDiameter / 2;
  const outerR = SPEC.outerDiameter / 2;
  const centerX = (NX - 1) / 2;
  const centerY = (NY - 1) / 2;
  const activeIndex = SPEC.holes.findIndex((hole) => hole.name === activeHole.name);

  for (let z = 0; z < NZ; z += 1) {
    const zMm = Z_ORIGIN_MM + (z + 0.5) * CELL_MM;
    for (let y = 0; y < NY; y += 1) {
      const yMm = (y - centerY) * CELL_MM;
      for (let x = 0; x < NX; x += 1) {
        const xMm = (x - centerX) * CELL_MM;
        const radius = Math.hypot(xMm, yMm);
        const cell = index3(x, y, z);
        const useProductionSTL = mode === "exact" && productionSolidMask;
        let material = useProductionSTL
          ? productionSolidMask[cell]
          : (
            zMm >= 0
            && zMm <= SPEC.acousticLength
            && radius > boreR
            && radius <= outerR
          ) ? 1 : 0;

        if (!useProductionSTL && material === 1 && notchContains(xMm, yMm, zMm)) material = 0;

        if (!useProductionSTL && material === 1) {
          for (let h = 0; h < SPEC.holes.length; h += 1) {
            const hole = SPEC.holes[h];
            const angle = hole.angle * Math.PI / 180;
            const normal = xMm * Math.cos(angle) + yMm * Math.sin(angle);
            const tangent = -xMm * Math.sin(angle) + yMm * Math.cos(angle);
            const open = h <= activeIndex;
            let tunnel = false;

            if (mode === "exact") {
              tunnel = roundedSquareContains(
                zMm - hole.z,
                tangent,
                hole.width,
                hole.width * SPEC.cornerRatio,
              ) && normal >= 0;
            } else {
              tunnel = Math.abs(zMm - hole.z) <= hole.diameter / 2;
            }

            if (tunnel) {
              material = (!open && normal > outerR - CELL_MM * 0.75) ? 1 : 0;
              break;
            }
          }
        }

        if (useProductionSTL) {
          for (let h = activeIndex + 1; h < SPEC.holes.length; h += 1) {
            const hole = SPEC.holes[h];
            const angle = hole.angle * Math.PI / 180;
            const normal = xMm * Math.cos(angle) + yMm * Math.sin(angle);
            const tangent = -xMm * Math.sin(angle) + yMm * Math.cos(angle);
            const onFingerPlane = Math.abs(normal - outerR) <= CELL_MM * 0.6;
            if (
              onFingerPlane
              && roundedSquareContains(
                zMm - hole.z,
                tangent,
                hole.width,
                hole.width * SPEC.cornerRatio,
              )
            ) {
              material = 1;
              break;
            }
          }
        }

        if (material === 0 && Math.abs(yMm) <= 4) {
          const inletDx = xMm - 15.5;
          const inletDz = zMm + 5.5;
          const alongJet = inletDx * -0.74 + inletDz * 0.67;
          const acrossJet = inletDx * -0.67 + inletDz * -0.74;
          if (Math.abs(alongJet) <= 0.6 && Math.abs(acrossJet) <= 0.6) material = 2;
        }

        mask[cell] = material;
      }
    }
  }
  return mask;
}

const computeShader = /* wgsl */ `
struct Params {
  dims: vec4<u32>,
  physical0: vec4<f32>,
  physical1: vec4<f32>,
  jet: vec4<f32>,
  view: vec4<u32>,
  display: vec4<f32>,
};

@group(0) @binding(0) var<storage, read> source: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read_write> outputState: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read> material: array<u32>;
@group(0) @binding(3) var<uniform> params: Params;

fn idx(p: vec3<u32>) -> u32 {
  return p.x + params.dims.x * (p.y + params.dims.y * p.z);
}

fn clampCell(p: vec3<i32>) -> vec3<u32> {
  return vec3<u32>(
    u32(clamp(p.x, 0, i32(params.dims.x) - 1)),
    u32(clamp(p.y, 0, i32(params.dims.y) - 1)),
    u32(clamp(p.z, 0, i32(params.dims.z) - 1))
  );
}

fn sampleVelocity(p: vec3<i32>) -> vec3<f32> {
  let q = clampCell(p);
  if (material[idx(q)] == 1u) { return vec3<f32>(0.0); }
  return source[idx(q)].xyz;
}

fn samplePressure(p: vec3<i32>, center: f32) -> f32 {
  let q = clampCell(p);
  if (material[idx(q)] == 1u) { return center; }
  return source[idx(q)].w;
}

fn inletVelocity(p: vec3<f32>, time: f32) -> vec3<f32> {
  let speed = params.jet.x;
  let amount = params.jet.y;
  let startup = smoothstep(0.0, 0.004, time);
  let phase0 = sin(171.0 * time + p.y * 1.73 + p.z * 0.39);
  let phase1 = sin(263.0 * time + p.x * 0.91 - p.y * 1.31);
  let phase2 = sin(389.0 * time + p.z * 0.77 + p.y * 2.17);
  let fluctuation = amount * vec3<f32>(phase0 * 0.35, phase1, phase2 * 0.55);
  return startup * speed * normalize(vec3<f32>(-0.74, 0.0, 0.67) + fluctuation);
}

@compute @workgroup_size(4, 4, 4)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  if (any(gid >= params.dims.xyz)) { return; }
  let centerIndex = idx(gid);
  let kind = material[centerIndex];
  if (kind == 1u) {
    outputState[centerIndex] = vec4<f32>(0.0);
    return;
  }

  let dt = params.physical0.x;
  let invDx = params.physical0.y;
  let rho = params.physical0.z;
  let c2 = params.physical0.w;
  let molecularNu = params.physical1.x;
  let cs = params.physical1.y;
  let time = params.physical1.z;
  let center = source[centerIndex];
  let p = vec3<i32>(gid);

  if (kind == 2u) {
    outputState[centerIndex] = vec4<f32>(inletVelocity(vec3<f32>(gid), time), 0.0);
    return;
  }

  let vxm = sampleVelocity(p + vec3<i32>(-1, 0, 0));
  let vxp = sampleVelocity(p + vec3<i32>( 1, 0, 0));
  let vym = sampleVelocity(p + vec3<i32>(0, -1, 0));
  let vyp = sampleVelocity(p + vec3<i32>(0,  1, 0));
  let vzm = sampleVelocity(p + vec3<i32>(0, 0, -1));
  let vzp = sampleVelocity(p + vec3<i32>(0, 0,  1));
  let pxm = samplePressure(p + vec3<i32>(-1, 0, 0), center.w);
  let pxp = samplePressure(p + vec3<i32>( 1, 0, 0), center.w);
  let pym = samplePressure(p + vec3<i32>(0, -1, 0), center.w);
  let pyp = samplePressure(p + vec3<i32>(0,  1, 0), center.w);
  let pzm = samplePressure(p + vec3<i32>(0, 0, -1), center.w);
  let pzp = samplePressure(p + vec3<i32>(0, 0,  1), center.w);

  let halfInvDx = 0.5 * invDx;
  let dvdx = (vxp - vxm) * halfInvDx;
  let dvdy = (vyp - vym) * halfInvDx;
  let dvdz = (vzp - vzm) * halfInvDx;
  let pressureGradient = vec3<f32>(pxp - pxm, pyp - pym, pzp - pzm) * halfInvDx;
  let pressureAdvection = dot(center.xyz, pressureGradient);
  let divergence = dvdx.x + dvdy.y + dvdz.z;
  let velocityAdvection = vec3<f32>(
    dot(center.xyz, vec3<f32>(dvdx.x, dvdy.x, dvdz.x)),
    dot(center.xyz, vec3<f32>(dvdx.y, dvdy.y, dvdz.y)),
    dot(center.xyz, vec3<f32>(dvdx.z, dvdy.z, dvdz.z))
  );

  let sxx = dvdx.x;
  let syy = dvdy.y;
  let szz = dvdz.z;
  let sxy = 0.5 * (dvdx.y + dvdy.x);
  let sxz = 0.5 * (dvdx.z + dvdz.x);
  let syz = 0.5 * (dvdy.z + dvdz.y);
  let strain = sqrt(max(0.0, 2.0 * (
    sxx*sxx + syy*syy + szz*szz
    + 2.0 * (sxy*sxy + sxz*sxz + syz*syz)
  )));
  let filterWidth = 1.0 / invDx;
  let eddyNu = (cs * filterWidth) * (cs * filterWidth) * strain;
  // Rusanov-equivalent viscosity damps only near-grid modes that a 1 mm LES
  // cannot resolve; long acoustic wavelengths remain effectively unchanged.
  let numericalNu = 0.25 * (sqrt(c2) + length(center.xyz)) * filterWidth;
  let nu = molecularNu + min(eddyNu, 0.003) + numericalNu;
  let lapVelocity = (vxm + vxp + vym + vyp + vzm + vzp - 6.0 * center.xyz) * invDx * invDx;
  let lapPressure = (pxm + pxp + pym + pyp + pzm + pzp - 6.0 * center.w) * invDx * invDx;

  var velocity = center.xyz + dt * (
    -velocityAdvection - pressureGradient / rho + nu * lapVelocity
  );
  var pressure = center.w + dt * (
    -pressureAdvection - rho * c2 * divergence + numericalNu * lapPressure
  );

  let edgeDistance = f32(min(
    min(min(gid.x, params.dims.x - 1u - gid.x), min(gid.y, params.dims.y - 1u - gid.y)),
    min(gid.z, params.dims.z - 1u - gid.z)
  ));
  let sponge = 1.0 - smoothstep(0.0, 7.0, edgeDistance);
  let attenuation = exp(-params.physical1.w * dt * sponge * sponge);
  velocity *= attenuation;
  pressure *= attenuation;

  let speed = length(velocity);
  if (speed > 60.0) { velocity *= 60.0 / speed; }
  pressure = clamp(pressure, -3000.0, 3000.0);
  outputState[centerIndex] = vec4<f32>(velocity, pressure);
}`;

const renderShader = /* wgsl */ `
struct Params {
  dims: vec4<u32>,
  physical0: vec4<f32>,
  physical1: vec4<f32>,
  jet: vec4<f32>,
  view: vec4<u32>,
  display: vec4<f32>,
};

@group(0) @binding(0) var<storage, read> state: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read> material: array<u32>;
@group(0) @binding(2) var<uniform> params: Params;

struct VertexOut {
  @builtin(position) position: vec4<f32>,
  @location(0) uv: vec2<f32>,
};

@vertex
fn vertexMain(@builtin(vertex_index) vertexIndex: u32) -> VertexOut {
  let positions = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
    vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0)
  );
  var out: VertexOut;
  let p = positions[vertexIndex];
  out.position = vec4<f32>(p, 0.0, 1.0);
  out.uv = vec2<f32>((p.x + 1.0) * 0.5, 1.0 - (p.y + 1.0) * 0.5);
  return out;
}

fn fieldIndex(x: u32, y: u32, z: u32) -> u32 {
  return x + params.dims.x * (y + params.dims.y * z);
}

fn velocityAt(x: u32, y: u32, z: u32) -> vec3<f32> {
  let cell = fieldIndex(x, y, z);
  if (material[cell] == 1u) { return vec3<f32>(0.0); }
  return state[cell].xyz;
}

fn sliceCoord(radial: f32, angle: f32) -> vec2<u32> {
  let center = vec2<f32>(
    0.5 * f32(params.dims.x - 1u),
    0.5 * f32(params.dims.y - 1u)
  );
  let direction = vec2<f32>(cos(angle), sin(angle));
  let maximum = vec2<f32>(f32(params.dims.x - 1u), f32(params.dims.y - 1u));
  return vec2<u32>(clamp(round(center + radial * direction), vec2<f32>(0.0), maximum));
}

@fragment
fn fragmentMain(in: VertexOut) -> @location(0) vec4<f32> {
  let z = min(u32(in.uv.x * f32(params.dims.z)), params.dims.z - 1u);
  let radial = (0.5 - in.uv.y) * f32(params.dims.x - 1u);
  let angle = params.display.w;
  let xy = sliceCoord(radial, angle);
  let x = xy.x;
  let y = xy.y;
  let cell = fieldIndex(x, y, z);
  let kind = material[cell];
  if (kind == 1u) { return vec4<f32>(0.055, 0.16, 0.135, 1.0); }
  if (kind == 2u) { return vec4<f32>(0.98, 0.63, 0.23, 1.0); }

  let value = state[cell];
  let neutral = vec3<f32>(0.008, 0.025, 0.023);
  if (params.view.y == 1u) {
    let speed = clamp(length(value.xyz) / params.display.y, 0.0, 1.0);
    return vec4<f32>(mix(neutral, vec3<f32>(1.0, 0.54, 0.16), pow(speed, 0.55)), 1.0);
  }
  if (params.view.y == 2u) {
    let radialMinus = sliceCoord(radial - 1.0, angle);
    let radialPlus = sliceCoord(radial + 1.0, angle);
    let zm = max(z, 1u) - 1u;
    let zp = min(z + 1u, params.dims.z - 1u);
    let dvdRadial = (
      velocityAt(radialPlus.x, radialPlus.y, z)
      - velocityAt(radialMinus.x, radialMinus.y, z)
    ) * 0.5 * params.physical0.y;
    let dvdz = (velocityAt(x, y, zp) - velocityAt(x, y, zm)) * 0.5 * params.physical0.y;
    let radialDirection = vec2<f32>(cos(angle), sin(angle));
    let omegaNormal = dot(dvdz.xy, radialDirection) - dvdRadial.z;
    let signed = tanh(omegaNormal / params.display.z);
    let color = select(
      mix(neutral, vec3<f32>(0.15, 0.40, 1.0), -signed),
      mix(neutral, vec3<f32>(1.0, 0.33, 0.12), signed),
      signed >= 0.0
    );
    return vec4<f32>(color, 1.0);
  }

  let pressure = tanh(value.w / params.display.x);
  let color = select(
    mix(neutral, vec3<f32>(0.12, 0.36, 1.0), -pressure),
    mix(neutral, vec3<f32>(1.0, 0.49, 0.20), pressure),
    pressure >= 0.0
  );
  return vec4<f32>(color, 1.0);
}`;

const volumeSampleShader = /* wgsl */ `
struct Params {
  dims: vec4<u32>,
  physical0: vec4<f32>,
  physical1: vec4<f32>,
  jet: vec4<f32>,
  view: vec4<u32>,
  display: vec4<f32>,
};

@group(0) @binding(0) var<storage, read> state: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read> material: array<u32>;
@group(0) @binding(2) var<uniform> params: Params;
@group(0) @binding(3) var<storage, read> sampleCells: array<u32>;
@group(0) @binding(4) var<storage, read_write> samples: array<vec4<f32>>;

fn idx(p: vec3<u32>) -> u32 {
  return p.x + params.dims.x * (p.y + params.dims.y * p.z);
}

fn clampCell(p: vec3<i32>) -> vec3<u32> {
  return vec3<u32>(
    u32(clamp(p.x, 0, i32(params.dims.x) - 1)),
    u32(clamp(p.y, 0, i32(params.dims.y) - 1)),
    u32(clamp(p.z, 0, i32(params.dims.z) - 1))
  );
}

fn velocityAt(p: vec3<i32>) -> vec3<f32> {
  let q = clampCell(p);
  if (material[idx(q)] == 1u) { return vec3<f32>(0.0); }
  return state[idx(q)].xyz;
}

@compute @workgroup_size(128)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let sampleIndex = gid.x;
  if (sampleIndex >= arrayLength(&sampleCells)) { return; }
  let cell = sampleCells[sampleIndex];
  if (material[cell] == 1u) {
    samples[sampleIndex] = vec4<f32>(0.0);
    return;
  }
  let z = cell / (params.dims.x * params.dims.y);
  let remainder = cell - z * params.dims.x * params.dims.y;
  let y = remainder / params.dims.x;
  let x = remainder - y * params.dims.x;
  let p = vec3<i32>(i32(x), i32(y), i32(z));
  let value = state[cell];
  var scalar = value.w;
  if (params.view.y == 1u) {
    scalar = length(value.xyz);
  } else if (params.view.y == 2u) {
    let vxm = velocityAt(p + vec3<i32>(-1, 0, 0));
    let vxp = velocityAt(p + vec3<i32>( 1, 0, 0));
    let vym = velocityAt(p + vec3<i32>(0, -1, 0));
    let vyp = velocityAt(p + vec3<i32>(0,  1, 0));
    let vzm = velocityAt(p + vec3<i32>(0, 0, -1));
    let vzp = velocityAt(p + vec3<i32>(0, 0,  1));
    let halfInvDx = 0.5 * params.physical0.y;
    let curl = vec3<f32>(
      (vyp.z - vym.z) - (vzp.y - vzm.y),
      (vzp.x - vzm.x) - (vxp.z - vxm.z),
      (vxp.y - vxm.y) - (vyp.x - vym.x)
    ) * halfInvDx;
    scalar = length(curl);
  }
  samples[sampleIndex] = vec4<f32>(value.xyz, scalar);
}`;

function createParamsRaw() {
  const raw = new ArrayBuffer(96);
  const u32 = new Uint32Array(raw);
  const f32 = new Float32Array(raw);
  u32.set([NX, NY, NZ, 0], 0);
  f32.set([DT_SECONDS, 1 / CELL_M, AIR_DENSITY, SOUND_SPEED2], 4);
  f32.set([KINEMATIC_VISCOSITY, SMAGORINSKY, 0, SPONGE_RATE], 8);
  f32.set([Number(ui.jetSpeed.value), Number(ui.turbulence.value) / 100, Z_ORIGIN_MM, CELL_MM], 12);
  const viewModes = { pressure: 0, speed: 1, vorticity: 2 };
  u32.set([Math.floor(NY / 2), viewModes[ui.field.value], 0, 0], 16);
  f32.set([120, 15, 8000, Number(ui.sliceAngle.value) * Math.PI / 180], 20);
  return raw;
}

function updateParams() {
  if (!gpu) return;
  const raw = createParamsRaw();
  new Float32Array(raw)[10] = stepCount * DT_SECONDS;
  gpu.device.queue.writeBuffer(gpu.paramsBuffer, 0, raw);
}

async function initWebGPU() {
  if (!navigator.gpu) throw new Error("WebGPU is unavailable");
  const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
  if (!adapter) throw new Error("No WebGPU adapter");
  const requiredBytes = CELL_COUNT * 16;
  if (adapter.limits.maxStorageBufferBindingSize < requiredBytes) {
    throw new Error("WebGPU storage-buffer limit is too small for the CFD domain");
  }
  const device = await adapter.requestDevice({
    requiredLimits: { maxStorageBufferBindingSize: requiredBytes },
  });
  const context = ui.canvas.getContext("webgpu");
  const format = navigator.gpu.getPreferredCanvasFormat();
  context.configure({ device, format, alphaMode: "opaque" });

  const stateBuffers = Array.from({ length: 2 }, () => device.createBuffer({
    size: requiredBytes,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC,
  }));
  const maskBuffer = device.createBuffer({
    size: CELL_COUNT * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
  });
  const paramsBuffer = device.createBuffer({
    size: 96,
    usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
  });
  const probeBuffer = device.createBuffer({
    size: 16,
    usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
  });
  const volumeSampleBytes = volumeSampleLayout.indices.byteLength * 4;
  const volumeSampleIndexBuffer = device.createBuffer({
    size: volumeSampleLayout.indices.byteLength,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
  });
  const volumeSampleOutputBuffer = device.createBuffer({
    size: volumeSampleBytes,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
  });
  const volumeSampleReadbackBuffer = device.createBuffer({
    size: volumeSampleBytes,
    usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
  });
  device.queue.writeBuffer(paramsBuffer, 0, createParamsRaw());
  device.queue.writeBuffer(volumeSampleIndexBuffer, 0, volumeSampleLayout.indices);

  const computeModule = device.createShaderModule({ code: computeShader });
  const renderModule = device.createShaderModule({ code: renderShader });
  const volumeSampleModule = device.createShaderModule({ code: volumeSampleShader });
  const compilation = await Promise.all([
    computeModule.getCompilationInfo(),
    renderModule.getCompilationInfo(),
    volumeSampleModule.getCompilationInfo(),
  ]);
  const errors = compilation.flatMap((info) => info.messages.filter((message) => message.type === "error"));
  if (errors.length) throw new Error(errors.map((error) => error.message).join("\n"));

  const computePipeline = device.createComputePipeline({
    layout: "auto",
    compute: { module: computeModule, entryPoint: "main" },
  });
  const renderPipeline = device.createRenderPipeline({
    layout: "auto",
    vertex: { module: renderModule, entryPoint: "vertexMain" },
    fragment: { module: renderModule, entryPoint: "fragmentMain", targets: [{ format }] },
    primitive: { topology: "triangle-list" },
  });
  const volumeSamplePipeline = device.createComputePipeline({
    layout: "auto",
    compute: { module: volumeSampleModule, entryPoint: "main" },
  });

  const computeGroups = stateBuffers.map((buffer, index) => device.createBindGroup({
    layout: computePipeline.getBindGroupLayout(0),
    entries: [
      { binding: 0, resource: { buffer } },
      { binding: 1, resource: { buffer: stateBuffers[1 - index] } },
      { binding: 2, resource: { buffer: maskBuffer } },
      { binding: 3, resource: { buffer: paramsBuffer } },
    ],
  }));
  const renderGroups = stateBuffers.map((buffer) => device.createBindGroup({
    layout: renderPipeline.getBindGroupLayout(0),
    entries: [
      { binding: 0, resource: { buffer } },
      { binding: 1, resource: { buffer: maskBuffer } },
      { binding: 2, resource: { buffer: paramsBuffer } },
    ],
  }));
  const volumeSampleGroups = stateBuffers.map((buffer) => device.createBindGroup({
    layout: volumeSamplePipeline.getBindGroupLayout(0),
    entries: [
      { binding: 0, resource: { buffer } },
      { binding: 1, resource: { buffer: maskBuffer } },
      { binding: 2, resource: { buffer: paramsBuffer } },
      { binding: 3, resource: { buffer: volumeSampleIndexBuffer } },
      { binding: 4, resource: { buffer: volumeSampleOutputBuffer } },
    ],
  }));

  device.lost.then(() => {
    running = false;
    ui.gpuBadge.className = "status fallback";
    ui.gpuBadge.innerHTML = "<span></span>GPU device lost";
  });
  device.addEventListener("uncapturederror", (event) => {
    console.error("WebGPU validation error", event.error);
  });

  return {
    device,
    context,
    stateBuffers,
    maskBuffer,
    paramsBuffer,
    probeBuffer,
    volumeSampleBytes,
    volumeSampleOutputBuffer,
    volumeSampleReadbackBuffer,
    computePipeline,
    renderPipeline,
    volumeSamplePipeline,
    computeGroups,
    renderGroups,
    volumeSampleGroups,
    state: 0,
  };
}

function colorVolumeSamples(samples) {
  if (!productionVolume) return;
  const mode = ui.field.value;
  const colors = productionVolume.colors;
  const strengths = productionVolume.strengths;
  for (let i = 0; i < strengths.length; i += 1) {
    const scalar = samples[i * 4 + 3];
    let strength;
    let negative = false;
    if (mode === "pressure") {
      strength = Math.abs(Math.tanh(scalar / 120));
      negative = scalar < 0;
    } else if (mode === "speed") {
      strength = Math.min(1, Math.max(0, scalar / 15));
    } else {
      strength = Math.min(1, Math.max(0, scalar / 8000));
    }
    const fieldStrength = strength;
    strength = 0.035 + 0.965 * strength;
    strengths[i] = strength;
    const offset = i * 3;
    if (fieldStrength < 0.025) {
      colors[offset] = 0.12;
      colors[offset + 1] = 0.30;
      colors[offset + 2] = 0.25;
    } else if (mode === "speed") {
      colors[offset] = 0.25 + 0.75 * strength;
      colors[offset + 1] = 0.86 - 0.28 * strength;
      colors[offset + 2] = 0.62 - 0.48 * strength;
    } else if (negative) {
      colors[offset] = 0.12;
      colors[offset + 1] = 0.36 + 0.12 * strength;
      colors[offset + 2] = 1.0;
    } else {
      colors[offset] = 1.0;
      colors[offset + 1] = 0.66 - 0.32 * strength;
      colors[offset + 2] = 0.18;
    }
  }
  productionVolume.points.geometry.attributes.color.needsUpdate = true;
  productionVolume.points.geometry.attributes.strength.needsUpdate = true;
  productionVolume.updates += 1;
  window.__agnuquena3D.updates = productionVolume.updates;
  window.__agnuquena3D.field = mode;
  ui.volumeStatus.textContent = (
    `${volumeSampleLayout.indices.length.toLocaleString()} live 3D ${mode} samples`
  );
}

function requestVolumeSample() {
  if (
    !gpu
    || !productionVolume
    || !productionVolume.points.visible
    || volumeReadPending
  ) return;
  const now = performance.now();
  if (now - lastVolumeSampleAt < 250) return;
  lastVolumeSampleAt = now;
  volumeReadPending = true;
  const encoder = gpu.device.createCommandEncoder();
  const pass = encoder.beginComputePass();
  pass.setPipeline(gpu.volumeSamplePipeline);
  pass.setBindGroup(0, gpu.volumeSampleGroups[gpu.state]);
  pass.dispatchWorkgroups(Math.ceil(volumeSampleLayout.indices.length / 128));
  pass.end();
  encoder.copyBufferToBuffer(
    gpu.volumeSampleOutputBuffer,
    0,
    gpu.volumeSampleReadbackBuffer,
    0,
    gpu.volumeSampleBytes,
  );
  gpu.device.queue.submit([encoder.finish()]);
  gpu.volumeSampleReadbackBuffer.mapAsync(GPUMapMode.READ).then(() => {
    const samples = new Float32Array(
      gpu.volumeSampleReadbackBuffer.getMappedRange().slice(0),
    );
    gpu.volumeSampleReadbackBuffer.unmap();
    colorVolumeSamples(samples);
    volumeReadPending = false;
  }).catch((error) => {
    console.error("3D CFD volume readback failed", error);
    volumeReadPending = false;
  });
}

async function readProbe(zMm = 8) {
  if (!gpu) return null;
  const z = Math.max(0, Math.min(NZ - 1, Math.floor((zMm - Z_ORIGIN_MM) / CELL_MM)));
  const cell = index3(Math.floor(NX / 2), Math.floor(NY / 2), z);
  const encoder = gpu.device.createCommandEncoder();
  encoder.copyBufferToBuffer(gpu.stateBuffers[gpu.state], cell * 16, gpu.probeBuffer, 0, 16);
  gpu.device.queue.submit([encoder.finish()]);
  await gpu.probeBuffer.mapAsync(GPUMapMode.READ);
  const values = Array.from(new Float32Array(gpu.probeBuffer.getMappedRange()).slice());
  gpu.probeBuffer.unmap();
  return { velocity: values.slice(0, 3), pressurePa: values[3], zMm };
}

function materialStatistics() {
  const counts = { air: 0, solid: 0, inlet: 0 };
  if (!fallbackMask) return counts;
  for (const kind of fallbackMask) {
    if (kind === 1) counts.solid += 1;
    else if (kind === 2) counts.inlet += 1;
    else counts.air += 1;
  }
  return counts;
}

function resetGPU() {
  stepCount = 0;
  renderDirty = true;
  if (!gpu) return;
  const zeros = new Float32Array(CELL_COUNT * 4);
  for (const buffer of gpu.stateBuffers) gpu.device.queue.writeBuffer(buffer, 0, zeros);
  gpu.state = 0;
  updateParams();
}

function uploadMask() {
  fallbackMask = buildMask(selectedHole, boundaryMode);
  if (gpu) gpu.device.queue.writeBuffer(gpu.maskBuffer, 0, fallbackMask);
  resetGPU();
  drawFallback();
}

function encodeRender(encoder) {
  const pass = encoder.beginRenderPass({
    colorAttachments: [{
      view: gpu.context.getCurrentTexture().createView(),
      clearValue: { r: 0.005, g: 0.02, b: 0.018, a: 1 },
      loadOp: "clear",
      storeOp: "store",
    }],
  });
  pass.setPipeline(gpu.renderPipeline);
  pass.setBindGroup(0, gpu.renderGroups[gpu.state]);
  pass.draw(6);
  pass.end();
}

function stepGPU(iterations) {
  if (gpuWorkPending) return;
  updateParams();
  const encoder = gpu.device.createCommandEncoder();
  for (let i = 0; i < iterations; i += 1) {
    const pass = encoder.beginComputePass();
    pass.setPipeline(gpu.computePipeline);
    pass.setBindGroup(0, gpu.computeGroups[gpu.state]);
    pass.dispatchWorkgroups(Math.ceil(NX / 4), Math.ceil(NY / 4), Math.ceil(NZ / 4));
    pass.end();
    gpu.state = 1 - gpu.state;
    stepCount += 1;
  }
  encodeRender(encoder);
  renderDirty = false;
  gpuWorkPending = true;
  gpu.device.queue.submit([encoder.finish()]);
  gpu.device.queue.onSubmittedWorkDone().then(() => {
    pressureTextureDirty = true;
    requestVolumeSample();
    gpuWorkPending = false;
  }).catch(() => {
    gpuWorkPending = false;
  });
}

function renderGPUOnly() {
  if (gpuWorkPending || !renderDirty) return;
  updateParams();
  const encoder = gpu.device.createCommandEncoder();
  encodeRender(encoder);
  renderDirty = false;
  gpuWorkPending = true;
  gpu.device.queue.submit([encoder.finish()]);
  gpu.device.queue.onSubmittedWorkDone().then(() => {
    pressureTextureDirty = true;
    requestVolumeSample();
    gpuWorkPending = false;
  }).catch(() => {
    gpuWorkPending = false;
  });
}

function drawFallback() {
  if (gpu || !fallbackMask) return;
  let ctx = ui.canvas.getContext("2d");
  if (!ctx) {
    const replacement = ui.canvas.cloneNode(false);
    ui.canvas.replaceWith(replacement);
    ui.canvas = replacement;
    ctx = replacement.getContext("2d");
  }
  const width = ui.canvas.width;
  const height = ui.canvas.height;
  ctx.fillStyle = "#020b0a";
  ctx.fillRect(0, 0, width, height);
  const sliceY = Math.floor(NY / 2);
  const cellW = width / NZ;
  const cellH = height / NX;
  for (let z = 0; z < NZ; z += 1) {
    for (let x = 0; x < NX; x += 1) {
      const kind = fallbackMask[index3(x, sliceY, z)];
      ctx.fillStyle = kind === 1 ? "#173d34" : kind === 2 ? "#f0a13d" : "#061411";
      ctx.fillRect(z * cellW, x * cellH, Math.ceil(cellW), Math.ceil(cellH));
    }
  }
  ctx.fillStyle = "rgba(231,245,239,.72)";
  ctx.font = "12px DM Mono, monospace";
  ctx.fillText("3D CFD GEOMETRY · WEBGPU REQUIRED TO ADVANCE FLOW", 20, 34);
}

function drawGeometry() {
  const canvas = ui.geometry;
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.max(600, Math.round(rect.width * ratio));
  canvas.height = Math.max(280, Math.round(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  ctx.clearRect(0, 0, width, height);
  const left = 52;
  const right = width - 24;
  const axisY = height * 0.53;
  const scale = (right - left) / SPEC.acousticLength;

  ctx.strokeStyle = "rgba(146,194,175,.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.rect(left, axisY - 26, right - left, 52);
  ctx.stroke();
  ctx.fillStyle = "rgba(105,224,180,.06)";
  ctx.fill();
  ctx.strokeStyle = "rgba(145,170,161,.22)";
  ctx.setLineDash([3, 5]);
  for (let mm = 0; mm <= 400; mm += 50) {
    const x = left + mm * scale;
    ctx.beginPath();
    ctx.moveTo(x, axisY - 52);
    ctx.lineTo(x, axisY + 62);
    ctx.stroke();
    ctx.fillStyle = "#547068";
    ctx.font = "9px DM Mono, monospace";
    ctx.fillText(`${mm}`, x - 7, axisY + 82);
  }
  ctx.setLineDash([]);
  for (const hole of SPEC.holes) {
    const x = left + hole.z * scale;
    const active = hole.name === selectedHole.name;
    const size = 8 + hole.width * 0.85;
    ctx.fillStyle = active ? "#ffb55f" : "#467b69";
    ctx.strokeStyle = active ? "#ffd49e" : "#69a88f";
    ctx.lineWidth = active ? 2 : 1;
    ctx.beginPath();
    ctx.roundRect(x - size / 2, axisY - size / 2, size, size, size * SPEC.cornerRatio);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = active ? "#ffcf94" : "#79998d";
    ctx.font = `${active ? "500 " : ""}10px DM Mono, monospace`;
    ctx.fillText(hole.name, x - 5, axisY - 44);
    if (active) {
      ctx.fillStyle = "#ffb55f";
      ctx.fillText(`${hole.z.toFixed(1)} mm`, x - 27, axisY + 50);
    }
  }
  ctx.fillStyle = "#91aaa1";
  ctx.font = "9px DM Mono, monospace";
  ctx.fillText("NOTCH + JET", left, 25);
  ctx.textAlign = "right";
  ctx.fillText("OPEN FOOT", right, 25);
  ctx.textAlign = "left";
  ctx.fillText("AXIAL CENTER (MM)", left, axisY + 106);
}

function updateProfile() {
  ui.title.textContent = `${selectedHole.note} · Hole ${selectedHole.name}`;
  ui.profileTitle.textContent = `Hole ${selectedHole.name} profile`;
  ui.target.textContent = `${selectedHole.target.toFixed(2)} Hz`;
  ui.diameter.textContent = `${selectedHole.diameter.toFixed(2)} mm`;
  ui.profile.textContent = `${selectedHole.width.toFixed(2)} mm`;
  ui.position.textContent = `${selectedHole.z.toFixed(2)} mm`;
  ui.profileWidth.textContent = `${selectedHole.width.toFixed(2)} mm`;
  const visualSize = 112;
  const x = 120 - visualSize / 2;
  ui.profileShape.setAttribute("x", String(x));
  ui.profileShape.setAttribute("y", String(x));
  ui.profileShape.setAttribute("width", String(visualSize));
  ui.profileShape.setAttribute("height", String(visualSize));
  ui.profileShape.setAttribute("rx", String(visualSize * SPEC.cornerRatio));
}

function updateJetReadouts() {
  const speed = Number(ui.jetSpeed.value);
  ui.jetSpeedValue.value = `${speed.toFixed(1)} m/s`;
  ui.turbulenceValue.value = `${ui.turbulence.value}%`;
  ui.reynolds.textContent = Math.round(speed * SPEC.notch.width / 1000 / KINEMATIC_VISCOSITY).toLocaleString();
  updateParams();
}

function updateRunButton() {
  ui.toggle.innerHTML = running
    ? '<span class="play-icon" style="border:0;width:8px;height:10px;background:linear-gradient(90deg,currentColor 0 35%,transparent 35% 65%,currentColor 65%)"></span> Pause CFD'
    : '<span class="play-icon" aria-hidden="true"></span> Run CFD';
}

function wireControls() {
  ui.note.addEventListener("change", () => {
    selectedHole = SPEC.holes.find((hole) => hole.name === ui.note.value) || SPEC.holes[0];
    updateProfile();
    uploadMask();
  });
  ui.field.addEventListener("change", () => {
    updateParams();
    renderDirty = true;
    lastVolumeSampleAt = 0;
    if (gpu) renderGPUOnly();
  });
  ui.toggle.addEventListener("click", () => {
    if (!gpu) return;
    running = !running;
    updateRunButton();
  });
  ui.reset.addEventListener("click", () => {
    resetGPU();
    if (gpu) renderGPUOnly();
  });
  ui.speed.addEventListener("input", () => { ui.speedValue.value = ui.speed.value; });
  ui.sliceAngle.addEventListener("input", () => {
    ui.sliceAngleValue.value = `${ui.sliceAngle.value}°`;
    if (productionPressurePlane) {
      productionPressurePlane.rotation.z = Number(ui.sliceAngle.value) * Math.PI / 180;
    }
    updateParams();
    renderDirty = true;
    if (gpu && !running) renderGPUOnly();
  });
  ui.jetSpeed.addEventListener("input", updateJetReadouts);
  ui.turbulence.addEventListener("input", updateJetReadouts);
}

function animate() {
  if (gpu) {
    if (running) stepGPU(Number(ui.speed.value));
    else if (renderDirty) renderGPUOnly();
  }
  ui.simTime.textContent = `${(stepCount * DT_SECONDS * 1000).toFixed(3)} ms`;
  requestAnimationFrame(animate);
}

async function start() {
  wireControls();
  try {
    await loadProductionAssets();
  } catch (error) {
    console.error(error);
    ui.gpuBadge.className = "status fallback";
    ui.gpuBadge.innerHTML = "<span></span>Production STL load failed";
    ui.productionProof.textContent = "Production STL load failed";
    return;
  }
  updateProfile();
  updateJetReadouts();
  fallbackMask = buildMask(selectedHole, boundaryMode);
  try {
    gpu = await Promise.race([
      initWebGPU(),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error("WebGPU initialization timed out")), 6000);
      }),
    ]);
    ui.gpuBadge.className = "status ready";
    ui.gpuBadge.innerHTML = "<span></span>WebGPU 3D LES";
    uploadMask();
    renderGPUOnly();
    window.__agnuquenaCFD = {
      readProbe,
      materialStatistics,
      setViewAngle(angleDegrees) {
        const normalized = ((Number(angleDegrees) % 360) + 360) % 360;
        ui.sliceAngle.value = String(Math.round(normalized));
        ui.sliceAngle.dispatchEvent(new Event("input", { bubbles: true }));
        return Number(ui.sliceAngle.value);
      },
      getViewAngle() {
        return Number(ui.sliceAngle.value);
      },
      configuration: {
        grid: [NX, NY, NZ],
        voxelMm: CELL_MM,
        timeStepSeconds: DT_SECONDS,
        model: "weakly-compressible Navier-Stokes LES",
        geometrySource: productionMetadata.assembly.file,
        geometrySha256: productionMetadata.assembly.sha256,
        boundarySource: productionMetadata.solver_mask.derivation,
        visualization: "orbitable production STL with independent 2D plane and live 3D solver volume",
      },
    };
  } catch (error) {
    console.error(error);
    ui.gpuBadge.className = "status fallback";
    ui.gpuBadge.innerHTML = "<span></span>Static fallback";
    drawFallback();
  }
  animate();
}

start();
