import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { SERVICES } from "./services.js";

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;

// Kľúčové zábery kamery podľa postupu scrollu (0 → 1). Súradnice: x doprava, y hore, z k ulici.
// Garáž: vnútro z ∈ [-3.9, 3.9], vráta v z ≈ 4.16, auto na otočnej plošine v strede, nos k vrátam (+z).
const KEYS = [
  { p: 0.00, pos: [0, 1.15, 14.0], tgt: [0, 2.75, 4.2], fov: 4 },
  { p: 0.30, pos: [0, 1.35, 10.0], tgt: [0, 1.40, 2.5], fov: 0 },
  { p: 0.47, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fov: 0 },
  { p: 0.58, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fov: 0 },
  { p: 0.70, pos: [1.4, 1.55, 4.6], tgt: [0, 0.80, 0.3], fov: 6 },
  { p: 1.00, pos: [3.05, 1.70, 3.5], tgt: [-0.45, 0.60, -0.45], fov: 14 },
];
// na výšku (mobil): kamera ostáva vnútri garáže, auto vidno šikmo zhora
const KEYS_PORTRAIT = [
  KEYS[0], KEYS[1],
  { p: 0.47, pos: [1.9, 2.25, 3.75], tgt: [0, 0.45, 0.35], fov: 0 },
  { p: 0.58, pos: [1.9, 2.25, 3.75], tgt: [0, 0.45, 0.35], fov: 0 },
  { p: 0.70, pos: [2.9, 2.0, 2.7], tgt: [0, 0.5, 0], fov: 0 },
  { p: 1.00, pos: [3.3, 2.05, 2.3], tgt: [-0.3, 0.5, -0.5], fov: 0 },
];
const YAW_END = -1.95;      // ~ -112° → bok + zadná tretina (výfuk) ku kamere
const toThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);   // Blender → three

