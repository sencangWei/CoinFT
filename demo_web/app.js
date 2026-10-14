const axisScales = [0.12, 0.12, 0.7, 0.0004, 0.001, 0.001];
const colors = ["#50e4d2", "#6ab7ff", "#ae92ff"];
const axisList = document.getElementById("axis-list");
const channelGrid = document.getElementById("channel-grid");
const gainInput = document.getElementById("gain");
const gainLabel = document.getElementById("gain-value");
const forceCanvas = document.getElementById("force-chart");
const torqueCanvas = document.getElementById("torque-chart");
const surfaceView = createSurface(document.getElementById("surface-canvas"));
let shearProfile = disabledSurfaceProfile;
let lastSurfaceFrameAt = 0;
let demoBaseline = null, demoZeroSamples = [], demoZeroStartedAt = 0, demoZeroFrame = -1;
let demoPaused = false;
let tareGeneration = 0;
let tareFrame = -1;
let tarePending = false;
let sawTaring = false;
let tareAcked = false;

function validShearProfile(profile) {
  const finitePositive = value => Number.isFinite(value) && value > 0;
  const vector = values => Array.isArray(values) && values.length === 8 &&
    values.every(Number.isFinite);
  return profile && profile.version === 1 &&
    typeof profile.assemblyId === "string" && profile.assemblyId.trim() &&
    typeof profile.rightLabel === "string" && profile.rightLabel.trim() &&
    typeof profile.leftLabel === "string" && profile.leftLabel.trim() &&
    profile.rightLabel !== profile.leftLabel &&
    Array.isArray(profile.evidence) && profile.evidence.length > 0 &&
    profile.evidence.every(name => typeof name === "string" && name.trim() &&
      name.endsWith(".json")) &&
    profile.normal && finitePositive(profile.normal.threshold) &&
    finitePositive(profile.normal.span) && profile.shear &&
    typeof profile.shear.enabled === "boolean" &&
    vector(profile.shear.weights) && vector(profile.shear.pressLeak) &&
    finitePositive(profile.shear.threshold) && finitePositive(profile.shear.span);
}

