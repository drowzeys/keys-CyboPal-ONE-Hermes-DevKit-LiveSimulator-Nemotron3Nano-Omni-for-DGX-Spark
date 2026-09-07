const LIMITS = {
  pan: [-55, 55, "°"],
  tilt: [-35, 35, "°"],
  height_mm: [80, 420, "mm"],
  reach_mm: [80, 700, "mm"],
  roll: [-18, 18, "°"],
  elbow: [-40, 25, "°"],
};

const state = {
  pose: { pan: 0, tilt: 6, height_mm: 200, reach_mm: 300, roll: 0, elbow: -8 },
  target: { pan: 0, tilt: 6, height_mm: 200, reach_mm: 300, roll: 0, elbow: -8 },
  user: { x: 0, y: 420, z: 620 },
  mode: "idle",
  pauli_text: "READY",
  display_markdown: "",
  events: [],
  arm_coordinates: { x: 0, y: 200, z: 300 },
};

const canvas = document.getElementById("stage");
const ctx = canvas.getContext("2d");
const metersEl = document.getElementById("meters");
const slidersEl = document.getElementById("sliders");
const logEl = document.getElementById("log");
const pauliEl = document.getElementById("pauli");
const mdEl = document.getElementById("main-md");
const connEl = document.getElementById("conn");

function pct(name, value) {
  const [lo, hi] = LIMITS[name];
  return Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
}

function renderMeters() {
  metersEl.innerHTML = Object.keys(LIMITS)
    .map((k) => {
      const v = state.pose[k] ?? 0;
      const unit = LIMITS[k][2];
      const w = (pct(k, v) * 100).toFixed(1);
      return `<div class="meter"><span>${k.replace("_mm", "")}</span><div class="bar"><span style="width:${w}%"></span></div><span class="val">${v.toFixed(1)}${unit}</span></div>`;
    })
    .join("");
}

function renderSliders() {
  if (slidersEl.childElementCount) return;
  slidersEl.innerHTML = Object.keys(LIMITS)
    .map((k) => {
      const [lo, hi, unit] = LIMITS[k];
      return `<div class="slider"><label>${k} <span id="lab-${k}">${state.pose[k]}${unit}</span></label><input type="range" id="s-${k}" min="${lo}" max="${hi}" step="0.5" value="${state.pose[k]}" /></div>`;
    })
    .join("");
}

function syncSliderLabels() {
  for (const k of Object.keys(LIMITS)) {
    const el = document.getElementById("s-" + k);
    const lab = document.getElementById("lab-" + k);
    if (el && document.activeElement !== el) el.value = state.target[k];
    if (lab) lab.textContent = `${Number(el ? el.value : state.target[k]).toFixed(1)}${LIMITS[k][2]}`;
  }
}

function md(src) {
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  return esc(src || "")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n{2,}/g, "<p></p>")
    .replace(/\n/g, "<br/>");
}

function renderLog() {
  logEl.innerHTML = (state.events || [])
    .map((e) => {
      const t = new Date(e.t * 1000).toLocaleTimeString();
      return `<li><span class="k">${e.kind}</span>${t} — ${e.message}</li>`;
    })
    .join("");
}

function iso(origin, x, y, z) {
  return {
    x: origin.x + x * 0.9 + z * 0.42,
    y: origin.y - y - z * 0.28,
  };
}

