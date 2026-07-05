import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/loaders/STLLoader.js";

const MM_TO_M = 0.001;
const DEG = Math.PI / 180;

const dims = {
  bottom: { x: 257.6, bodyY: 63.4, overallY: 74.0, bodyZ: 19.15 },
  lid: { x: 257.6, bodyY: 63.4, overallY: 74.0, bodyZ: 17.55 },
  hingeAxis: { x: 0, y: -36.0, z: 17.95 },
  lidClosedZ: 16.75,
  hingeOuterD: 6.2,
  hingeSpan: 227.6,
  pull: { x: 48, y: 3.6, z: 2.2, cy: 33.1 },
  latchClip: { bridgeY: 36.25, bottomZ: 11.95 },
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

let AmmoLib;
let world;
let bottomBody;
let lidBody;
let caseHinge;
let transform;
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
const materialPin = new THREE.MeshStandardMaterial({ color: 0xc9ced0, metalness: 0.45, roughness: 0.34 });
const materialLatch = new THREE.MeshStandardMaterial({ color: 0x263b45, roughness: 0.7 });

const bottomMesh = new THREE.Group();
const lidMesh = new THREE.Group();
scene.add(bottomMesh, lidMesh);
let latchMesh;

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

function ammoVector(v) {
  return new AmmoLib.btVector3(v.x, v.y, v.z);
}

function ammoQuat(q) {
  return new AmmoLib.btQuaternion(q.x, q.y, q.z, q.w);
}

function makeTransform(position, quaternion = new THREE.Quaternion()) {
  const t = new AmmoLib.btTransform();
  t.setIdentity();
  t.setOrigin(ammoVector(position));
  t.setRotation(ammoQuat(quaternion));
  return t;
}

function makeAmmoBox(size) {
  return new AmmoLib.btBoxShape(new AmmoLib.btVector3(
    meters(size.x / 2),
    meters(size.y / 2),
    meters(size.z / 2),
  ));
}

function addCompoundBox(compound, size, position, quaternion = new THREE.Quaternion()) {
  compound.addChildShape(makeTransform(position, quaternion), makeAmmoBox(size));
}

function createRigidBody(shape, mass, position, quaternion = new THREE.Quaternion()) {
  const startTransform = makeTransform(position, quaternion);
  const localInertia = new AmmoLib.btVector3(0, 0, 0);
  if (mass > 0) shape.calculateLocalInertia(mass, localInertia);

  const motionState = new AmmoLib.btDefaultMotionState(startTransform);
  const rbInfo = new AmmoLib.btRigidBodyConstructionInfo(mass, motionState, shape, localInertia);
  const body = new AmmoLib.btRigidBody(rbInfo);
  body.setActivationState(4);
  world.addRigidBody(body);
  return body;
}

function createCompoundBody(children, mass, position = new THREE.Vector3()) {
  const compound = new AmmoLib.btCompoundShape();
  for (const child of children) {
    addCompoundBox(
      compound,
      child.size,
      new THREE.Vector3(meters(child.x || 0), meters(child.y || 0), meters(child.z || 0)),
      child.quaternion || new THREE.Quaternion(),
    );
  }
  return createRigidBody(compound, mass, position);
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
  const bottomStl = await loadStl("./assets/QuenaCaseBottom.stl", materialBottom);
  bottomMesh.add(bottomStl);

  const lidStl = await loadStl("./assets/QuenaCaseLid.stl", materialLid);
  lidStl.position.copy(lidLocalHinge().multiplyScalar(-1));
  lidMesh.position.copy(hingeWorld());
  lidMesh.add(lidStl);

  const pinStl = await loadStl("./assets/QuenaCasePin.stl", materialPin);
  pinStl.position.set(0, meters(dims.hingeAxis.y), meters(dims.hingeAxis.z - 0.875));
  scene.add(pinStl);

  latchMesh = await loadStl("./assets/QuenaCaseLatch.stl", materialLatch);
  latchMesh.position.set(0, meters(dims.latchClip.bridgeY), meters(dims.latchClip.bottomZ));
  scene.add(latchMesh);
}

function initPhysics() {
  const collisionConfig = new AmmoLib.btDefaultCollisionConfiguration();
  const dispatcher = new AmmoLib.btCollisionDispatcher(collisionConfig);
  const broadphase = new AmmoLib.btDbvtBroadphase();
  const solver = new AmmoLib.btSequentialImpulseConstraintSolver();
  world = new AmmoLib.btDiscreteDynamicsWorld(dispatcher, broadphase, solver, collisionConfig);
  world.setGravity(new AmmoLib.btVector3(0, 0, -9.81));
  transform = new AmmoLib.btTransform();

  bottomBody = createCompoundBody([
    { size: { x: dims.bottom.x, y: dims.bottom.bodyY, z: 2.8 }, z: 1.4 },
    { size: { x: dims.bottom.x, y: 3, z: 14.0 }, y: -dims.bottom.bodyY / 2 + 1.5, z: 7.0 },
    { size: { x: dims.bottom.x, y: 3, z: 14.0 }, y: dims.bottom.bodyY / 2 - 1.5, z: 7.0 },
    { size: { x: 3, y: dims.bottom.bodyY, z: 14.0 }, x: -dims.bottom.x / 2 + 1.5, z: 7.0 },
    { size: { x: 3, y: dims.bottom.bodyY, z: 14.0 }, x: dims.bottom.x / 2 - 1.5, z: 7.0 },
    { size: { x: dims.hingeSpan, y: dims.hingeOuterD, z: dims.hingeOuterD }, y: dims.hingeAxis.y, z: dims.hingeAxis.z },
    { size: { x: dims.pull.x, y: dims.pull.y, z: dims.pull.z }, y: dims.pull.cy, z: 15.4 },
  ], 0);

  lidBody = createCompoundBody([
    {
      size: { x: dims.lid.x, y: dims.lid.bodyY, z: 2.8 },
      y: -dims.hingeAxis.y,
      z: dims.lidClosedZ + dims.lid.bodyZ - 1.4 - dims.hingeAxis.z,
    },
    { size: { x: dims.lid.x, y: 3, z: 10.5 }, y: -dims.hingeAxis.y - dims.lid.bodyY / 2 + 1.5, z: dims.lidClosedZ + 6.0 - dims.hingeAxis.z },
    { size: { x: dims.lid.x, y: 3, z: 10.5 }, y: -dims.hingeAxis.y + dims.lid.bodyY / 2 - 1.5, z: dims.lidClosedZ + 6.0 - dims.hingeAxis.z },
    { size: { x: 3, y: dims.lid.bodyY, z: 10.5 }, x: -dims.lid.x / 2 + 1.5, y: -dims.hingeAxis.y, z: dims.lidClosedZ + 6.0 - dims.hingeAxis.z },
    { size: { x: 3, y: dims.lid.bodyY, z: 10.5 }, x: dims.lid.x / 2 - 1.5, y: -dims.hingeAxis.y, z: dims.lidClosedZ + 6.0 - dims.hingeAxis.z },
    { size: { x: dims.hingeSpan / 3, y: dims.hingeOuterD, z: dims.hingeOuterD }, y: 0, z: 0 },
    { size: { x: dims.pull.x, y: dims.pull.y, z: dims.pull.z }, y: dims.pull.cy - dims.hingeAxis.y, z: dims.lidClosedZ + 3.3 - dims.hingeAxis.z },
  ], 0.22, hingeWorld());

  caseHinge = new AmmoLib.btHingeConstraint(
    bottomBody,
    lidBody,
    new AmmoLib.btVector3(0, meters(dims.hingeAxis.y), meters(dims.hingeAxis.z)),
    new AmmoLib.btVector3(0, 0, 0),
    new AmmoLib.btVector3(1, 0, 0),
    new AmmoLib.btVector3(1, 0, 0),
    true,
  );
  caseHinge.setLimit(0, 135 * DEG, 0.9, 0.3, 1.0);
  world.addConstraint(caseHinge, true);
}

function setBodyTransform(body, position, quaternion) {
  const t = makeTransform(position, quaternion);
  body.setWorldTransform(t);
  body.getMotionState().setWorldTransform(t);
  body.setLinearVelocity(new AmmoLib.btVector3(0, 0, 0));
  body.setAngularVelocity(new AmmoLib.btVector3(0, 0, 0));
}

function setLidAngle(angleDeg) {
  const angle = THREE.MathUtils.clamp(angleDeg, 0, 135) * DEG;
  const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), angle);
  setBodyTransform(lidBody, hingeWorld(), q);
  caseHinge.enableAngularMotor(false, 0, 0);
  lidMesh.position.copy(hingeWorld());
  lidMesh.quaternion.copy(q);
  if (latchMesh) {
    latchMesh.visible = angle < 3 * DEG;
  }
}

