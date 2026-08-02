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
const JET_ORIGIN_MM = [15.5, 0, -5.5];
const CELL_COUNT = NX * NY * NZ;
const simulationParameters = {
  airDensity: 1.204,
  soundSpeed: 343,
  kinematicViscosity: 1.5e-5,
  courant: 0.28,
  smagorinsky: 0.17,
  spongeRate: 16000,
  startupRampUs: 5,
  pressureScale: 120,
  speedScale: 15,
  vorticityScale: 8000,
  jetDeflectionGain: 200,
  jetDirectionX: -0.718988,
  jetDirectionY: 0,
  jetDirectionZ: 0.695022,
  jetTargetX: 9.5,
  jetTargetY: 0,
  jetTargetZ: 0.3,
};

function timeStepSeconds() {
  return simulationParameters.courant * CELL_M
    / (simulationParameters.soundSpeed + Number(ui.jetSpeed?.value || 20));
}

const ui = {
  gpuBadge: document.querySelector("#gpuBadge"),
  productionCanvas: document.querySelector("#productionCanvas"),
  productionRevision: document.querySelector("#productionRevision"),
  productionProof: document.querySelector("#productionProof"),
  volumeStatus: document.querySelector("#volumeStatus"),
  volumeOverlayToggle: document.querySelector("#volumeOverlayToggle"),
  note: document.querySelector("#noteSelect"),
  field: document.querySelector("#fieldSelect"),
  controlTabButtons: [...document.querySelectorAll("[data-control-tab]")],
  controlPanels: [...document.querySelectorAll("[data-control-panel]")],
  parameterInputs: [...document.querySelectorAll("[data-sim-param]")],
  parameterOutputs: [...document.querySelectorAll("[data-param-output]")],
  playerBoundary: document.querySelector("#playerBoundarySelect"),
  playerMetric: document.querySelector("#playerMetric"),
  title: document.querySelector("#simulationTitle"),
  target: document.querySelector("#targetMetric"),
  holeDiameter: document.querySelector("#holeDiameterMetric"),
  holePosition: document.querySelector("#holePositionMetric"),
  holeProfile: document.querySelector("#holeProfileMetric"),
  timeStep: document.querySelector("#timeStepMetric"),
  oscillation: document.querySelector("#oscillationMetric"),
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
let playerBoundary = "none";
let playerSolidCells = 0;
let syncPlayerVisual = () => {};
let updateJetPath = () => {};
let jetSignalMinimum = Number.POSITIVE_INFINITY;
let jetSignalMaximum = Number.NEGATIVE_INFINITY;
let jetVisualMinimum = Number.POSITIVE_INFINITY;
let jetVisualMaximum = Number.NEGATIVE_INFINITY;
let running = false;
let stepCount = 0;
let gpu = null;
let gpuWorkPending = false;
let fallbackMask = null;
let productionSolidMask = null;
let productionMetadata = null;
let productionVolume = null;
let volumeSampleLayout = null;
let volumeReadPending = false;
let lastVolumeSampleAt = 0;

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
  camera.position.set(-0.75, 0, -0.15);

  const controls = new OrbitControls(camera, ui.productionCanvas);
  controls.target.set(0, 0, 0);
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
  assemblyGroup.rotation.x = Math.PI / 2;
  assemblyGroup.position.y = 0.20;
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

  const skinMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd79a73,
    roughness: 0.72,
    transparent: true,
    opacity: 0.34,
    depthWrite: false,
  });
  const clothingMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x315d72,
    roughness: 0.82,
    transparent: true,
    opacity: 0.28,
    depthWrite: false,
  });
  const playerGroup = new THREE.Group();
  const bodyGroup = new THREE.Group();
  assemblyGroup.add(playerGroup);
  playerGroup.add(bodyGroup);

  function addEllipsoid(parent, radii, position, material = skinMaterial) {
    const part = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), material);
    part.scale.set(...radii);
    part.position.set(...position);
    part.renderOrder = 1;
    parent.add(part);
    return part;
  }

  function addLimb(parent, start, end, radius, material = skinMaterial) {
    const from = new THREE.Vector3(...start);
    const to = new THREE.Vector3(...end);
    const direction = to.clone().sub(from);
    const length = direction.length();
    const limb = new THREE.Mesh(
      new THREE.CapsuleGeometry(radius, Math.max(0.001, length - 2 * radius), 8, 16),
      material,
    );
    limb.position.copy(from).add(to).multiplyScalar(0.5);
    limb.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
    limb.renderOrder = 1;
    parent.add(limb);
    return limb;
  }

  addEllipsoid(playerGroup, [0.050, 0.066, 0.055], [0.048, 0, -0.022]);
  addEllipsoid(playerGroup, [0.013, 0.018, 0.038], [0.012, -0.008, 0.185]);
  addEllipsoid(playerGroup, [0.013, 0.018, 0.038], [0.012, 0.008, 0.270]);
  addEllipsoid(bodyGroup, [0.11, 0.15, 0.29], [0.10, 0, 0.31], clothingMaterial);
  addEllipsoid(bodyGroup, [0.055, 0.055, 0.30], [0.10, -0.07, 0.77], clothingMaterial);
  addEllipsoid(bodyGroup, [0.055, 0.055, 0.30], [0.10, 0.07, 0.77], clothingMaterial);
  addLimb(bodyGroup, [0.07, -0.13, 0.16], [0.05, -0.19, 0.24], 0.035);
  addLimb(bodyGroup, [0.05, -0.19, 0.24], [0.012, -0.008, 0.270], 0.032);
  addLimb(bodyGroup, [0.07, 0.13, 0.16], [0.05, 0.19, 0.20], 0.035);
  addLimb(bodyGroup, [0.05, 0.19, 0.20], [0.012, 0.008, 0.185], 0.032);

  syncPlayerVisual = () => {
    playerGroup.visible = playerBoundary !== "none";
    bodyGroup.visible = playerBoundary === "full";
    controls.maxDistance = playerBoundary === "full" ? 3 : 1.4;
    if (playerBoundary === "full") {
      camera.position.set(-2.2, -0.28, -0.30);
      controls.target.set(0, -0.30, 0);
    } else {
      camera.position.set(-0.75, 0, -0.15);
      controls.target.set(0, 0, 0);
    }
    controls.update();
    if (window.__agnuquena3D) window.__agnuquena3D.playerBoundary = playerBoundary;
  };
  syncPlayerVisual();

  const jetPointCount = 25;
  const jetPositions = new Float32Array(jetPointCount * 3);
  const jetGeometry = new THREE.BufferGeometry();
  jetGeometry.setAttribute("position", new THREE.BufferAttribute(jetPositions, 3));
  const jetLine = new THREE.Line(
    jetGeometry,
    new THREE.LineBasicMaterial({ color: 0x7fffd4, transparent: true, opacity: 0.95 }),
  );
  jetLine.renderOrder = 6;
  assemblyGroup.add(jetLine);
  const jetDots = new THREE.Points(
    jetGeometry,
    new THREE.PointsMaterial({ color: 0x7fffd4, size: 0.0032, sizeAttenuation: true }),
  );
  jetDots.renderOrder = 6;
  assemblyGroup.add(jetDots);
  const targetMarker = new THREE.Mesh(
    new THREE.SphereGeometry(0.0038, 16, 10),
    new THREE.MeshBasicMaterial({ color: 0xffb55f }),
  );
  targetMarker.renderOrder = 7;
  assemblyGroup.add(targetMarker);

  updateJetPath = (oscillation = 0) => {
    const origin = new THREE.Vector3(...JET_ORIGIN_MM).multiplyScalar(0.001);
    const target = new THREE.Vector3(
      simulationParameters.jetTargetX,
      simulationParameters.jetTargetY,
      simulationParameters.jetTargetZ,
    ).multiplyScalar(0.001);
    const direction = target.clone().sub(origin).normalize();
    const lateral = new THREE.Vector3(0, 1, 0).cross(direction);
    if (lateral.lengthSq() < 1e-8) lateral.set(1, 0, 0);
    lateral.normalize();
    for (let i = 0; i < jetPointCount; i += 1) {
      const t = i / (jetPointCount - 1);
      const point = origin.clone().lerp(target, t)
        .addScaledVector(lateral, Math.sin(Math.PI * t) * oscillation * 0.0035);
      jetPositions[i * 3] = point.x;
      jetPositions[i * 3 + 1] = point.y;
      jetPositions[i * 3 + 2] = point.z;
    }
    jetGeometry.attributes.position.needsUpdate = true;
    targetMarker.position.copy(target);
  };
  updateJetPath(0);

  volumeSampleLayout = createVolumeSampleLayout();
  const volumeGeometry = new THREE.BufferGeometry();
  volumeGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(volumeSampleLayout.positions, 3),
  );
  const volumeColors = new Float32Array(volumeSampleLayout.indices.length * 3);
  const volumeStrengths = new Float32Array(volumeSampleLayout.indices.length);
  const volumeFluid = new Float32Array(volumeSampleLayout.indices.length).fill(1);
  for (let i = 0; i < volumeStrengths.length; i += 1) {
    volumeStrengths[i] = 0;
    volumeColors[i * 3] = 0.12;
    volumeColors[i * 3 + 1] = 0.30;
    volumeColors[i * 3 + 2] = 0.25;
  }
  volumeGeometry.setAttribute("color", new THREE.BufferAttribute(volumeColors, 3));
  volumeGeometry.setAttribute("strength", new THREE.BufferAttribute(volumeStrengths, 1));
  volumeGeometry.setAttribute("fluid", new THREE.BufferAttribute(volumeFluid, 1));
  const volumeMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    vertexColors: true,
    uniforms: {
      pixelRatio: { value: renderer.getPixelRatio() },
    },
    vertexShader: `
      attribute float strength;
      attribute float fluid;
      varying vec3 pointColor;
      varying float pointStrength;
      uniform float pixelRatio;
      void main() {
        pointColor = color;
        pointStrength = fluid * strength;
        vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * viewPosition;
        gl_PointSize = pixelRatio * (1.5 + 5.5 * strength);
      }
    `,
    fragmentShader: `
      varying vec3 pointColor;
      varying float pointStrength;
      void main() {
        float radius = length(gl_PointCoord - vec2(0.5));
        if (radius > 0.5 || pointStrength < 0.015) discard;
        float edge = 1.0 - smoothstep(0.30, 0.50, radius);
        gl_FragColor = vec4(pointColor, edge * (0.20 + 0.80 * pointStrength));
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
    fluid: volumeFluid,
    updates: 0,
  };
  assemblyGroup.updateWorldMatrix(true, false);
  const boreOrigin = assemblyGroup.localToWorld(new THREE.Vector3(0, 0, 0));
  const boreDirection = assemblyGroup.localToWorld(new THREE.Vector3(0, 0, 1))
    .sub(boreOrigin)
    .normalize();
  window.__agnuquena3D = {
    ready: true,
    pointCount: volumeSampleLayout.indices.length,
    updates: 0,
    visible: true,
    orientation: "vertical",
    boreAxis: boreDirection.toArray(),
    source: "actual solver field with live near-edge jet response",
  };

  function syncFluteMaterial() {
    const showVolume = productionVolume.points.visible;
    fluteMaterial.transparent = showVolume;
    fluteMaterial.opacity = showVolume ? 0.22 : 1;
    fluteMaterial.depthWrite = !showVolume;
    fluteMaterial.needsUpdate = true;
  }
  syncFluteMaterial();

  const cameraViews = {
    full: {
      position: new THREE.Vector3(-0.75, 0, -0.15),
      target: new THREE.Vector3(0, 0, 0),
    },
    holes: {
      position: new THREE.Vector3(-0.34, -0.05, -0.08),
      target: new THREE.Vector3(0, -0.05, 0),
    },
    mouth: {
      position: new THREE.Vector3(-0.25, 0.18, -0.05),
      target: new THREE.Vector3(0, 0.19, 0),
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

  ui.volumeOverlayToggle.addEventListener("click", () => {
    const showVolume = !productionVolume.points.visible;
    productionVolume.points.visible = showVolume;
    window.__agnuquena3D.visible = showVolume;
    syncFluteMaterial();
    ui.volumeOverlayToggle.textContent = showVolume
      ? "Hide pressure waves"
      : "Show pressure waves";
    if (showVolume) requestVolumeSample();
  });

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

function ellipsoidContains(x, y, z, center, radii) {
  return ((x - center[0]) / radii[0]) ** 2
    + ((y - center[1]) / radii[1]) ** 2
    + ((z - center[2]) / radii[2]) ** 2 <= 1;
}

function playerBoundaryContains(x, y, z) {
  if (playerBoundary === "none") return false;
  const mouthAirway = x >= 4 && x <= 24 && Math.abs(y) <= 10 && z >= -12 && z <= 18;
  const head = ellipsoidContains(x, y, z, [48, 0, -22], [50, 66, 55]) && !mouthAirway;
  const lowerHand = ellipsoidContains(x, y, z, [12, -8, 185], [13, 18, 38]);
  const upperHand = ellipsoidContains(x, y, z, [12, 8, 270], [13, 18, 38]);
  if (head || lowerHand || upperHand) return true;
  return playerBoundary === "full"
    && x <= -20
    && Math.abs(y) <= 22
    && z >= 25
    && z <= 365;
}

function buildMask(activeHole, mode) {
  const mask = new Uint32Array(CELL_COUNT);
  const boreR = SPEC.boreDiameter / 2;
  const outerR = SPEC.outerDiameter / 2;
  const centerX = (NX - 1) / 2;
  const centerY = (NY - 1) / 2;
  const activeIndex = SPEC.holes.findIndex((hole) => hole.name === activeHole.name);
  playerSolidCells = 0;

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

        const playerAtCell = material === 0 && playerBoundaryContains(xMm, yMm, zMm);
        if (playerAtCell) {
          material = 1;
          playerSolidCells += 1;
        }

        if ((material === 0 || playerAtCell) && Math.abs(yMm) <= 4) {
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
  jetAim: vec4<f32>,
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
  let startup = smoothstep(0.0, params.display.w, time);
  let phase0 = sin(171.0 * time + p.y * 1.73 + p.z * 0.39);
  let phase1 = sin(263.0 * time + p.x * 0.91 - p.y * 1.31);
  let phase2 = sin(389.0 * time + p.z * 0.77 + p.y * 2.17);
  let fluctuation = amount * vec3<f32>(phase0 * 0.35, phase1, phase2 * 0.55);
  return startup * speed * normalize(params.jetAim.xyz + fluctuation);
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

const volumeSampleShader = /* wgsl */ `
struct Params {
  dims: vec4<u32>,
  physical0: vec4<f32>,
  physical1: vec4<f32>,
  jet: vec4<f32>,
  view: vec4<u32>,
  display: vec4<f32>,
  jetAim: vec4<f32>,
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
  const raw = new ArrayBuffer(112);
  const u32 = new Uint32Array(raw);
  const f32 = new Float32Array(raw);
  u32.set([NX, NY, NZ, 0], 0);
  f32.set([
    timeStepSeconds(),
    1 / CELL_M,
    simulationParameters.airDensity,
    simulationParameters.soundSpeed ** 2,
  ], 4);
  f32.set([
    simulationParameters.kinematicViscosity,
    simulationParameters.smagorinsky,
    0,
    simulationParameters.spongeRate,
  ], 8);
  f32.set([
    Number(ui.jetSpeed.value),
    Number(ui.turbulence.value) / 100,
    selectedHole.target,
    0,
  ], 12);
  const viewModes = { pressure: 0, speed: 1, vorticity: 2 };
  u32.set([Math.floor(NY / 2), viewModes[ui.field.value], 0, 0], 16);
  f32.set([
    simulationParameters.pressureScale,
    simulationParameters.speedScale,
    simulationParameters.vorticityScale,
    simulationParameters.startupRampUs / 1e6,
  ], 20);
  f32.set([
    simulationParameters.jetDirectionX,
    simulationParameters.jetDirectionY,
    simulationParameters.jetDirectionZ,
    0,
  ], 24);
  return raw;
}

