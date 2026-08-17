import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/loaders/STLLoader.js";
import { RoomEnvironment } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/environments/RoomEnvironment.js";
import { MeshBVH } from "https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.9.5/build/index.module.js";

const MM_TO_M = 0.001;
const DEG = Math.PI / 180;
const MAX_SWEEP_DEG = 180;
const INITIAL_ANGLE_DEG = 180;
const ASSET_REVISION = "complete-latch-nubs-v2";

const dims = {
  hingeAxis: { x: 0, y: -28.35, z: 14.40 },
  lidClosedZ: 14.55,
  latch: {
    xs: [-72, 72],
    y: 27.2,
    localZ: -2.35,
    radius: 2.0,
    releaseAngle: 4,
  },
  quenaSlots: [
    { asset: "QuenaTube1.stl", x: 0, y: -11.9, z: 12.95, bodyX0: -120.625, rotationZ: 0, outwardRoll: 270, openingAxis: [0, -1, 0] },
    { asset: "QuenaTube2.stl", x: -46.4027, y: 11.9, z: 12.95, bodyX0: -59.2223, rotationZ: 0, outwardRoll: 90, openingAxis: [0, 1, 0] },
    { asset: "QuenaMouthpiece.stl", x: 89.325, y: 11.9, z: 12.95, bodyX0: -31.3, rotationZ: 180, outwardRoll: 180, openingAxis: [1, 0, 0] },
  ],
};

const ui = {
  angle: document.querySelector("#angle"),
  contacts: document.querySelector("#contacts"),
  sweep: document.querySelector("#sweep"),
  firstCollision: document.querySelector("#firstCollision"),
  slider: document.querySelector("#angleSlider"),
  play: document.querySelector("#play"),
  pause: document.querySelector("#pause"),
  reset: document.querySelector("#reset"),
  meshAppearance: document.querySelector("#meshAppearance"),
};

let runningSweep = false;
let manualMode = true;
let targetAngle = INITIAL_ANGLE_DEG;
let sweepAngle = INITIAL_ANGLE_DEG;
let firstCollision = null;
let lastTime = performance.now();
let animationFrameCount = 0;

const scene = new THREE.Scene();
function updateSceneTheme(theme = document.documentElement.dataset.theme) {
  scene.background = new THREE.Color(theme === "dark" ? 0x091b18 : 0xe8eadf);
}
updateSceneTheme();
window.addEventListener("agnuquena-themechange", (event) => updateSceneTheme(event.detail.theme));

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const environmentGenerator = new THREE.PMREMGenerator(renderer);
const studioRoom = new RoomEnvironment();
scene.environment = environmentGenerator.fromScene(studioRoom, 0.04).texture;
studioRoom.dispose();
environmentGenerator.dispose();

const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 4);
camera.position.set(0, 0.38, -0.28);
camera.up.set(0, 0, 1);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, -0.015, 0.05);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x6f7c82, 1.15));
const sun = new THREE.DirectionalLight(0xfff7e8, 3.2);
sun.position.set(0.25, -0.35, 0.45);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 0.05;
sun.shadow.camera.far = 1.5;
sun.shadow.camera.left = -0.34;
sun.shadow.camera.right = 0.34;
sun.shadow.camera.top = 0.34;
sun.shadow.camera.bottom = -0.34;
sun.shadow.bias = -0.00008;
sun.shadow.normalBias = 0.0015;
sun.target.position.set(0, 0, 0.025);
scene.add(sun, sun.target);

const fill = new THREE.DirectionalLight(0xbfd8ff, 1.1);
fill.position.set(-0.32, 0.2, 0.24);
scene.add(fill);

const shadowCatcher = new THREE.Mesh(
  new THREE.PlaneGeometry(1.2, 1.2),
  new THREE.ShadowMaterial({ color: 0x24302e, opacity: 0.2 }),
);
shadowCatcher.name = "Studio shadow catcher";
shadowCatcher.position.z = -0.002;
shadowCatcher.receiveShadow = true;
scene.add(shadowCatcher);

