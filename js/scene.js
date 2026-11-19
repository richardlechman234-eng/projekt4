import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { SERVICES } from "./services.js";

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;

// Kľúčové zábery kamery podľa postupu scrollu (0 → 1). Súradnice: x doprava, y hore, z k ulici.
// Garáž: vnútro z ∈ [-3.9, 3.9], vráta v z ≈ 4.16, auto na otočnej plošine v strede, nos k vrátam (+z).
const KEYS = [
  { p: 0.00, pos: [0, 1.50, 15.5], tgt: [0, 1.60, 4.2], fov: 0 },
  { p: 0.30, pos: [0, 1.45, 11.5], tgt: [0, 1.10, 2.5], fov: 0 },
  { p: 0.47, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fov: 0 },
  { p: 0.58, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fov: 0 },
  { p: 0.70, pos: [1.4, 1.55, 4.6], tgt: [0, 0.80, 0.3], fov: 6 },
  { p: 1.00, pos: [3.05, 1.70, 3.5], tgt: [-0.45, 0.60, -0.45], fov: 14 },
];
const YAW_END = -1.95;      // ~ -112° → bok + zadná tretina (výfuk) ku kamere
const toThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);   // Blender → three

export async function createScene({ canvas, bubblesEl, onBubble, onProgress, reduced }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x10141a);
  scene.fog = new THREE.Fog(0x10141a, 18, 48);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80);

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
  spot.shadow.mapSize.set(1024, 1024);
  spot.shadow.bias = -0.0004;
  scene.add(spot, spot.target);
  const sun = new THREE.DirectionalLight(0xdfe8ff, 0.7);
  sun.position.set(-5, 7, 14);
  scene.add(sun);
  const facadeLamp = new THREE.SpotLight(0xffe6c8, 70, 20, 0.7, 0.8, 1.6);
  facadeLamp.position.set(2.5, 5.0, 11.0);
  facadeLamp.target.position.set(0, 1.6, 4.2);
  scene.add(facadeLamp, facadeLamp.target);

  // model (garáž + auto vymodelované v Blenderi, export GLB)
  const gltf = await new GLTFLoader().loadAsync("models/garage.glb?v=5");
  const root = gltf.scene;
  scene.add(root);
  root.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = false;
      o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => { if (m && "envMapIntensity" in m) m.envMapIntensity = /CarPaint|Glass|Chrome|Rim/.test(m.name) ? 1.0 : 0.35; });
    }
  });
  const car = root.getObjectByName("Car");
  car.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  const door = root.getObjectByName("Door");

  // logo na vrátach (canvas textúra)
  try { await Promise.all([document.fonts.load('800 120px "Barlow Condensed"'), document.fonts.load('600 40px "Barlow"')]); } catch (e) {}
  const logo = makeLogo();
  door.add(logo);

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
  const setTarget = (p) => { target = reduced ? 1 : clamp(p); };
  const tmpP = new THREE.Vector3(), tmpT = new THREE.Vector3(), w = new THREE.Vector3(), nW = new THREE.Vector3(), q = new THREE.Quaternion();

  let fovAdd = 0, baseFov = 42;
  function pose(p) {
    let i = 0;
    while (i < KEYS.length - 2 && p > KEYS[i + 1].p) i++;
    const a = KEYS[i], b = KEYS[i + 1];
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
    cur += (target - cur) * (reduced ? 1 : 1 - Math.exp(-dt * 7));
    if (Math.abs(target - cur) < 0.0004) cur = target;
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
    if (camera.aspect < 0.9 && p > 0.5) {
      tmpP.sub(tmpT).multiplyScalar(1.35).add(tmpT);
      tmpP.y += 0.25;
    }
    camera.fov = baseFov + fovAdd * (camera.aspect < 0.9 ? 0.4 : 1);
    camera.updateProjectionMatrix();
    camera.position.copy(tmpP);
    camera.lookAt(tmpT);
    camera.updateMatrixWorld();
    root.updateMatrixWorld(true);

    // bubliny
    car.getWorldQuaternion(q);
    const show = smooth(0.42, 0.54, p);
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
      b.el.classList.toggle("left", x > W * 0.6);
      b.el.tabIndex = op > 0.5 ? 0 : -1;
    });
    onProgress && onProgress(p);
    renderer.render(scene, camera);
  }

  let running = true;
  let loopId = 0;
  const kick = () => { if (!loopId) { last = performance.now(); loopId = requestAnimationFrame(function tick() { loopId = 0; if (running) { frame(); if (target !== cur) loopId = requestAnimationFrame(tick); } }); } };

  resize();
  new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
  frame();
  kick();

  return {
    setProgress: (p) => { setTarget(p); kick(); },
    pause: () => { running = false; },
    resume: () => { running = true; kick(); },
    kick,
  };
}

function makeLogo() {
  const c = document.createElement("canvas");
  c.width = 2048; c.height = 1024;
  const g = c.getContext("2d");
  // oranžový štvorec s "P"
  const s = 330, x0 = 150, y0 = 200;
  g.fillStyle = "#ff5a1f"; g.fillRect(x0, y0, s, s);
  g.fillStyle = "#121212"; g.font = '800 300px "Barlow Condensed", Impact, sans-serif'; g.textAlign = "center"; g.textBaseline = "alphabetic";
  g.fillText("P", x0 + s / 2, y0 + s * 0.8);
  g.textAlign = "left";
  g.fillStyle = "#ffffff"; g.font = '800 330px "Barlow Condensed", Impact, sans-serif';
  g.fillText("PLS GROUP", x0 + s + 60, y0 + 270);
  g.fillStyle = "#ff5a1f"; g.fillRect(x0 + s + 64, y0 + 306, 1380, 12);
  g.fillStyle = "#e8e8e8"; g.font = '700 120px "Barlow Condensed", Impact, sans-serif';
  g.fillText("AUTOSLUŽBY PLN  ·  BRATISLAVA", x0 + s + 64, y0 + 470);
  g.fillStyle = "rgba(255,255,255,.75)"; g.font = '600 78px "Barlow", sans-serif';
  g.fillText("servis · diagnostika · pneuservis · STK", x0, 840);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(3.9, 1.95), new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false }));
  m.position.set(0, -1.35, 0.045);   // Door pivot je hore, panely idú dole; +z je predná strana vrát
  m.name = "DoorLogo";
  return m;
}