function syncBodyToMesh(body, mesh) {
  const motionState = body.getMotionState();
  if (!motionState) return;
  motionState.getWorldTransform(transform);
  const origin = transform.getOrigin();
  const rotation = transform.getRotation();
  mesh.position.set(origin.x(), origin.y(), origin.z());
  mesh.quaternion.set(rotation.x(), rotation.y(), rotation.z(), rotation.w());
}

function bodyQuaternion(body) {
  const motionState = body.getMotionState();
  if (!motionState) return new THREE.Quaternion();
  motionState.getWorldTransform(transform);
  const rotation = transform.getRotation();
  return new THREE.Quaternion(rotation.x(), rotation.y(), rotation.z(), rotation.w());
}

function contactCount() {
  if (typeof world.performDiscreteCollisionDetection === "function") {
    world.performDiscreteCollisionDetection();
  }
  const dispatcher = world.getDispatcher();
  let count = 0;
  for (let i = 0; i < dispatcher.getNumManifolds(); i += 1) {
    const manifold = dispatcher.getManifoldByIndexInternal(i);
    for (let j = 0; j < manifold.getNumContacts(); j += 1) {
      const point = manifold.getContactPoint(j);
      if (point.getDistance() < -0.0004) count += 1;
    }
  }
  return count;
}