const materialBottom = new THREE.MeshStandardMaterial({ color: 0x2f6f99, roughness: 0.64 });
const materialLid = new THREE.MeshStandardMaterial({ color: 0x7fa7b8, roughness: 0.58 });
const materialEngraving = new THREE.MeshStandardMaterial({
  color: 0xffdf78,
  roughness: 0.46,
  metalness: 0.02,
});
const materialLogo = new THREE.MeshStandardMaterial({
  color: 0xff6680,
  roughness: 0.42,
  metalness: 0.02,
});
const materialQuena = new THREE.MeshStandardMaterial({
  color: 0xc98b3c,
  roughness: 0.5,
  metalness: 0.03,
});
const meshAppearances = new Map();

function makeMaterial(shader, color) {
  const common = { color: new THREE.Color(color), side: THREE.DoubleSide };
  if (shader === "brushed-metal") {
    return new THREE.MeshPhysicalMaterial({
      ...common,
      metalness: 0.92,
      roughness: 0.3,
      clearcoat: 0.25,
      clearcoatRoughness: 0.22,
      anisotropy: 0.7,
    });
  }
  if (shader === "polished-metal") {
    return new THREE.MeshPhysicalMaterial({
      ...common,
      metalness: 1,
      roughness: 0.06,
      clearcoat: 1,
      clearcoatRoughness: 0.04,
    });
  }
  if (shader === "iridescent") {
    return new THREE.MeshPhysicalMaterial({
      ...common,
      metalness: 0.58,
      roughness: 0.18,
      clearcoat: 1,
      iridescence: 1,
      iridescenceIOR: 1.6,
      iridescenceThicknessRange: [120, 900],
    });
  }
  if (shader === "pearl") {
    return new THREE.MeshPhysicalMaterial({
      ...common,
      metalness: 0.05,
      roughness: 0.24,
      clearcoat: 1,
      sheen: 1,
      sheenColor: new THREE.Color(color).offsetHSL(0.08, 0.1, 0.2),
      iridescence: 0.4,
      iridescenceThicknessRange: [100, 420],
    });
  }
  if (shader === "glass") {
    return new THREE.MeshPhysicalMaterial({
      ...common,
      metalness: 0,
      roughness: 0.08,
      transmission: 0.9,
      thickness: 0.8,
      ior: 1.46,
      transparent: true,
      opacity: 0.68,
      depthWrite: false,
    });
  }
  if (shader === "emissive") {
    return new THREE.MeshStandardMaterial({
      ...common,
      roughness: 0.3,
      emissive: new THREE.Color(color),
      emissiveIntensity: 1.8,
      toneMapped: false,
    });
  }
  if (shader === "xray") {
    return new THREE.MeshBasicMaterial({
      ...common,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
  }
  if (shader === "hologram") {
    return new THREE.ShaderMaterial({
      side: THREE.DoubleSide,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        baseColor: { value: new THREE.Color(color) },
        time: { value: 0 },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vWorldPosition;
        void main() {
          vNormal = normalize(mat3(modelMatrix) * normal);
          vec4 worldPosition = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPosition.xyz;
          gl_Position = projectionMatrix * viewMatrix * worldPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 baseColor;
        uniform float time;
        varying vec3 vNormal;
        varying vec3 vWorldPosition;
        void main() {
          vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
          float fresnel = pow(1.0 - abs(dot(normalize(vNormal), viewDirection)), 2.2);
          float scan = 0.5 + 0.5 * sin(vWorldPosition.z * 420.0 - time * 5.0);
          vec3 rainbow = 0.5 + 0.5 * cos(
            6.28318 * (fresnel + vec3(0.0, 0.33, 0.67) + time * 0.04)
          );
          vec3 glow = mix(baseColor, rainbow, 0.62) * (0.55 + fresnel + scan * 0.22);
          gl_FragColor = vec4(glow, 0.38 + fresnel * 0.52);
        }
      `,
    });
  }
  if (shader === "phong") {
    return new THREE.MeshPhongMaterial({ ...common, shininess: 80 });
  }
  if (shader === "toon") return new THREE.MeshToonMaterial(common);
  if (shader === "normal") return new THREE.MeshNormalMaterial({ side: THREE.DoubleSide });
  if (shader === "wireframe") {
    return new THREE.MeshBasicMaterial({ ...common, wireframe: true });
  }
  return new THREE.MeshStandardMaterial({ ...common, roughness: 0.55, metalness: 0.02 });
}

function registerMeshAppearance(id, label, mesh, color, shader = "standard") {
  meshAppearances.set(id, { id, label, mesh, color, shader });
}

function setMeshAppearance(id, shader, color) {
  const entry = meshAppearances.get(id);
  if (!entry) throw new Error(`Unknown mesh: ${id}`);
  const previous = entry.mesh.material;
  entry.shader = shader;
  entry.color = color;
  entry.mesh.material = makeMaterial(shader, color);
  if (previous && previous !== entry.mesh.material) previous.dispose();
}

function buildAppearanceControls() {
  ui.meshAppearance.replaceChildren();
  for (const entry of meshAppearances.values()) {
    const row = document.createElement("div");
    row.className = "mesh-control";
    row.dataset.mesh = entry.id;
    const label = document.createElement("label");
    label.textContent = entry.label;
    const shader = document.createElement("select");
    shader.setAttribute("aria-label", `${entry.label} shader`);
    for (const [value, text] of [
      ["standard", "Standard"],
      ["brushed-metal", "Brushed metal"],
      ["polished-metal", "Polished metal"],
      ["iridescent", "Iridescent metal"],
      ["pearl", "Pearlescent"],
      ["glass", "Tinted glass"],
      ["emissive", "Neon glow"],
      ["hologram", "Hologram"],
      ["xray", "X-ray"],
      ["phong", "Phong"],
      ["toon", "Toon"],
      ["normal", "Normals"],
      ["wireframe", "Wireframe"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      option.selected = value === entry.shader;
      shader.append(option);
    }
    const color = document.createElement("input");
    color.type = "color";
    color.value = entry.color;
    color.setAttribute("aria-label", `${entry.label} color`);
    const apply = () => setMeshAppearance(entry.id, shader.value, color.value);
    shader.addEventListener("change", apply);
    color.addEventListener("input", apply);
    row.append(label, shader, color);
    ui.meshAppearance.append(row);
  }
}

const bottomMesh = new THREE.Group();
const lidMesh = new THREE.Group();
const quenaMesh = new THREE.Group();
const contactLines = new THREE.LineSegments(
  new THREE.BufferGeometry(),
  new THREE.LineBasicMaterial({
    color: 0xff2600,
    transparent: true,
    opacity: 1,
    depthTest: false,
  }),
);
const contactPoints = new THREE.Points(
  new THREE.BufferGeometry(),
  new THREE.PointsMaterial({
    color: 0xffb000,
    size: 0.008,
    sizeAttenuation: true,
    transparent: true,
    opacity: 1,
    depthTest: false,
    blending: THREE.AdditiveBlending,
  }),
);
contactLines.renderOrder = 20;
contactPoints.renderOrder = 21;
scene.add(bottomMesh, lidMesh, quenaMesh, contactLines, contactPoints);
let bottomStl;
let lidStl;
let engravingStl;
let logoStl;
let latchContactMarkers;
let currentLidAngle = INITIAL_ANGLE_DEG;
const quenaStls = [];

function meters(value) {
  return value * MM_TO_M;
}

function hingeWorld() {
  return new THREE.Vector3(0, meters(dims.hingeAxis.y), meters(dims.hingeAxis.z));
}

function lidLocalHinge() {
  return new THREE.Vector3(
    0,
    meters(dims.hingeAxis.y),
    meters(dims.hingeAxis.z - dims.lidClosedZ),
  );
}

async function loadStl(path, material) {
  const loader = new STLLoader();
  const geometry = await loader.loadAsync(`${path}?v=${ASSET_REVISION}`);
  geometry.computeVertexNormals();
  geometry.scale(MM_TO_M, MM_TO_M, MM_TO_M);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

async function buildVisuals() {
  bottomStl = await loadStl("./assets/QuenaCaseBottom.stl", materialBottom);
  registerMeshAppearance("case-bottom", "Case bottom", bottomStl, "#2f6f99");
  bottomStl.geometry.boundsTree = new MeshBVH(bottomStl.geometry);
  bottomMesh.add(bottomStl);

  logoStl = await loadStl("./assets/QuenaCaseLogo.stl", materialLogo);
  registerMeshAppearance("case-logo", "Bottom logo", logoStl, "#ff6680");
  logoStl.renderOrder = 2;
  bottomMesh.add(logoStl);

  lidStl = await loadStl("./assets/QuenaCaseLid.stl", materialLid);
  registerMeshAppearance("case-lid", "Case lid", lidStl, "#7fa7b8");
  lidStl.geometry.boundsTree = new MeshBVH(lidStl.geometry);
  lidStl.position.copy(lidLocalHinge().multiplyScalar(-1));
  lidMesh.position.copy(hingeWorld());
  lidMesh.add(lidStl);

  engravingStl = await loadStl(
    "./assets/QuenaCaseEngraving.stl",
    materialEngraving,
  );
  registerMeshAppearance("case-engraving", "Lid engraving", engravingStl, "#ffdf78");
  engravingStl.position.copy(lidStl.position);
  engravingStl.renderOrder = 2;
  lidMesh.add(engravingStl);

  latchContactMarkers = new THREE.Group();
  const latchGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xff3200,
    transparent: true,
    opacity: 0.72,
    depthTest: false,
    blending: THREE.AdditiveBlending,
  });
  for (const x of dims.latch.xs) {
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(meters(dims.latch.radius * 1.08), 24, 16),
      latchGlowMaterial,
    );
    marker.position.set(meters(x), meters(dims.latch.y), meters(dims.latch.localZ));
    marker.renderOrder = 22;
    latchContactMarkers.add(marker);
  }
  latchContactMarkers.visible = false;
  lidStl.add(latchContactMarkers);

  for (const [index, slot] of dims.quenaSlots.entries()) {
    const part = await loadStl(`./assets/${slot.asset}`, materialQuena.clone());
    registerMeshAppearance(
      `quena-${index + 1}`,
      slot.asset.replace(".stl", ""),
      part,
      "#c98b3c",
    );
    part.rotation.set(0, 90 * DEG, slot.rotationZ * DEG, "ZXY");
    part.rotateOnAxis(new THREE.Vector3(0, 0, 1), slot.outwardRoll * DEG);
    part.userData.openingAxis = slot.openingAxis;
    part.position.set(
      meters(slot.x + Math.cos(slot.rotationZ * DEG) * slot.bodyX0),
      meters(slot.y + Math.sin(slot.rotationZ * DEG) * slot.bodyX0),
      meters(slot.z),
    );
    quenaMesh.add(part);
    quenaStls.push(part);
  }

  scene.updateMatrixWorld(true);
  buildAppearanceControls();
}

function setLidAngle(angleDeg, worldOffset = new THREE.Vector3()) {
  currentLidAngle = THREE.MathUtils.clamp(angleDeg, 0, MAX_SWEEP_DEG);
  const angle = currentLidAngle * DEG;
  const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), angle);
  const position = hingeWorld().add(worldOffset);
  lidMesh.position.copy(position);
  lidMesh.quaternion.copy(q);
  lidStl.updateWorldMatrix(true, false);
}

function contactCount() {
  return bottomStl.geometry.boundsTree.intersectsGeometry(
    lidStl.geometry,
    lidStl.matrixWorld,
  ) ? 1 : 0;
}

function updateContactHighlight(hasContact = contactCount() > 0) {
  const segments = [];
  const points = [];
  const intersection = new THREE.Line3();
  const maxSegments = 128;
  const latchEngaged = currentLidAngle < dims.latch.releaseAngle;
  // At closure the broad mating faces are intentionally coplanar. Show the
  // two interference-fit nubs there, not harmless face-to-face contact.
  if (hasContact && !latchEngaged) {
    bottomStl.geometry.boundsTree.bvhcast(
      lidStl.geometry.boundsTree,
      lidStl.matrixWorld,
      {
        intersectsTriangles(bottomTriangle, lidTriangle) {
          if (!bottomTriangle.intersectsTriangle(lidTriangle, intersection, true)) {
            return false;
          }
          const start = intersection.start;
          const end = intersection.end;
          // Coplanar pairs have no representable intersection edge and the
          // library reports their target segment at the origin. The visible
          // highlight is reserved for actual crossing/contact segments.
          if (start.lengthSq() === 0 && end.lengthSq() === 0) return false;
          segments.push(start.x, start.y, start.z, end.x, end.y, end.z);
          points.push(
            (start.x + end.x) / 2,
            (start.y + end.y) / 2,
            (start.z + end.z) / 2,
          );
          return points.length / 3 >= maxSegments;
        },
      },
    );
  }
  contactLines.geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(segments, 3),
  );
  contactPoints.geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(points, 3),
  );
  contactLines.visible = segments.length > 0;
  contactPoints.visible = points.length > 0;
  if (latchContactMarkers) latchContactMarkers.visible = latchEngaged;
  return points.length / 3 + (latchEngaged ? dims.latch.xs.length : 0);
}

function updateUi(angleDeg, contacts) {
  ui.angle.textContent = `${angleDeg.toFixed(1)} deg`;
  ui.contacts.textContent = String(contacts);
  ui.sweep.textContent = runningSweep ? "running" : "paused";
  ui.firstCollision.textContent = firstCollision == null ? "none" : `${firstCollision.toFixed(1)} deg`;
  ui.slider.value = String(Math.round(angleDeg));
}

function resize() {
  const { clientWidth, clientHeight } = renderer.domElement;
  if (renderer.domElement.width !== clientWidth || renderer.domElement.height !== clientHeight) {
    renderer.setSize(clientWidth, clientHeight, false);
    camera.aspect = clientWidth / Math.max(clientHeight, 1);
    camera.updateProjectionMatrix();
  }
}

function animate(now, scheduleNext = true) {
  const dt = Math.min((now - lastTime) / 1000, 0.05);
  lastTime = now;

  let displayAngle = manualMode ? targetAngle : sweepAngle;
  if (runningSweep && !manualMode) {
    sweepAngle += 35 * dt;
    if (sweepAngle >= MAX_SWEEP_DEG) {
      sweepAngle = MAX_SWEEP_DEG;
      runningSweep = false;
    }
    displayAngle = sweepAngle;
  }

  setLidAngle(displayAngle);
  const contacts = updateContactHighlight();
  if (runningSweep && contacts > 0 && firstCollision == null) {
    firstCollision = displayAngle;
  }
  updateUi(displayAngle, contacts);

  for (const entry of meshAppearances.values()) {
    if (entry.mesh.material.uniforms?.time) {
      entry.mesh.material.uniforms.time.value = now / 1000;
    }
  }

  controls.update();
  resize();
  renderer.render(scene, camera);
  animationFrameCount += 1;
  if (scheduleNext) requestAnimationFrame(animate);
}

function wireControls() {
  ui.play.addEventListener("click", () => {
    if (manualMode) sweepAngle = 0;
    manualMode = false;
    runningSweep = true;
    firstCollision = null;
    if (sweepAngle >= MAX_SWEEP_DEG) sweepAngle = 0;
    setLidAngle(sweepAngle);
  });
  ui.pause.addEventListener("click", () => {
    runningSweep = false;
  });
  ui.reset.addEventListener("click", () => {
    runningSweep = false;
    manualMode = false;
    sweepAngle = 0;
    targetAngle = 0;
    firstCollision = null;
    setLidAngle(0);
  });
  ui.slider.addEventListener("input", () => {
    manualMode = true;
    runningSweep = false;
    targetAngle = Number(ui.slider.value);
    setLidAngle(targetAngle);
  });
}

async function main() {
  await buildVisuals();
  const query = new URLSearchParams(window.location.search);
  const requestedAngle = Number(query.get("angle"));
  if (Number.isFinite(requestedAngle) && query.has("angle")) {
    targetAngle = THREE.MathUtils.clamp(requestedAngle, 0, MAX_SWEEP_DEG);
  }
  setLidAngle(targetAngle);
  wireControls();
  window.__agnuquenaCase = {
    getViewState() {
      return {
        animationFrameCount,
        cameraPosition: camera.position.toArray(),
        currentLidAngle,
        runningSweep,
      };
    },
    setAngle(angle) {
      setLidAngle(Number(angle));
      return updateContactHighlight();
    },
    runClearanceSelfTest() {
      let closedLatchContact = false;
      let latchReleaseAngle = null;
      let firstSurfaceContactAfterRelease = null;
      for (let angle = 0; angle <= MAX_SWEEP_DEG; angle += 1) {
        setLidAngle(angle);
        const contacts = contactCount();
        const latchEngaged = angle < dims.latch.releaseAngle;
        if (angle === 0) closedLatchContact = latchEngaged;
        if (closedLatchContact && latchReleaseAngle == null && !latchEngaged) {
          latchReleaseAngle = angle;
        } else if (latchReleaseAngle != null && contacts > 0
          && firstSurfaceContactAfterRelease == null) {
          firstSurfaceContactAfterRelease = angle;
        }
      }
      setLidAngle(0, new THREE.Vector3(0, 0, -0.004));
      const detectorProbeContacts = contactCount();
      setLidAngle(0);
      const closedHighlightPoints = updateContactHighlight();
      setLidAngle(latchReleaseAngle ?? 1);
      const releasedHighlightPoints = updateContactHighlight();
      scene.updateMatrixWorld(true);
      const bottomBounds = new THREE.Box3().setFromObject(bottomStl);
      const planTolerance = meters(0.1);
      const quenaWithinCasePlan = quenaStls.every((part) => {
        const bounds = new THREE.Box3().setFromObject(part);
        return bounds.min.x >= bottomBounds.min.x - planTolerance
          && bounds.max.x <= bottomBounds.max.x + planTolerance
          && bounds.min.y >= bottomBounds.min.y - planTolerance
          && bounds.max.y <= bottomBounds.max.y + planTolerance;
      });
      const quenaHolesFaceOutward = quenaStls.every((part) => {
        const holeDirection = new THREE.Vector3(...part.userData.openingAxis)
          .applyQuaternion(part.quaternion);
        return holeDirection.z > 0.99;
      });
      const engravingVisible = engravingStl.visible
        && engravingStl.parent === lidMesh
        && engravingStl.geometry.attributes.position.count > 0;
      const engravingColorDelta = new THREE.Vector3(
        engravingStl.material.color.r - lidStl.material.color.r,
        engravingStl.material.color.g - lidStl.material.color.g,
        engravingStl.material.color.b - lidStl.material.color.b,
      );
      const engravingContrastsWithLid = engravingColorDelta.length() > 0.25;
      const logoVisible = logoStl.visible
        && logoStl.parent === bottomMesh
        && logoStl.geometry.attributes.position.count > 0;
      const logoColorDelta = new THREE.Vector3(
        logoStl.material.color.r - bottomStl.material.color.r,
        logoStl.material.color.g - bottomStl.material.color.g,
        logoStl.material.color.b - bottomStl.material.color.b,
      );
      const decorationColorDelta = new THREE.Vector3(
        logoStl.material.color.r - engravingStl.material.color.r,
        logoStl.material.color.g - engravingStl.material.color.g,
        logoStl.material.color.b - engravingStl.material.color.b,
      );
      const decorationsHaveDistinctColors = logoColorDelta.length() > 0.25
        && decorationColorDelta.length() > 0.25;
      const appearanceControlCount = ui.meshAppearance.querySelectorAll(
        ".mesh-control",
      ).length;
      const originalBottomShader = meshAppearances.get("case-bottom").shader;
      const originalBottomColor = meshAppearances.get("case-bottom").color;
      setMeshAppearance("case-bottom", "brushed-metal", "#123456");
      const metalSelectionWorks = bottomStl.material.type === "MeshPhysicalMaterial"
        && bottomStl.material.metalness === 0.92
        && bottomStl.material.color.getHexString() === "123456";
      setMeshAppearance("case-bottom", "hologram", "#654321");
      renderer.compile(scene, camera);
      const funSelectionWorks = bottomStl.material.type === "ShaderMaterial"
        && bottomStl.material.uniforms.baseColor.value.getHexString() === "654321";
      const appearanceSelectionWorks = metalSelectionWorks && funSelectionWorks;
      const studioLightingConfigured = scene.environment?.isTexture === true
        && renderer.toneMapping === THREE.ACESFilmicToneMapping
        && renderer.shadowMap.enabled
        && sun.castShadow;
      const studioSurfaceConfigured = shadowCatcher.parent === scene
        && shadowCatcher.material.type === "ShadowMaterial"
        && shadowCatcher.material.transparent
        && shadowCatcher.receiveShadow;
      ui.play.click();
      const sweepControlsWork = runningSweep
        && !manualMode
        && sweepAngle === 0
        && currentLidAngle === 0;
      ui.pause.click();
      const pauseControlWorks = !runningSweep;
      const framesBeforeProbe = animationFrameCount;
      animate(performance.now() + 16, false);
      const animationLoopAdvanced = animationFrameCount === framesBeforeProbe + 1;
      setMeshAppearance("case-bottom", originalBottomShader, originalBottomColor);
      const result = {
        pass: closedLatchContact
          && latchReleaseAngle != null
          && closedHighlightPoints > 0
          && releasedHighlightPoints === 0
          && detectorProbeContacts > 0
          && quenaWithinCasePlan
          && quenaHolesFaceOutward
          && engravingVisible
          && engravingContrastsWithLid
          && logoVisible
          && decorationsHaveDistinctColors
          && appearanceControlCount === meshAppearances.size
          && appearanceSelectionWorks
          && studioLightingConfigured
          && studioSurfaceConfigured
          && sweepControlsWork
          && pauseControlWorks
          && animationLoopAdvanced,
        closedLatchContact,
        latchReleaseAngle,
        firstSurfaceContactAfterRelease,
        closedHighlightPoints,
        releasedHighlightPoints,
        detectorProbeContacts,
        quenaWithinCasePlan,
        quenaHolesFaceOutward,
        engravingVisible,
        engravingContrastsWithLid,
        logoVisible,
        decorationsHaveDistinctColors,
        appearanceControlCount,
        appearanceSelectionWorks,
        studioLightingConfigured,
        studioSurfaceConfigured,
        sweepControlsWork,
        pauseControlWorks,
        animationLoopAdvanced,
      };
      document.body.dataset.caseSweepResult = JSON.stringify(result);
      setLidAngle(0);
      updateContactHighlight();
      return result;
    },
  };
  if (query.has("selftest")) {
    window.__agnuquenaCase.runClearanceSelfTest();
  }
  requestAnimationFrame(animate);
}

main().catch((error) => {
  console.error(error);
  ui.sweep.textContent = "failed";
});