export async function createScene({ canvas, bubblesEl, onBubble, onProgress, reduced }) {
  // slabšie zariadenia (mobil, málo jadier) → nižšie rozlíšenie a jednoduchšie tiene
  const small = Math.min(screen.width, screen.height) < 820;
  const weak = small || (navigator.hardwareConcurrency || 8) <= 4;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: !weak, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, weak ? 1.25 : 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = weak ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x10141a);
  scene.fog = new THREE.Fog(0x10141a, 18, 48);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.15, 80);

  // prostredie pre odlesky laku
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  // svetlá: interiér (LED panely) + vonkajšie osvetlenie fasády
  scene.add(new THREE.HemisphereLight(0xbfd0e8, 0x20232a, 0.35));
  [[-1.6, 1.3], [1.6, 1.3], [-1.6, -1.3], [1.6, -1.3]].forEach(([x, z]) => {
    const l = new THREE.PointLight(0xfff1de, 6, 10, 2);
    l.position.set(x, 3.0, z);
    scene.add(l);
  });
  const spot = new THREE.SpotLight(0xfff4e6, 55, 12, 0.85, 0.6, 1.6);
  spot.position.set(0.4, 3.1, 0.6);
  spot.target.position.set(0, 0, 0);
  spot.castShadow = true;
  spot.shadow.mapSize.set(weak ? 512 : 1024, weak ? 512 : 1024);
  spot.shadow.bias = -0.0004;
  scene.add(spot, spot.target);
  const sun = new THREE.DirectionalLight(0xdfe8ff, 0.7);
  sun.position.set(-5, 7, 14);
  scene.add(sun);
  const facadeLamp = new THREE.SpotLight(0xffe6c8, 160, 26, 0.95, 0.75, 1.5);
  facadeLamp.position.set(0, 7.0, 13.5);
  facadeLamp.target.position.set(0, 2.4, 4.2);
  scene.add(facadeLamp, facadeLamp.target);

  // model (garáž + auto vymodelované v Blenderi, export GLB)
  const draco = new DRACOLoader().setDecoderPath("vendor/three/jsm/libs/draco/gltf/").setDecoderConfig({ type: "wasm" });
  const gltf = await new GLTFLoader().setDRACOLoader(draco).loadAsync("models/garage.glb?v=10");
  draco.dispose();
  const root = gltf.scene;
  scene.add(root);
  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = false;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => { if (m && "envMapIntensity" in m) m.envMapIntensity = /CarPaint|Glass|Chrome|Rim|Alloy/.test(m.name) ? 1.0 : 0.35; });
    }
  });
  const car = root.getObjectByName("Car");
  car.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  const door = root.getObjectByName("Door");


  // bubliny
  const bubbles = SERVICES.map((s) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "bubble";
    el.setAttribute("aria-label", s.title + " – zobraziť detail");
    el.innerHTML = `<span class="dot">${s.icon}</span><span class="lab">${s.title}</span>`;
    el.addEventListener("click", () => onBubble(s.id));
    bubblesEl.appendChild(el);
    const an = car.getObjectByName("AN_" + s.id);
    return { s, el, a: an ? an.position.clone() : new THREE.Vector3(), n: toThree(s.normal).normalize(), v: 0 };
  });

  // --- stav ---
  let target = reduced ? 1 : 0, cur = target;
  let intro = null;   // časový úvod: {t0, dur, to}
  const setTarget = (p) => { target = reduced ? 1 : clamp(p); };
  const tmpP = new THREE.Vector3(), tmpT = new THREE.Vector3(), w = new THREE.Vector3(), nW = new THREE.Vector3(), q = new THREE.Quaternion();

  let fovAdd = 0, baseFov = 42;
  function pose(p) {
    const KEYS_ = camera.aspect < 0.9 ? KEYS_PORTRAIT : KEYS;
    let i = 0;
    while (i < KEYS_.length - 2 && p > KEYS_[i + 1].p) i++;
    const a = KEYS_[i], b = KEYS_[i + 1];
    const t = smooth(0, 1, clamp((p - a.p) / (b.p - a.p)));
    tmpP.set(lerp(a.pos[0], b.pos[0], t), lerp(a.pos[1], b.pos[1], t), lerp(a.pos[2], b.pos[2], t));
    fovAdd = lerp(a.fov, b.fov, t);
    tmpT.set(lerp(a.tgt[0], b.tgt[0], t), lerp(a.tgt[1], b.tgt[1], t), lerp(a.tgt[2], b.tgt[2], t));
  }

  let W = 0, H = 0;
  function resize() {
    W = canvas.clientWidth; H = canvas.clientHeight;
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    baseFov = camera.aspect < 0.9 ? 58 : camera.aspect < 1.3 ? 50 : 42;
  }

  let last = performance.now(), slow = 0, dpr = Math.min(window.devicePixelRatio || 1, 1.5), lastYaw = null;
  function frame() {
    const now = performance.now(), dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    // plynulé dobiehanie podľa času (nezávislé od FPS)
    if (intro) {
      const t = clamp((now - intro.t0) / intro.dur);
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      cur = target = intro.to * e;
      if (t >= 1) { const done = intro.done; intro = null; done && done(); }
    } else {
      cur += (target - cur) * (reduced ? 1 : 1 - Math.exp(-dt * 7));
      if (Math.abs(target - cur) < 0.0004) cur = target;
    }
    // slabý výkon → nižšie rozlíšenie
    if (dt > 0.045) { if (++slow > 20 && dpr > 1) { dpr = 1; renderer.setPixelRatio(dpr); renderer.setSize(W, H, false); } } else slow = Math.max(0, slow - 1);
    const p = cur;
    // vráta: rolovacie, zbalia sa nahor
    const open = smooth(0.03, 0.27, p);
    door.scale.y = Math.max(0.0015, 1 - open * 0.998);
    door.visible = open < 0.995;
    // otočenie auta predok → bok
    car.rotation.y = YAW_END * smooth(0.58, 0.97, p);
    if (car.rotation.y !== lastYaw) { renderer.shadowMap.needsUpdate = true; lastYaw = car.rotation.y; }

    pose(p);
    // pri úzkych displejoch kameru trochu odsunieme od cieľa
    camera.fov = baseFov + fovAdd * (camera.aspect < 0.9 ? 0.4 : 1);
    camera.updateProjectionMatrix();
    camera.position.copy(tmpP);
    camera.lookAt(tmpT);
    camera.updateMatrixWorld();
    root.updateMatrixWorld(true);

    // bubliny
    car.getWorldQuaternion(q);
    const show = smooth(0.42, 0.54, p);
    const cc = new THREE.Vector3(); car.getWorldPosition(cc); cc.y += 0.6; cc.project(camera);
    const cx = (cc.x * 0.5 + 0.5) * W;
    bubbles.forEach((b, idx) => {
      w.copy(b.a); car.localToWorld(w);
      nW.copy(b.n).applyQuaternion(q);
      const toCam = tmpP.clone().sub(w).normalize();
      const facing = nW.dot(toCam);
      const vis = show * smooth(-0.1, 0.3, facing);
      w.project(camera);
      const inView = w.z < 1 && Math.abs(w.x) < 1.05 && Math.abs(w.y) < 1.05;
      const x = (w.x * 0.5 + 0.5) * W, y = (-w.y * 0.5 + 0.5) * H;
      const op = inView ? vis : 0;
      b.el.style.opacity = op.toFixed(3);
      b.el.style.pointerEvents = op > 0.5 ? "auto" : "none";
      b.el.style.visibility = op < 0.02 ? "hidden" : "visible";
      b.el.style.transform = `translate(${(x - 26).toFixed(1)}px,${(y - 26).toFixed(1)}px)`;
      b.el.style.zIndex = String(1000 - Math.round(w.z * 500));
      b.el.classList.toggle("left", x < cx - 8);
      b.el.tabIndex = op > 0.5 ? 0 : -1;
    });
    onProgress && onProgress(p);
    renderer.render(scene, camera);
  }

  let running = true;
  let loopId = 0;
  const kick = () => { if (!loopId) { last = performance.now(); loopId = requestAnimationFrame(function tick() { loopId = 0; if (running) { frame(); if (target !== cur || intro) loopId = requestAnimationFrame(tick); } }); } };

  resize();
  new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
  // shadery skompilovať vopred → úvodná animácia bez trhania
  try { renderer.shadowMap.needsUpdate = true; await renderer.compileAsync(scene, camera); } catch (e) {}
  frame();
  kick();

  return {
    setProgress: (p) => { if (!intro) { setTarget(p); kick(); } },
    highlight: (id) => bubbles.forEach((b) => b.el.classList.toggle("hot", b.s.id === id)),
    playIntro: (to, dur, done) => { intro = { t0: performance.now(), dur, to, done }; kick(); },
    pause: () => { running = false; },
    resume: () => { running = true; kick(); },
    kick,
  };
}
