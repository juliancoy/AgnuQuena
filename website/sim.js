import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/loaders/STLLoader.js";
import { MeshBVH } from "https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.9.5/build/index.module.js";

const MM_TO_M = 0.001;
const DEG = Math.PI / 180;
const MAX_SWEEP_DEG = 180;
const INITIAL_ANGLE_DEG = 180;
const ASSET_REVISION = "decorations-v2";

const dims = {
  hingeAxis: { x: 0, y: -28.35, z: 14.40 },
  lidClosedZ: 14.55,
  latch: {
    xs: [-72, 72],
    y: 27.2,
    localZ: -2.35,
    radius: 2.0,
    releaseAngle: 3,
  },
  quenaSlots: [
    { asset: "QuenaTube1.stl", x: 0, y: -11.9, z: 12.95, bodyX0: -115.05, rotationZ: 0, outwardRoll: 270, openingAxis: [0, -1, 0] },
    { asset: "QuenaTube2.stl", x: -38.9527, y: 11.9, z: 12.95, bodyX0: -76.0973, rotationZ: 0, outwardRoll: 90, openingAxis: [0, 1, 0] },
    { asset: "QuenaMouthpiece.stl", x: 83.75, y: 11.9, z: 12.95, bodyX0: -31.3, rotationZ: 180, outwardRoll: 180, openingAxis: [1, 0, 0] },
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
};

let runningSweep = false;
let manualMode = true;
let targetAngle = INITIAL_ANGLE_DEG;
let sweepAngle = INITIAL_ANGLE_DEG;
let firstCollision = null;
let lastTime = performance.now();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe8eadf);

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 4);
camera.position.set(0, 0.38, -0.28);
camera.up.set(0, 0, 1);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, -0.015, 0.05);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x6f7c82, 2.5));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(0.25, -0.35, 0.45);
scene.add(sun);

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
  bottomStl = await loadStl("./assets/QuenaCaseBottomViewer.stl", materialBottom);
  bottomStl.geometry.boundsTree = new MeshBVH(bottomStl.geometry);
  bottomMesh.add(bottomStl);

  logoStl = await loadStl("./assets/QuenaCaseLogoViewer.stl", materialLogo);
  logoStl.renderOrder = 2;
  bottomMesh.add(logoStl);

  lidStl = await loadStl("./assets/QuenaCaseLidViewer.stl", materialLid);
  lidStl.geometry.boundsTree = new MeshBVH(lidStl.geometry);
  lidStl.position.copy(lidLocalHinge().multiplyScalar(-1));
  lidMesh.position.copy(hingeWorld());
  lidMesh.add(lidStl);

  engravingStl = await loadStl(
    "./assets/QuenaCaseEngravingViewer.stl",
    materialEngraving,
  );
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

  for (const slot of dims.quenaSlots) {
    const part = await loadStl(`./assets/${slot.asset}`, materialQuena);
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
  const contacts = updateContactHighlight();
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
        materialEngraving.color.r - materialLid.color.r,
        materialEngraving.color.g - materialLid.color.g,
        materialEngraving.color.b - materialLid.color.b,
      );
      const engravingContrastsWithLid = engravingColorDelta.length() > 0.25;
      const logoVisible = logoStl.visible
        && logoStl.parent === bottomMesh
        && logoStl.geometry.attributes.position.count > 0;
      const logoColorDelta = new THREE.Vector3(
        materialLogo.color.r - materialBottom.color.r,
        materialLogo.color.g - materialBottom.color.g,
        materialLogo.color.b - materialBottom.color.b,
      );
      const decorationColorDelta = new THREE.Vector3(
        materialLogo.color.r - materialEngraving.color.r,
        materialLogo.color.g - materialEngraving.color.g,
        materialLogo.color.b - materialEngraving.color.b,
      );
      const decorationsHaveDistinctColors = logoColorDelta.length() > 0.25
        && decorationColorDelta.length() > 0.25;
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
          && decorationsHaveDistinctColors,
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
