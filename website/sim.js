import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/loaders/STLLoader.js";
import { MeshBVH } from "https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.9.5/build/index.module.js";

const MM_TO_M = 0.001;
const DEG = Math.PI / 180;
const MAX_SWEEP_DEG = 180;

const dims = {
  hingeAxis: { x: 0, y: -28.15, z: 14.40 },
  lidClosedZ: 14.55,
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
};

let runningSweep = false;
let manualMode = false;
let targetAngle = 0;
let sweepAngle = 0;
let firstCollision = null;
let lastTime = performance.now();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe8eadf);

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 4);
camera.position.set(0.24, -0.26, 0.16);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.025);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x6f7c82, 2.5));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(0.25, -0.35, 0.45);
scene.add(sun);

const materialBottom = new THREE.MeshStandardMaterial({ color: 0x2f6f99, roughness: 0.64 });
const materialLid = new THREE.MeshStandardMaterial({ color: 0x7fa7b8, roughness: 0.58 });

const bottomMesh = new THREE.Group();
const lidMesh = new THREE.Group();
scene.add(bottomMesh, lidMesh);
let bottomStl;
let lidStl;

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
  const geometry = await loader.loadAsync(path);
  geometry.computeVertexNormals();
  geometry.scale(MM_TO_M, MM_TO_M, MM_TO_M);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

async function buildVisuals() {
  bottomStl = await loadStl("./assets/QuenaCaseBottomViewer.stl", materialBottom);
  bottomStl.geometry.boundsTree = new MeshBVH(bottomStl.geometry);
  bottomMesh.add(bottomStl);

  lidStl = await loadStl("./assets/QuenaCaseLidViewer.stl", materialLid);
  lidStl.geometry.boundsTree = new MeshBVH(lidStl.geometry);
  lidStl.position.copy(lidLocalHinge().multiplyScalar(-1));
  lidMesh.position.copy(hingeWorld());
  lidMesh.add(lidStl);
}

function setLidAngle(angleDeg, worldOffset = new THREE.Vector3()) {
  const angle = THREE.MathUtils.clamp(angleDeg, 0, MAX_SWEEP_DEG) * DEG;
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

function animate(now) {
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
  const contacts = contactCount();
  if (runningSweep && contacts > 0 && firstCollision == null) {
    firstCollision = displayAngle;
  }
  updateUi(displayAngle, contacts);

  controls.update();
  resize();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

function wireControls() {
  ui.play.addEventListener("click", () => {
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
  setLidAngle(0);
  wireControls();
  window.__agnuquenaCase = {
    setAngle(angle) {
      setLidAngle(Number(angle));
      return contactCount();
    },
    runClearanceSelfTest() {
      let firstSweepCollision = null;
      for (let angle = 0; angle <= MAX_SWEEP_DEG; angle += 1) {
        setLidAngle(angle);
        if (contactCount() > 0 && firstSweepCollision == null) {
          firstSweepCollision = angle;
        }
      }
      setLidAngle(0, new THREE.Vector3(0, 0, -0.004));
      const detectorProbeContacts = contactCount();
      setLidAngle(0);
      const result = {
        pass: firstSweepCollision == null && detectorProbeContacts > 0,
        firstSweepCollision,
        detectorProbeContacts,
      };
      document.body.dataset.caseSweepResult = JSON.stringify(result);
      return result;
    },
  };
  if (new URLSearchParams(window.location.search).has("selftest")) {
    window.__agnuquenaCase.runClearanceSelfTest();
  }
  requestAnimationFrame(animate);
}

main().catch((error) => {
  console.error(error);
  ui.sweep.textContent = "failed";
});