function drawStage() {
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#15202c");
  g.addColorStop(1, "#0b0d10");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  const origin = { x: W * 0.42, y: H * 0.78 };
  const pose = state.pose;
  const pan = (pose.pan * Math.PI) / 180;
  const tilt = (pose.tilt * Math.PI) / 180;
  const roll = (pose.roll * Math.PI) / 180;
  const elbow = (pose.elbow * Math.PI) / 180;

  // Floor grid
  ctx.strokeStyle = "#1d2733";
  ctx.lineWidth = 1;
  for (let i = -6; i <= 8; i++) {
    const a = iso(origin, i * 40, 0, -80);
    const b = iso(origin, i * 40, 0, 420);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  // Desk
  const desk = [
    iso(origin, -240, 0, -40),
    iso(origin, 260, 0, -40),
    iso(origin, 300, 0, 280),
    iso(origin, -200, 0, 280),
  ];
  ctx.beginPath();
  ctx.moveTo(desk[0].x, desk[0].y);
  desk.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
  ctx.closePath();
  ctx.fillStyle = "#6a4a32";
  ctx.fill();
  ctx.strokeStyle = "#3a281c";
  ctx.stroke();

  // User sits on the near side of the desk so the arm is clearly tracking someone.
  const u = iso(origin, state.user.x * 0.42, 58, 55);
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.beginPath();
  ctx.ellipse(u.x, u.y + 36, 24, 8, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#3d7aad";
  ctx.beginPath();
  ctx.ellipse(u.x, u.y + 10, 26, 30, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#6ec4ff";
  ctx.beginPath();
  ctx.arc(u.x, u.y - 28, 18, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#1a2430";
  ctx.beginPath();
  ctx.arc(u.x - 6, u.y - 30, 3, 0, Math.PI * 2);
  ctx.arc(u.x + 6, u.y - 30, 3, 0, Math.PI * 2);
  ctx.fill();

  // Arm kinematics in mm → scene units
  const h = pose.height_mm * 0.42;
  const r = pose.reach_mm * 0.42;
  const base = iso(origin, 0, 8, 40);
  const shoulder = iso(origin, 0, 8 + h * 0.35, 40);
  const midX = Math.sin(pan) * r * 0.45;
  const midZ = 40 + Math.cos(pan) * r * 0.45;
  const elbowPt = iso(origin, midX, 8 + h * 0.7 + Math.sin(elbow) * 18, midZ);
  const tipX = Math.sin(pan) * r;
  const tipZ = 40 + Math.cos(pan) * r;
  const tipY = 8 + h + Math.sin(elbow) * 24;
  const wrist = iso(origin, tipX, tipY, tipZ);

  // Shadow
  const sh = iso(origin, tipX, 1, tipZ);
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.beginPath();
  ctx.ellipse(sh.x, sh.y, 46, 14, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#c9d0da";
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.moveTo(base.x, base.y);
  ctx.lineTo(shoulder.x, shoulder.y);
  ctx.lineTo(elbowPt.x, elbowPt.y);
  ctx.lineTo(wrist.x, wrist.y);
  ctx.stroke();
  ctx.strokeStyle = "#8a929e";
  ctx.lineWidth = 4;
  ctx.stroke();

  for (const p of [base, shoulder, elbowPt, wrist]) {
    ctx.fillStyle = "#e8eef6";
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  // Monitor
  const mw = 78;
  const mh = 46;
  ctx.save();
  ctx.translate(wrist.x, wrist.y - 8);
  ctx.rotate(-tilt * 0.9 + roll * 0.3);
  ctx.fillStyle = "#1a1d22";
  ctx.fillRect(-mw, -mh, mw * 2, mh * 2);
  ctx.fillStyle = "#c8e86a";
  ctx.fillRect(-mw + 6, -mh + 6, mw * 2 - 12, mh * 2 - 18);
  ctx.fillStyle = "#0b0d10";
  ctx.font = "9px ui-monospace, monospace";
  ctx.fillText("ONE", -10, 4);
  // Pauli
  ctx.fillStyle = "#0e1512";
  ctx.fillRect(mw - 22, mh - 8, 28, 16);
  ctx.fillStyle = "#7ee0c6";
  ctx.fillRect(mw - 19, mh - 5, 22, 10);
  // Bezel cam
  ctx.fillStyle = "#f04";
  ctx.beginPath();
  ctx.arc(0, -mh + 10, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.fillStyle = "#8b97a8";
  ctx.font = "12px ui-monospace, monospace";
  const c = state.arm_coordinates || {};
  ctx.fillText(
    `xyz ${c.x ?? 0}, ${c.y ?? 0}, ${c.z ?? 0}   mode ${state.mode}`,
    24,
    28
  );
}

function applySnapshot(s) {
  state.pose = s.pose || state.pose;
  state.target = s.target || state.target;
  state.user = s.user || state.user;
  state.mode = s.mode || state.mode;
  state.pauli_text = s.pauli_text || "";
  state.display_markdown = s.display_markdown || "";
  state.events = s.events || [];
  state.arm_coordinates = s.arm_coordinates || {};
  pauliEl.textContent = state.pauli_text;
  mdEl.innerHTML = md(state.display_markdown);
  renderMeters();
  renderLog();
  syncSliderLabels();
  document.querySelectorAll(".modes button").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === state.mode || (state.mode === "preset" && false));
  });
  const followBtn = document.querySelector('[data-mode="tracking"]');
  if (followBtn) followBtn.classList.toggle("active", state.mode === "tracking");
}

function loop() {
  drawStage();
  requestAnimationFrame(loop);
}

async function post(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

document.getElementById("modes").addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-mode]");
  if (!b) return;
  await post("/api/v1/mode", { mode: b.dataset.mode });
});

document.getElementById("nudge").addEventListener("click", async () => {
  const body = {};
  for (const k of Object.keys(LIMITS)) {
    body[k] = Number(document.getElementById("s-" + k).value);
  }
  body.mode = "agent";
  await post("/api/v1/control", body);
});

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/telemetry`);
  ws.onopen = () => {
    connEl.textContent = "live";
    connEl.className = "status-pill ok";
  };
  ws.onclose = () => {
    connEl.textContent = "reconnecting";
    connEl.className = "status-pill bad";
    setTimeout(connect, 800);
  };
  ws.onmessage = (ev) => {
    try {
      applySnapshot(JSON.parse(ev.data));
    } catch (_) {}
  };
}

renderSliders();
renderMeters();
connect();
loop();