function updateParams() {
  if (!gpu) return;
  const raw = createParamsRaw();
  new Float32Array(raw)[10] = stepCount * timeStepSeconds();
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
  const stateBuffers = Array.from({ length: 2 }, () => device.createBuffer({
    size: requiredBytes,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC,
  }));
  const maskBuffer = device.createBuffer({
    size: CELL_COUNT * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
  });
  const paramsBuffer = device.createBuffer({
    size: 112,
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
  const volumeSampleModule = device.createShaderModule({ code: volumeSampleShader });
  const compilation = await Promise.all([
    computeModule.getCompilationInfo(),
    volumeSampleModule.getCompilationInfo(),
  ]);
  const errors = compilation.flatMap((info) => info.messages.filter((message) => message.type === "error"));
  if (errors.length) throw new Error(errors.map((error) => error.message).join("\n"));

  const computePipeline = device.createComputePipeline({
    layout: "auto",
    compute: { module: computeModule, entryPoint: "main" },
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
    stateBuffers,
    maskBuffer,
    paramsBuffer,
    probeBuffer,
    volumeSampleBytes,
    volumeSampleOutputBuffer,
    volumeSampleReadbackBuffer,
    computePipeline,
    volumeSamplePipeline,
    computeGroups,
    volumeSampleGroups,
    state: 0,
  };
}

function colorVolumeSamples(samples) {
  if (!productionVolume) return;
  const mode = ui.field.value;
  const colors = productionVolume.colors;
  const strengths = productionVolume.strengths;
  let minimum = Number.POSITIVE_INFINITY;
  let maximum = Number.NEGATIVE_INFINITY;
  for (let i = 0; i < strengths.length; i += 1) {
    const scalar = samples[i * 4 + 3];
    minimum = Math.min(minimum, scalar);
    maximum = Math.max(maximum, scalar);
    let strength;
    let negative = false;
    if (mode === "pressure") {
      strength = Math.abs(Math.tanh(scalar / simulationParameters.pressureScale));
      negative = scalar < 0;
    } else if (mode === "speed") {
      strength = Math.min(1, Math.max(0, scalar / simulationParameters.speedScale));
    } else {
      strength = Math.min(1, Math.max(0, scalar / simulationParameters.vorticityScale));
    }
    const fieldStrength = strength;
    strength = fieldStrength < 0.015 ? 0 : strength;
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
  const target = [
    simulationParameters.jetTargetX / 1000,
    simulationParameters.jetTargetY / 1000,
    simulationParameters.jetTargetZ / 1000,
  ];
  const direction = new THREE.Vector3(
    simulationParameters.jetDirectionX,
    simulationParameters.jetDirectionY,
    simulationParameters.jetDirectionZ,
  ).normalize();
  const lateral = new THREE.Vector3(0, 1, 0).cross(direction).normalize();
  let nearest = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (let i = 0; i < volumeSampleLayout.indices.length; i += 1) {
    const offset = i * 3;
    const distance = (volumeSampleLayout.positions[offset] - target[0]) ** 2
      + (volumeSampleLayout.positions[offset + 1] - target[1]) ** 2
      + (volumeSampleLayout.positions[offset + 2] - target[2]) ** 2;
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = i;
    }
  }
  const sampleOffset = nearest * 4;
  const lateralVelocity = samples[sampleOffset] * lateral.x
    + samples[sampleOffset + 1] * lateral.y
    + samples[sampleOffset + 2] * lateral.z;
  const edgePressure = mode === "pressure" ? samples[sampleOffset + 3] : 0;
  const jetSignal = Math.tanh(
    lateralVelocity / Math.max(0.1, Number(ui.jetSpeed.value) * 0.08)
    + edgePressure / simulationParameters.pressureScale,
  );
  jetSignalMinimum = Math.min(jetSignalMinimum, jetSignal);
  jetSignalMaximum = Math.max(jetSignalMaximum, jetSignal);
  const jetVisualSignal = Math.tanh(jetSignal * simulationParameters.jetDeflectionGain);
  jetVisualMinimum = Math.min(jetVisualMinimum, jetVisualSignal);
  jetVisualMaximum = Math.max(jetVisualMaximum, jetVisualSignal);
  updateJetPath(jetVisualSignal);
  productionVolume.points.geometry.attributes.color.needsUpdate = true;
  productionVolume.points.geometry.attributes.strength.needsUpdate = true;
  productionVolume.updates += 1;
  window.__agnuquena3D.updates = productionVolume.updates;
  window.__agnuquena3D.field = mode;
  window.__agnuquena3D.minimum = minimum;
  window.__agnuquena3D.maximum = maximum;
  window.__agnuquena3D.waveSpan = maximum - minimum;
  window.__agnuquena3D.jetSignal = jetSignal;
  window.__agnuquena3D.jetSignalMinimum = jetSignalMinimum;
  window.__agnuquena3D.jetSignalMaximum = jetSignalMaximum;
  window.__agnuquena3D.jetSignalRange = jetSignalMaximum - jetSignalMinimum;
  window.__agnuquena3D.jetVisualSignal = jetVisualSignal;
  window.__agnuquena3D.jetVisualSignalRange = jetVisualMaximum - jetVisualMinimum;
  window.__agnuquena3D.jetTargetDistanceMm = Math.sqrt(nearestDistance) * 1000;
  ui.oscillation.textContent = `${jetSignal >= 0 ? "+" : ""}${jetSignal.toExponential(2)} raw · ${jetVisualSignal.toFixed(2)} visible`;
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
  if (now - lastVolumeSampleAt < 80) return;
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
  jetSignalMinimum = Number.POSITIVE_INFINITY;
  jetSignalMaximum = Number.NEGATIVE_INFINITY;
  jetVisualMinimum = Number.POSITIVE_INFINITY;
  jetVisualMaximum = Number.NEGATIVE_INFINITY;
  updateJetPath(0);
  ui.oscillation.textContent = "waiting for steady jet";
  if (!gpu) return;
  const zeros = new Float32Array(CELL_COUNT * 4);
  for (const buffer of gpu.stateBuffers) gpu.device.queue.writeBuffer(buffer, 0, zeros);
  gpu.state = 0;
  updateParams();
}

function updateVolumeFluidMask() {
  if (!productionVolume || !fallbackMask) return;
  let fluidSamples = 0;
  for (let i = 0; i < volumeSampleLayout.indices.length; i += 1) {
    const fluid = fallbackMask[volumeSampleLayout.indices[i]] === 1 ? 0 : 1;
    productionVolume.fluid[i] = fluid;
    fluidSamples += fluid;
  }
  productionVolume.points.geometry.attributes.fluid.needsUpdate = true;
  window.__agnuquena3D.fluidPointCount = fluidSamples;
}

function uploadMask() {
  fallbackMask = buildMask(selectedHole, boundaryMode);
  updateVolumeFluidMask();
  if (gpu) gpu.device.queue.writeBuffer(gpu.maskBuffer, 0, fallbackMask);
  resetGPU();
  updatePlayerReadout();
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
  gpuWorkPending = true;
  gpu.device.queue.submit([encoder.finish()]);
  gpu.device.queue.onSubmittedWorkDone().then(() => {
    requestVolumeSample();
    gpuWorkPending = false;
  }).catch(() => {
    gpuWorkPending = false;
  });
}

function updateProfile() {
  ui.title.textContent = `${selectedHole.note} · Hole ${selectedHole.name}`;
  ui.target.textContent = `${selectedHole.target.toFixed(2)} Hz`;
  ui.holeDiameter.textContent = `${selectedHole.diameter.toFixed(2)} mm · locked`;
  ui.holePosition.textContent = `${selectedHole.z.toFixed(2)} mm · locked`;
  ui.holeProfile.textContent = `${selectedHole.width.toFixed(2)} mm · ${selectedHole.angle}° · locked`;
}

function updatePlayerReadout() {
  const labels = {
    none: "not included",
    headHands: "head + hands",
    full: "full · local boundary",
  };
  ui.playerMetric.textContent = labels[playerBoundary];
  if (playerBoundary === "none") {
    ui.truth.textContent = "The visible mesh is the assembled, validated production STL. Its triangle surfaces are sampled onto the solver grid and form the solid boundary for pressure and all three velocity components.";
  } else if (playerBoundary === "headHands") {
    ui.truth.textContent = `The production STL remains exact. Anatomical head and hand ellipsoids add ${playerSolidCells.toLocaleString()} rigid player-boundary voxels inside the 1 mm acoustic domain.`;
  } else {
    ui.truth.textContent = `The production STL remains exact. Head, hands, and the torso surface add ${playerSolidCells.toLocaleString()} rigid voxels where the player intersects the local domain; anatomy outside the 48 mm cross-section is visual context, not room-scale CFD.`;
  }
  if (window.__agnuquenaCFD) {
    window.__agnuquenaCFD.playerBoundary = playerBoundary;
    window.__agnuquenaCFD.playerSolidCells = playerSolidCells;
  }
}

function publishSimulationParameters() {
  if (!window.__agnuquenaCFD) return;
  window.__agnuquenaCFD.configuration.timeStepSeconds = timeStepSeconds();
  window.__agnuquenaCFD.configuration.parameters = { ...simulationParameters };
}

function updateParameterOutput(name) {
  const output = ui.parameterOutputs.find((candidate) => candidate.dataset.paramOutput === name);
  if (!output) return;
  const digits = name.startsWith("jetDirection") ? 3 : 1;
  output.value = Number(simulationParameters[name]).toFixed(digits);
}

function applySimulationParameter(input) {
  const name = input.dataset.simParam;
  const minimum = Number(input.min);
  const maximum = Number(input.max);
  const requested = Number(input.value);
  const value = Math.min(maximum, Math.max(minimum, requested));
  if (!Number.isFinite(value)) {
    input.value = String(simulationParameters[name]);
    updateParameterOutput(name);
    return;
  }
  input.value = String(value);
  simulationParameters[name] = value;
  const targetNames = ["jetTargetX", "jetTargetY", "jetTargetZ"];
  const directionNames = ["jetDirectionX", "jetDirectionY", "jetDirectionZ"];
  if (targetNames.includes(name)) {
    targetNames.forEach((field) => {
      simulationParameters[field] = Number(
        ui.parameterInputs.find((candidate) => candidate.dataset.simParam === field).value,
      );
      updateParameterOutput(field);
    });
    const direction = new THREE.Vector3(
      simulationParameters.jetTargetX - JET_ORIGIN_MM[0],
      simulationParameters.jetTargetY - JET_ORIGIN_MM[1],
      simulationParameters.jetTargetZ - JET_ORIGIN_MM[2],
    );
    if (direction.lengthSq() > 1e-8) {
      direction.normalize();
      directionNames.forEach((field, index) => {
        simulationParameters[field] = direction.getComponent(index);
        ui.parameterInputs.find((candidate) => candidate.dataset.simParam === field).value
          = direction.getComponent(index).toFixed(3);
        updateParameterOutput(field);
      });
    }
  } else if (directionNames.includes(name)) {
    directionNames.forEach((field) => {
      simulationParameters[field] = Number(
        ui.parameterInputs.find((candidate) => candidate.dataset.simParam === field).value,
      );
    });
    const direction = new THREE.Vector3(
      simulationParameters.jetDirectionX,
      simulationParameters.jetDirectionY,
      simulationParameters.jetDirectionZ,
    );
    if (direction.lengthSq() > 1e-8) {
      direction.normalize();
      const currentTarget = new THREE.Vector3(
        simulationParameters.jetTargetX,
        simulationParameters.jetTargetY,
        simulationParameters.jetTargetZ,
      );
      const origin = new THREE.Vector3(...JET_ORIGIN_MM);
      const distance = Math.max(1, currentTarget.distanceTo(origin));
      const target = origin.addScaledVector(direction, distance);
      directionNames.forEach((field, index) => {
        simulationParameters[field] = direction.getComponent(index);
        ui.parameterInputs.find((candidate) => candidate.dataset.simParam === field).value
          = direction.getComponent(index).toFixed(3);
        updateParameterOutput(field);
      });
      targetNames.forEach((field, index) => {
        simulationParameters[field] = target.getComponent(index);
        ui.parameterInputs.find((candidate) => candidate.dataset.simParam === field).value
          = target.getComponent(index).toFixed(1);
        updateParameterOutput(field);
      });
    }
  }
  updateParameterOutput(name);
  resetGPU();
  colorVolumeSamples(new Float32Array(volumeSampleLayout.indices.length * 4));
  updateJetReadouts();
  publishSimulationParameters();
}

function updateJetReadouts() {
  const speed = Number(ui.jetSpeed.value);
  ui.jetSpeedValue.value = `${speed.toFixed(1)} m/s`;
  ui.turbulenceValue.value = `${ui.turbulence.value}%`;
  ui.reynolds.textContent = Math.round(
    speed * SPEC.notch.width / 1000 / simulationParameters.kinematicViscosity,
  ).toLocaleString();
  ui.timeStep.textContent = `${(timeStepSeconds() * 1e6).toFixed(3)} µs · derived`;
  updateParams();
}

function updateRunButton() {
  ui.toggle.innerHTML = running
    ? '<span class="play-icon" style="border:0;width:8px;height:10px;background:linear-gradient(90deg,currentColor 0 35%,transparent 35% 65%,currentColor 65%)"></span> Pause CFD'
    : '<span class="play-icon" aria-hidden="true"></span> Run CFD';
}

function selectControlTab(tabName) {
  for (const button of ui.controlTabButtons) {
    const selected = button.dataset.controlTab === tabName;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  }
  for (const panel of ui.controlPanels) {
    panel.hidden = panel.dataset.controlPanel !== tabName;
  }
  document.querySelector(".controls-scroll").scrollTop = 0;
}

function wireControls() {
  for (const button of ui.controlTabButtons) {
    button.addEventListener("click", () => selectControlTab(button.dataset.controlTab));
  }
  ui.note.addEventListener("change", () => {
    selectedHole = SPEC.holes.find((hole) => hole.name === ui.note.value) || SPEC.holes[0];
    updateProfile();
    uploadMask();
  });
  ui.field.addEventListener("change", () => {
    updateParams();
    lastVolumeSampleAt = 0;
    requestVolumeSample();
  });
  ui.playerBoundary.addEventListener("change", () => {
    playerBoundary = ui.playerBoundary.value;
    syncPlayerVisual();
    uploadMask();
  });
  ui.toggle.addEventListener("click", () => {
    if (!gpu) return;
    running = !running;
    updateRunButton();
  });
  ui.reset.addEventListener("click", () => {
    resetGPU();
    colorVolumeSamples(new Float32Array(volumeSampleLayout.indices.length * 4));
  });
  ui.speed.addEventListener("input", () => { ui.speedValue.value = ui.speed.value; });
  ui.jetSpeed.addEventListener("input", updateJetReadouts);
  ui.turbulence.addEventListener("input", updateJetReadouts);
  for (const input of ui.parameterInputs) {
    const eventName = input.type === "range" && input.closest(".vector-slider")
      ? "input"
      : "change";
    input.addEventListener(eventName, () => applySimulationParameter(input));
  }
}

function animate() {
  if (gpu && running) stepGPU(Number(ui.speed.value));
  ui.simTime.textContent = `${(stepCount * timeStepSeconds() * 1000).toFixed(3)} ms`;
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
  updatePlayerReadout();
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
    window.__agnuquenaCFD = {
      readProbe,
      materialStatistics,
      playerBoundary,
      playerSolidCells,
      configuration: {
        grid: [NX, NY, NZ],
        voxelMm: CELL_MM,
        timeStepSeconds: timeStepSeconds(),
        parameters: { ...simulationParameters },
        model: "weakly-compressible Navier-Stokes LES",
        geometrySource: productionMetadata.assembly.file,
        geometrySha256: productionMetadata.assembly.sha256,
        boundarySource: productionMetadata.solver_mask.derivation,
        visualization: "actual 3D field samples plus live near-edge jet deflection",
      },
    };
  } catch (error) {
    console.error(error);
    ui.gpuBadge.className = "status fallback";
    ui.gpuBadge.innerHTML = "<span></span>Static fallback";
    ui.volumeStatus.textContent = "WebGPU unavailable · production STL only";
  }
  animate();
}

start();