async function loadShearProfile() {
  try {
    const response = await fetch("/shear_profile.json", { cache: "no-store" });
    if (response.status === 404) {
      const demoResponse = await fetch("/shear_demo_profile.json", { cache: "no-store" });
      if (!demoResponse.ok) throw new Error(`HTTP ${demoResponse.status}`);
      const demoProfile = await demoResponse.json();
      if (!validShearProfile(demoProfile) || demoProfile.mode !== "qualitative")
        throw new Error("Invalid qualitative profile");
      shearProfile = demoProfile;
      surfaceView.clear();
      updateDemoZero(lastSurfaceFrameAt > 0 && performance.now() - lastSurfaceFrameAt < 500);
      return;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const profile = await response.json();
    if (!validShearProfile(profile)) throw new Error("Invalid shear profile");
    shearProfile = profile;
    if (profile.shear.enabled) {
      document.querySelector(".surface-label").textContent = "正压／剪切响应示意（相对响应，非标定力值）";
    }
  } catch (_) {
    shearProfile = disabledSurfaceProfile;
  }
  updateDemoZero();
}
loadShearProfile();
const histories = Array.from({ length: 6 }, () => []);
const groupWindows = Array.from({ length: 6 }, () => []);
let gain = Number(gainInput.value);
let latestFrame = -1;
let lastAxes = Array(6).fill(0);
let lastGroups = Array(6).fill(0);
let lastChannels = Array(12).fill(0);
let fetching = false;
let displayCleared = false;

function updateDemoZero(ready = false) {
  const qualitative = shearProfile.mode === "qualitative";
  document.getElementById("demo-zero").disabled = !qualitative || !ready || tarePending;
  if (qualitative) document.querySelector(".surface-label").textContent =
    `定性演示 · 非标定力值 · 方向未经过独立验收 · ${demoBaseline ? (demoPaused ? "已暂停，等待自动恢复" : "画面已归零") :
      demoZeroFrame >= 0 ? "采集空载中" : "未归零"}`;
}

function invalidateDemoZero() {
  demoBaseline = null;
  demoPaused = false;
  demoZeroSamples = [];
  demoZeroStartedAt = 0;
  demoZeroFrame = -1;
  surfaceView.clear();
  updateDemoZero();
}

function pauseDemoZero() {
  if (shearProfile.mode !== "qualitative" || !demoBaseline) {
    invalidateDemoZero();
    return;
  }
  demoPaused = true;
  surfaceView.clear();
  lastSurfaceFrameAt = 0;
  updateDemoZero();
}

groupWindows.forEach((_, i) => {
  const row = document.createElement("div");
  row.className = "axis-row";
  row.innerHTML = `<span class="axis-label">G${i + 1}<small>CH${i * 2 + 1}–${i * 2 + 2}</small></span><div class="axis-rail"><span class="axis-fill"></span></div><strong class="axis-value">0</strong>`;
  axisList.append(row);
});
for (let i = 0; i < 12; i++) {
  const card = document.createElement("div");
  card.className = `channel-card ${i >= 8 ? "normal" : "shear"}`;
  card.innerHTML = `<div class="channel-top"><span>CH ${String(i + 1).padStart(2, "0")}</span><strong>+0</strong></div><div class="mini-rail"><span class="mini-fill"></span></div>`;
  channelGrid.append(card);
}

function response(value, axis) {
  return Math.tanh(value / axisScales[axis] * gain);
}

function chartResponse(value, axis) {
  return response(axis < 3 ? value / 3 : value, axis);
}

function groupResponses(channels) {
  return groupWindows.map((_, i) => (Math.abs(channels[i * 2]) + Math.abs(channels[i * 2 + 1])) / 2);
}

function median(values) {
  const ordered = [...values].sort((a, b) => a - b);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}

function paintBars(axes, groups, channels) {
  const rows = axisList.children;
  groups.forEach((value, i) => {
    const fill = rows[i].querySelector(".axis-fill");
    fill.style.left = "0%";
    fill.style.width = `${Math.min(value / 1000, 1) * 100}%`;
    rows[i].querySelector(".axis-value").textContent = String(Math.round(value));
  });
  channels.forEach((value, i) => {
    const card = channelGrid.children[i];
    const signed = Math.max(-1, Math.min(1, value / 1000));
    const fill = card.querySelector(".mini-fill");
    fill.style.left = `${50 + Math.min(0, signed) * 50}%`;
    fill.style.width = `${Math.abs(signed) * 50}%`;
    card.querySelector("strong").textContent = `${value >= 0 ? "+" : ""}${Math.round(value)}`;
    card.classList.toggle("over-range", Math.abs(value) > 1000);
  });
  const energy = axes.reduce((sum, value, i) => sum + Math.abs(response(value, i)), 0) / 6;
  const activity = Math.round(energy * 100);
  document.getElementById("activity-value").innerHTML = `${activity}<span>%</span>`;
}

function clearDisplay() {
  pauseDemoZero();
  surfaceView.clear();
  lastSurfaceFrameAt = 0;
  if (shearProfile.mode !== "qualitative") latestFrame = -1;
  lastAxes = Array(6).fill(0);
  lastGroups = Array(6).fill(0);
  lastChannels = Array(12).fill(0);
  histories.forEach(history => history.splice(0));
  groupWindows.forEach(window => window.splice(0));
  for (const row of axisList.children) {
    row.querySelector(".axis-value").textContent = "—";
    row.querySelector(".axis-fill").style.width = "0";
  }
  for (const card of channelGrid.children) {
    card.querySelector("strong").textContent = "—";
    card.querySelector(".mini-fill").style.width = "0";
    card.classList.remove("over-range");
  }
  document.getElementById("activity-value").innerHTML = "—";
  drawChart(forceCanvas, 0);
  drawChart(torqueCanvas, 3);
}

function drawChart(canvas, start) {
  const box = canvas.getBoundingClientRect();
  if (!box.width || !box.height) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(box.width * ratio);
  canvas.height = Math.round(box.height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const w = box.width, h = box.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "#2b4656";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 5]);
  for (let y = 0; y <= 2; y++) { ctx.beginPath(); ctx.moveTo(0, h * y / 2); ctx.lineTo(w, h * y / 2); ctx.stroke(); }
  for (let x = 1; x <= 4; x++) { ctx.beginPath(); ctx.moveTo(w * x / 4, 0); ctx.lineTo(w * x / 4, h); ctx.stroke(); }
  ctx.setLineDash([]);
  for (let k = 0; k < 3; k++) {
    const samples = histories[start + k];
    if (samples.length < 2) continue;
    ctx.beginPath();
    ctx.strokeStyle = colors[k];
    ctx.lineWidth = 2;
    for (let n = 0; n < samples.length; n++) {
      const x = n / (samples.length - 1) * w;
      const y = h / 2 - chartResponse(samples[n], start + k) * (h / 2 - 8);
      if (n === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

function updateStatus(data) {
  const good = data.status === "live" && data.invalid_recent === 0 &&
    data.saturated_recent === 0;
  if (data.status === "taring") invalidateDemoZero();
  else if (!good) pauseDemoZero();
  const pill = document.getElementById("status-pill");
  pill.classList.toggle("good", data.status === "live" && !data.invalid_recent && !data.saturated_recent);
  pill.classList.toggle("bad", data.status === "error" || data.invalid_recent > 0 || data.saturated_recent > 0);
  const labels = { connecting: "连接中", taring: `空载归零 ${data.tare_progress}%`, live: "数据正常", waiting: "等待数据", error: "连接异常" };
  document.getElementById("status-label").textContent = data.invalid_recent > 0 ? "原始帧异常" : data.saturated_recent > 0 ? "通道饱和" : (labels[data.status] || data.status);
  const sourceName = data.port || "串口";
  document.getElementById("source-label").textContent = data.mode === "replay" ? "历史采集回放" :
    data.status === "live" ? `${sourceName} · Teensy` :
    data.status === "taring" ? `${sourceName} · 空载归零中` :
    data.status === "waiting" ? `${sourceName} · 等待数据` : `${sourceName} · 未连接`;
  document.getElementById("mode-label").textContent = data.mode === "replay" ? "历史回放" :
    data.status === "live" ? "实时采集" : "实时模式 · 等待连接";
  document.getElementById("rate-label").innerHTML = `${data.rate.toFixed(1)} Hz <b>·</b> ${data.frames.toLocaleString()} 帧`;
  document.getElementById("stream-tag").textContent = data.status === "live" ?
    (data.invalid_recent || data.saturated_recent ? "SIGNAL DEGRADED" : "SIGNAL ACTIVE") : "SIGNAL STANDBY";
  document.querySelector(".live-tag").classList.toggle("good", data.status === "live" && !data.invalid_recent && !data.saturated_recent);
  document.getElementById("tare").disabled = data.status !== "live";
  document.getElementById("foot-status").textContent = data.message + (data.invalid_recent ? ` · 最近 2 秒异常帧 ${data.invalid_recent}` : "") + (data.invalid_frames ? ` · 累计异常 ${data.invalid_frames}` : "") + (data.saturated_recent ? ` · 最近 2 秒饱和样本 ${data.saturated_recent}` : "") + (data.resyncs ? ` · 错位 ${data.resyncs}` : "");
  if (data.status !== "live" && !displayCleared) {
    clearDisplay();
    displayCleared = true;
  }
  if (data.status === "live") displayCleared = false;
}

async function poll() {
  if (fetching) return;
  fetching = true;
  const requestGeneration = tareGeneration;
  const requestAfterTareAck = tareAcked;
  const controller = new AbortController();
  let timer;
  try {
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => {
        reject(new Error("State request timed out"));
        controller.abort();
      }, 1500);
    });
    const data = await Promise.race([fetch("/api/state", {
      cache: "no-store", signal: controller.signal
    }).then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }), timeout]);
    if (requestGeneration !== tareGeneration) return;
    if (tarePending) {
      if (data.status === "taring") sawTaring = true;
      if (data.status === "live") {
        if (!(sawTaring || (tareAcked && requestAfterTareAck)) ||
            !Number.isInteger(data.frames) ||
            data.frames <= tareFrame) return;
        tarePending = false;
      }
    }
    const qualitative = shearProfile.mode === "qualitative";
    const regressed = Number.isInteger(data.frames) && data.frames < latestFrame;
    const previousFrame = latestFrame;
    if (qualitative && Number.isInteger(data.frames)) {
      if (regressed) {
        invalidateDemoZero();
        lastSurfaceFrameAt = 0;
      }
      // A regression starts a disarmed server epoch; transient clears never reset it.
      latestFrame = data.frames;
    }
    updateStatus(data);
    if (shearProfile.mode === "qualitative" && data.status === "live" &&
        (!Array.isArray(data.channels) || data.channels.length !== 12 ||
         !data.channels.every(Number.isFinite))) {
      pauseDemoZero();
      lastSurfaceFrameAt = 0;
      return;
    }
    if (data.status === "live" && data.frames !== previousFrame) {
      if (!regressed && Number.isInteger(data.frames) && data.frames > previousFrame &&
          data.invalid_recent === 0 && data.saturated_recent === 0) {
        if (shearProfile.mode === "qualitative") {
          if (demoZeroFrame >= 0 && data.frames > demoZeroFrame) {
            if (!demoZeroSamples.length) demoZeroStartedAt = performance.now();
            demoZeroSamples.push([...data.channels]);
            demoZeroFrame = data.frames;
            if (demoZeroSamples.length >= 10 &&
                performance.now() - demoZeroStartedAt >= 1000) {
              demoBaseline = Array.from({ length: 12 }, (_, i) =>
                median(demoZeroSamples.map(sample => sample[i])));
              demoZeroSamples = [];
              demoZeroStartedAt = 0;
              demoZeroFrame = -1;
              updateDemoZero(true);
            }
          }
          if (demoBaseline) {
            demoPaused = false;
            surfaceView.set(data.channels.map((value, i) =>
              value - demoBaseline[i]), shearProfile);
          }
          else surfaceView.clear();
        } else surfaceView.set(data.channels, shearProfile);
        lastSurfaceFrameAt = performance.now();
        updateDemoZero(true);
      } else {
        if (regressed || !Number.isInteger(data.frames)) invalidateDemoZero();
        else pauseDemoZero();
        surfaceView.clear();
        lastSurfaceFrameAt = 0;
      }
      if (Number.isInteger(data.frames) && data.frames > latestFrame)
        latestFrame = data.frames;
      lastAxes = data.axes;
      lastChannels = data.channels;
      groupResponses(data.channels).forEach((value, i) => {
        groupWindows[i].push(value);
        if (groupWindows[i].length > 5) groupWindows[i].shift();
      });
      lastGroups = groupWindows.map(median);
      paintBars(data.axes, lastGroups, data.channels);
      data.axes.forEach((value, i) => {
        histories[i].push(value);
        if (histories[i].length > 180) histories[i].shift();
      });
      drawChart(forceCanvas, 0);
      drawChart(torqueCanvas, 3);
    } else if (data.status === "live" &&
               (data.invalid_recent !== 0 || data.saturated_recent !== 0 ||
                !lastSurfaceFrameAt || performance.now() - lastSurfaceFrameAt > 500)) {
      pauseDemoZero();
      surfaceView.clear();
      if (shearProfile.mode === "qualitative") lastSurfaceFrameAt = 0;
    }
  } catch (error) {
    if (requestGeneration !== tareGeneration) return;
    pauseDemoZero();
    document.getElementById("status-label").textContent = "页面与采集服务断开";
    document.getElementById("foot-status").textContent = String(error);
    document.getElementById("stream-tag").textContent = "SIGNAL STANDBY";
    document.querySelector(".live-tag").classList.remove("good");
    document.getElementById("status-pill").classList.remove("good");
    document.getElementById("status-pill").classList.add("bad");
    document.getElementById("tare").disabled = true;
    if (!displayCleared) {
      clearDisplay();
      displayCleared = true;
    }
  } finally {
    clearTimeout(timer);
    fetching = false;
  }
}