function lidAngleDeg() {
  const q = bodyQuaternion(lidBody);
  return THREE.MathUtils.radToDeg(new THREE.Euler().setFromQuaternion(q, "XYZ").x);
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
    if (sweepAngle >= 135) {
      sweepAngle = 135;
      runningSweep = false;
    }
    displayAngle = sweepAngle;
  }

  setLidAngle(displayAngle);
  world.stepSimulation(dt, 8);
  syncBodyToMesh(lidBody, lidMesh);

  const contacts = contactCount();
  if (runningSweep && contacts > 0 && firstCollision == null) {
    firstCollision = displayAngle;
  }
  updateUi(Number.isFinite(lidAngleDeg()) ? displayAngle : 0, contacts);

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
    if (sweepAngle >= 135) sweepAngle = 0;
    setLidAngle(sweepAngle);
  });
  ui.pause.addEventListener("click", () => {
    runningSweep = false;
    caseHinge.enableAngularMotor(false, 0, 0);
  });
  ui.reset.addEventListener("click", () => {
    runningSweep = false;
    manualMode = false;
    sweepAngle = 0;
    targetAngle = 0;
    firstCollision = null;
    caseHinge.enableAngularMotor(false, 0, 0);
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
  AmmoLib = typeof window.Ammo === "function" ? await window.Ammo() : window.Ammo;
  initPhysics();
  await buildVisuals();
  setLidAngle(0);
  wireControls();
  requestAnimationFrame(animate);
}

main().catch((error) => {
  console.error(error);
  ui.sweep.textContent = "failed";
});
