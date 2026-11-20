import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { SERVICES } from "./services.js";
import { pickView, VIEWS, INTRO, INTRO_MS, frontFov } from "./views.js";
import { calloutQuery, layoutCallouts, clearCallouts, resetCalloutBounds } from "./callouts.js";

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
const toThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);   // Blender → three

// Úvod: z ulice cez vráta k predku auta a potom na hlavný pohľad. Potom sa auto otáča ťahaním (myš aj prst).
export async function createScene({ canvas, bubblesEl, onBubble, reduced }) {
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

  // svetlá interiéru (LED panely) + bodové svetlo nad autom
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
  const facadeLamp = new THREE.SpotLight(0xffe6c8, 160, 26, 0.95, 0.75, 1.5);   // osvetlenie fasády pri úvode
  facadeLamp.position.set(0, 7.0, 13.5);
  facadeLamp.target.position.set(0, 2.4, 4.2);
  scene.add(facadeLamp, facadeLamp.target);

  // model (garáž + auto z Blendera, export GLB)
  const draco = new DRACOLoader().setDecoderPath("vendor/three/jsm/libs/draco/gltf/").setDecoderConfig({ type: "wasm" });
  const gltf = await new GLTFLoader().setDRACOLoader(draco).loadAsync("models/garage.glb?v=17");
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
  function highlight(id) {
    bubbles.forEach((b) => b.el.classList.toggle("hot", b.s.id === id));
    document.dispatchEvent(new CustomEvent("svc-highlight", { detail: id }));
  }
  const bubbles = SERVICES.map((s) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "bubble" + (s.big ? " big" : "");
    el.setAttribute("aria-label", s.title + " – zobraziť detail");
    el.innerHTML = `<span class="dot">${s.icon}</span><span class="lab"><span class="lf">${s.title}</span><span class="ls">${s.mob || s.title}</span></span>`;
    el.addEventListener("click", () => onBubble(s.id));
    // prejdenie myšou / fokus → zvýrazní bublinu
    el.addEventListener("pointerenter", () => highlight(s.id));
    el.addEventListener("pointerleave", () => highlight(null));
    el.addEventListener("focus", () => highlight(s.id));
    el.addEventListener("blur", () => highlight(null));
    bubblesEl.appendChild(el);
    if (s.id === "odtah" && VIEWS.odtah) {            // pevný bod mimo auta (podľa pohľadu), neotáča sa
      return { s, el, world: new THREE.Vector3(), half: s.big ? 34 : 26 };
    }
    const an = car.getObjectByName("AN_" + s.id);
    const a = an ? an.position.clone() : new THREE.Vector3(), n = toThree(s.normal).normalize();
    // zrkadlový bod na druhom boku auta (kolesá, kapota…) – bublina ostane viditeľná aj po otočení
    const side = Math.abs(n.x) > 0.25 || Math.abs(a.x) > 0.3;
    return { s, el, half: 26, a, n, a2: side ? new THREE.Vector3(-a.x, a.y, a.z) : null, n2: side ? new THREE.Vector3(-n.x, n.y, n.z) : null };
  });

  // --- otáčanie auta ťahaním ---
  let view = pickView(1.6);
  let yaw = 0, vel = 0, dragging = false, lastX = 0, lastT = 0, moved = 0;
  canvas.style.touchAction = "pan-y";            // zvislý pohyb prstom ďalej posúva stránku
  canvas.addEventListener("pointerdown", (e) => {
    if (zoomTo) return;                                   // priblížené → neotáčať
    if (intro && intro.t0 !== Infinity) intro.t0 = -1e9;   // ťah počas úvodu → jazdu preskočiť, hneď otáčať
    dragging = true; moved = 0; lastX = e.clientX; lastT = performance.now(); vel = 0;
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add("grabbing");
    kick();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const now = performance.now(), dx = e.clientX - lastX;
    const k = 6.0 / Math.max(500, canvas.clientWidth);          // celá šírka obrazovky ≈ 1 otočka
    yaw += dx * k;
    vel = (dx * k) / Math.max(0.008, (now - lastT) / 1000);
    moved += Math.abs(dx); lastX = e.clientX; lastT = now;
    kick();
  });
  const release = (e) => {
    if (!dragging) return;
    dragging = false;
    canvas.classList.remove("grabbing");
    if (performance.now() - lastT > 80) vel = 0;               // pustil bez pohybu → bez zotrvačnosti
    try { canvas.releasePointerCapture(e.pointerId); } catch (err) {}
    if (moved > 4) document.dispatchEvent(new CustomEvent("car-rotated"));
    kick();
  };
  canvas.addEventListener("pointerup", release);
  canvas.addEventListener("pointercancel", release);
  // klávesnica: šípky otáčajú auto (fokus na plátne)
  canvas.tabIndex = 0;
  canvas.setAttribute("aria-label", "3D garáž – auto otočíte ťahaním alebo šípkami");
  canvas.removeAttribute("aria-hidden");
  canvas.addEventListener("keydown", (e) => {
    if (!intro && (e.key === "ArrowLeft" || e.key === "ArrowRight")) { e.preventDefault(); vel = (e.key === "ArrowLeft" ? -1 : 1) * 2.2; kick(); }
  });

  let W = 0, H = 0;
  function resize() {
    resetCalloutBounds();
    W = canvas.clientWidth; H = canvas.clientHeight;
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    view = pickView(camera.aspect);
  }

  // úvodná jazda (časová, nezávislá od FPS)
  let intro = reduced ? null : { t0: Infinity, done: null };   // čaká na playIntro – dovtedy stojí kamera na ulici
  const P = new THREE.Vector3(), T = new THREE.Vector3();
  function pose(now) {
    let t = intro ? clamp((now - intro.t0) / INTRO_MS) : 1;
    if (reduced) t = 1;
    const keys = [...INTRO, { t: 1, pos: view.pos, tgt: view.tgt, fovAbs: view.vfov }];
    let i = 0;
    while (i < keys.length - 2 && t > keys[i + 1].t) i++;
    const a = keys[i], b = keys[i + 1];
    const k = smooth(0, 1, (t - a.t) / (b.t - a.t));
    const ff = frontFov(camera.aspect);
    const fa = a.fovAbs ?? ff + a.fovAdd, fb = b.fovAbs ?? ff + b.fovAdd;
    P.set(lerp(a.pos[0], b.pos[0], k), lerp(a.pos[1], b.pos[1], k), lerp(a.pos[2], b.pos[2], k));
    T.set(lerp(a.tgt[0], b.tgt[0], k), lerp(a.tgt[1], b.tgt[1], k), lerp(a.tgt[2], b.tgt[2], k));
    camera.fov = lerp(fa, fb, k);
    camera.updateProjectionMatrix();
    camera.position.copy(P);
    camera.lookAt(T);
    camera.updateMatrixWorld();
    // vráta sa zrolujú nahor počas prvej časti
    const open = smooth(0.02, 0.24, t);
    if (door) { door.scale.y = Math.max(0.0015, 1 - open * 0.998); door.visible = open < 0.995; }
    // auto sa z predného pohľadu natočí do hlavného uhla
    const turn = smooth(INTRO[INTRO.length - 1].t, 1, t);
    if (intro && t >= 1) { const d = intro.done; intro = null; d && d(); }
    return { t, turn };
  }

  // --- priblíženie na miesto služby (klik na bublinu) ---
  let zoom = null, zk = 0, zoomTo = null;          // zk: 0 = hlavný pohľad, 1 = priblížené
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  function focusPose(id) {
    const s = SERVICES.find((x) => x.id === id);
    if (id === "odtah" && VIEWS.sign) {               // Odťah: kamera priletí k tabuli na pravej stene, text bude vľavo
      const g = VIEWS.sign, tgt = new THREE.Vector3(...g.tgt), n = new THREE.Vector3(...g.n).normalize();
      // vzdialenosť tak, aby sa celá tabuľa (1,5 m) zmestila do svojej polovice obrazu aj na užšej obrazovke
      const tall = camera.aspect < 1, fov = tall ? 58 : 38, tn = Math.tan((fov * Math.PI) / 360) * camera.aspect;
      const dist = clamp(Math.max(tall ? g.distTall : g.dist, (tall ? 0.95 : 1.75) / tn), 2, 4.8);
      const pos = tgt.clone().addScaledVector(n, dist);
      pos.y -= 0.25;
      return { pos, tgt, fov, dyaw: 0, left: true };
    }
    const an = car.getObjectByName("AN_" + id);
    if (!s || !an) return null;
    const n = toThree(s.normal).normalize();
    const pick = () => {
      root.updateMatrixWorld(true);
      const qq = new THREE.Quaternion(); car.getWorldQuaternion(qq);
      const cands = [[an.position.clone(), n.clone()]];
      if (Math.abs(n.x) > 0.25 || Math.abs(an.position.x) > 0.3) cands.push([new THREE.Vector3(-an.position.x, an.position.y, an.position.z), new THREE.Vector3(-n.x, n.y, n.z)]);
      let best = null;
      cands.forEach(([a, nn]) => {                    // strana auta otočená ku kamere
        const wa = car.localToWorld(a.clone()), wn = nn.applyQuaternion(qq);
        const f = wn.dot(camera.position.clone().sub(wa).normalize());
        if (!best || f > best.f) best = { wa, wn, f };
      });
      return best;
    };
    let best = pick(), dyaw = 0;
    if (best.f < 0.35) {                              // miesto je na odvrátenej strane (napr. výfuk) → auto najprv pootočíme
      const cp = new THREE.Vector3(); car.getWorldPosition(cp);
      const angCam = Math.atan2(camera.position.x - cp.x, camera.position.z - cp.z);
      const need = angCam - Math.atan2(n.x, n.z) - 0.5 * Math.sign(n.x || 1);
      dyaw = Math.atan2(Math.sin(need - car.rotation.y), Math.cos(need - car.rotation.y));
      const keep = car.rotation.y;
      car.rotation.y += dyaw; best = pick(); car.rotation.y = keep; root.updateMatrixWorld(true);
    }
    const toC = camera.position.clone().sub(best.wa).normalize();
    const dir = best.wn.clone().multiplyScalar(0.55).add(toC.multiplyScalar(0.45)).normalize();
    const pos = best.wa.clone().addScaledVector(dir, s.zoom ?? 1.9);
    pos.y += 0.3;
    // kamera ostane v garáži (vnútro x ±3.8, z −3.9…+3.9, vráta otvorené dopredu)
    pos.x = clamp(pos.x, -3.0, 3.0); pos.z = clamp(pos.z, -3.0, 6.5); pos.y = clamp(pos.y, 0.45, 2.6);
    return { pos, tgt: best.wa, fov: camera.aspect < 1 ? 58 : 38, dyaw };
  }

  const w = new THREE.Vector3(), nW = new THREE.Vector3(), q = new THREE.Quaternion(), cc = new THREE.Vector3(), toCam = new THREE.Vector3();
  let last = performance.now(), slow = 0, dpr = Math.min(window.devicePixelRatio || 1, 1.5), lastYaw = null;
  function frame() {
    const now = performance.now(), dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    if (!dragging && vel) {
      yaw += vel * dt;
      vel *= Math.exp(-dt * (reduced ? 20 : 3.2));
      if (Math.abs(vel) < 0.01) vel = 0;
    }
    // slabý výkon → nižšie rozlíšenie
    if (dt > 0.045) { if (++slow > 20 && dpr > 1) { dpr = 1; renderer.setPixelRatio(dpr); renderer.setSize(W, H, false); } } else slow = Math.max(0, slow - 1);

    const { t, turn } = pose(now);
    if (zoom) {
      const p = clamp((now - zoom.t0) / zoom.dur);
      zk = zoom.dir > 0 ? ease(p) : 1 - ease(p);
      if (zoom.dir > 0 && zoom.dyaw) yaw = zoom.yaw0 + zoom.dyaw * ease(p);   // pootočenie auta k miestu služby
      if (p >= 1) { const d = zoom.done; if (zoom.dir < 0) zoomTo = null; zoom = null; d && d(); }
    }
    if (zoomTo && zk > 0) {
      // priblížená časť auta je v jednej polovici, text v druhej (PC: auto vľavo / text vpravo, mobil: auto hore / text dole)
      // Odťah (left): naopak – tabuľa v pravej polovici, text vľavo
      if (camera.aspect >= 1) camera.setViewOffset(W, H, W * 0.25 * zk * (zoomTo.left ? -1 : 1), 0, W, H);
      else camera.setViewOffset(W, H, 0, H * 0.25 * zk, W, H);                     // stred hornej polovice
      camera.position.lerpVectors(P, zoomTo.pos, zk);
      camera.lookAt(T.clone().lerp(zoomTo.tgt, zk));
      camera.fov = lerp(camera.fov, zoomTo.fov, zk);
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld();
    }
    car.rotation.y = view.yaw * turn + yaw;
    if (car.rotation.y !== lastYaw) { renderer.shadowMap.needsUpdate = true; lastYaw = car.rotation.y; }
    root.updateMatrixWorld(true);

    // bubliny – iba tie, ktoré sú natočené ku kamere
    car.getWorldQuaternion(q);
    car.getWorldPosition(cc); cc.y += 0.6; cc.project(camera);
    const cx = (cc.x * 0.5 + 0.5) * W;
    const facing = (a, n) => {
      w.copy(a); car.localToWorld(w);
      nW.copy(n).applyQuaternion(q);
      return nW.dot(toCam.copy(camera.position).sub(w).normalize());
    };
    if (!(zoomTo && zk > 0) && camera.view?.enabled) { camera.clearViewOffset(); }
    const show = smooth(0.82, 1, t) * (1 - smooth(0, 0.35, zk));
    bubbles.forEach((b) => {
      if (b.world) {
        w.fromArray(view.odtah || [0, 0, 0]).project(camera);
        const x = (w.x * 0.5 + 0.5) * W, y = (-w.y * 0.5 + 0.5) * H;
        const op = w.z < 1 && Math.abs(w.x) < 1.05 && Math.abs(w.y) < 1.05 ? show : 0;
        b.el.style.opacity = op.toFixed(3);
        b.el.style.pointerEvents = op > 0.5 ? "auto" : "none";
        b.el.style.visibility = op < 0.02 ? "hidden" : "visible";
        b.el.style.transform = `translate(${(x - b.half).toFixed(1)}px,${(y - b.half).toFixed(1)}px)`;
        b.el.style.zIndex = "1500";
        b.el.classList.toggle("left", x < cx - 8);
        b.el.tabIndex = op > 0.5 ? 0 : -1;
        b.x = x; b.y = y; b.op = op;
        return;
      }
      let f = facing(b.a, b.n), a = b.a;
      if (b.a2) { const f2 = facing(b.a2, b.n2); if (f2 > f + 0.05) { f = f2; a = b.a2; } }
      w.copy(a); car.localToWorld(w);
      const vis = smooth(-0.1, 0.3, f);
      w.project(camera);
      const inView = w.z < 1 && Math.abs(w.x) < 1.05 && Math.abs(w.y) < 1.05;
      const x = (w.x * 0.5 + 0.5) * W, y = (-w.y * 0.5 + 0.5) * H;
      const op = inView ? vis * show : 0;
      b.el.style.opacity = op.toFixed(3);
      b.el.style.pointerEvents = op > 0.5 ? "auto" : "none";
      b.el.style.visibility = op < 0.02 ? "hidden" : "visible";
      b.el.style.transform = `translate(${(x - b.half).toFixed(1)}px,${(y - b.half).toFixed(1)}px)`;
      b.el.style.zIndex = String(1000 - Math.round(w.z * 500));
      b.el.classList.toggle("left", x < cx - 8);
      b.el.tabIndex = op > 0.5 ? 0 : -1;
      b.x = x; b.y = y; b.op = op;
    });
    // mobil: popisky ako obdĺžniky nad/pod autom so spojovacou čiarou
    if (calloutQuery.matches) layoutCallouts(bubblesEl, bubbles, (-cc.y * 0.5 + 0.5) * H);
    else if (bubblesEl.classList.contains("callouts")) clearCallouts(bubblesEl);
    renderer.render(scene, camera);
  }

  let running = true, loopId = 0;
  const busy = () => dragging || vel !== 0 || !!intro || !!zoom;
  function kick() {
    if (loopId) return;
    last = performance.now();
    loopId = requestAnimationFrame(function tick() {
      loopId = 0;
      if (!running) return;
      frame();
      if (busy()) loopId = requestAnimationFrame(tick);
    });
  }

  resize();
  new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
  // shadery skompilovať vopred → prvé otočenie bez trhania
  try { renderer.shadowMap.needsUpdate = true; await renderer.compileAsync(scene, camera); } catch (e) {}
  frame();

  return {
    highlight,
    // klik na bublinu: kamera sa priblíži na miesto služby (koleso, sklo…), potom sa otvorí detail
    focus: (id) => new Promise((res) => {
      if (intro) { intro.t0 = -1e9; frame(); }          // úvodnú jazdu preskočiť, kamera hneď na hlavnom pohľade
      if (reduced) return res();
      const to = focusPose(id);
      if (!to) return res();
      vel = 0; zoomTo = to;
      zoom = { t0: performance.now(), dur: to.dyaw ? 1300 : 950, dir: 1, done: res, yaw0: yaw, dyaw: to.dyaw };
      kick();
    }),
    unfocus: () => {
      if (!zoomTo) return;
      zoom = { t0: performance.now() - (1 - zk) * 700, dur: 700, dir: -1, done: null };
      kick();
    },
    playIntro: (done) => { if (reduced) { done && done(); kick(); return; } intro = { t0: performance.now(), done }; kick(); },
    pause: () => { running = false; },
    resume: () => { running = true; kick(); },
    kick,
  };
}
