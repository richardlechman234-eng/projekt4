// Pohľady kamery na auto. Súradnice three.js: x doprava, y hore, z k vrátam (auto v strede, nos k +z).
// hfov = vodorovný zorný uhol v stupňoch (zvislý sa dopočíta podľa pomeru strán), yaw = počiatočné natočenie auta.
// POZOR: obsah medzi /*JSON*/ a /*END*/ musí ostať platný JSON – číta ho aj tools/render_poster.py.
export const VIEWS = /*JSON*/{
  "wide": { "pos": [1.30, 1.54, 4.75], "tgt": [0.00, 0.80, 0.35], "hfov": 88.8, "vmax": 62, "yaw": -0.32 },
  "tall": { "pos": [1.10, 1.55, 6.20], "tgt": [-0.40, 0.50, 0.30], "hfov": 48.0, "vmax": 80, "yaw": -0.42 },
  "odtah": { "wide": [2.95, 1.55, -0.95], "tall": [1.40, 0.13, 3.60] },
  "sign": { "tgt": [3.00, 2.20, -1.00], "n": [-0.71, 0.00, 0.71], "dist": 2.9, "distTall": 3.3 }
}/*END*/;
// "odtah" = pevný bod pre bublinu Odťah v každom pohľade (neotáča sa s autom). PC: pod tabuľou ODŤAH vpravo,
// na výšku: vpravo dole pod autom (tabuľa je mimo úzkeho záberu, kamera k nej pri detaile priletí; hore by sa popisok bil s ostatnými).
// "sign" = stred tabule ODŤAH a smer jej líca (musí sedieť s TOW_LOC / TOW_YAW v tools/build_scene.py);
// dist / distTall = vzdialenosť kamery pri detaile (PC / na výšku).

// Úvodná jazda kamery: z ulice cez vráta k predku auta, potom na pohľad "wide"/"tall".
export const INTRO = [
  { t: 0.00, pos: [0, 1.15, 14.0], tgt: [0, 2.75, 4.2], fovAdd: 4 },
  { t: 0.26, pos: [0, 1.35, 10.0], tgt: [0, 1.40, 2.5], fovAdd: 0 },
  { t: 0.46, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fovAdd: 0 },
  { t: 0.54, pos: [0, 1.40, 6.6], tgt: [0, 0.75, 1.0], fovAdd: 0 },
];
export const INTRO_MS = 3600;
export const frontFov = (aspect) => (aspect < 0.65 ? 74 : aspect < 0.9 ? 64 : aspect < 1.3 ? 50 : 42);

export const TALL_BELOW = 1.15;      // pomer šírka/výška, pod ktorým sa použije pohľad "tall"

export function pickView(aspect) {
  const key = aspect < TALL_BELOW ? "tall" : "wide", v = VIEWS[key];
  const h = Math.tan((v.hfov * Math.PI) / 360);
  const vfov = Math.min(v.vmax, (Math.atan(h / aspect) * 360) / Math.PI);
  return { ...v, vfov, odtah: VIEWS.odtah?.[key] };
}