gainInput.addEventListener("input", () => {
  gain = Number(gainInput.value);
  gainLabel.textContent = `${gain.toFixed(1)}×`;
  if (!displayCleared) paintBars(lastAxes, lastGroups, lastChannels);
  drawChart(forceCanvas, 0);
  drawChart(torqueCanvas, 3);
});
document.getElementById("demo-zero").addEventListener("click", () => {
  demoBaseline = null;
  demoPaused = false;
  demoZeroSamples = [];
  demoZeroStartedAt = 0;
  demoZeroFrame = latestFrame;
  surfaceView.clear();
  updateDemoZero(true);
});
document.getElementById("tare").addEventListener("click", async () => {
  invalidateDemoZero();
  const button = document.getElementById("tare");
  button.disabled = true;
  tareGeneration += 1;
  tareFrame = latestFrame;
  tarePending = true;
  sawTaring = false;
  tareAcked = false;
  surfaceView.clear();
  lastSurfaceFrameAt = 0;
  try {
    const response = await fetch("/api/tare", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    tareAcked = true;
    histories.forEach(history => history.splice(0));
    groupWindows.forEach(window => window.splice(0));
  } catch (_) {
    tareGeneration += 1;
    tarePending = false;
    tareAcked = false;
    sawTaring = false;
    button.disabled = displayCleared;
  }
  invalidateDemoZero();
});
document.getElementById("fullscreen").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
});
document.addEventListener("keydown", event => {
  if (event.key.toLowerCase() === "f" && !["INPUT", "BUTTON"].includes(document.activeElement.tagName)) document.getElementById("fullscreen").click();
});
window.addEventListener("resize", () => {
  surfaceView.resize();
  drawChart(forceCanvas, 0);
  drawChart(torqueCanvas, 3);
});
drawChart(forceCanvas, 0);
drawChart(torqueCanvas, 3);
poll();
setInterval(poll, 50);
setInterval(() => {
  if (lastSurfaceFrameAt && performance.now() - lastSurfaceFrameAt >= 500) {
    pauseDemoZero();
    surfaceView.clear();
    lastSurfaceFrameAt = 0;
  }
}, 50);
