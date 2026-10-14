function surfaceLevel(channels) {
  if (!Array.isArray(channels) || channels.length !== 12 ||
      channels.some(value => !Number.isFinite(value))) return 0;
  const values = channels.map(Math.abs).sort((a, b) => a - b);
  const median = (values[5] + values[6]) / 2;
  return Math.max(0, Math.min(1, (median - 100) / 600));
}

const disabledSurfaceProfile = {
  version: 1,
  normal: { threshold: 100, span: 600 },
  shear: { enabled: false, weights: Array(8).fill(0),
           pressLeak: Array(8).fill(0), threshold: 1, span: 1 }
};

function validSurfaceChannels(channels) {
  return Array.isArray(channels) && channels.length === 12 &&
    channels.every(Number.isFinite);
}

function normalScore(channels) {
  const values = channels.slice(8).sort((a, b) => a - b);
  return Math.max(0, (values[1] + values[2]) / 2);
}

function normalLevel(channels, profile = disabledSurfaceProfile) {
  if (!validSurfaceChannels(channels) || !profile || profile.version !== 1 ||
      !profile.normal || !Number.isFinite(profile.normal.threshold) ||
      !Number.isFinite(profile.normal.span) || profile.normal.threshold <= 0 ||
      profile.normal.span <= 0) return 0;
  return Math.max(0, Math.min(1,
    (normalScore(channels) - profile.normal.threshold) / profile.normal.span));
}

function shearLevel(channels, profile = disabledSurfaceProfile, active = false) {
  const shear = profile && profile.shear;
  if (!validSurfaceChannels(channels) || !profile || profile.version !== 1 ||
      !shear || shear.enabled !== true ||
      !Array.isArray(shear.weights) || shear.weights.length !== 8 ||
      !shear.weights.every(Number.isFinite) ||
      !Array.isArray(shear.pressLeak) || shear.pressLeak.length !== 8 ||
      !shear.pressLeak.every(Number.isFinite) ||
      !Number.isFinite(shear.threshold) || shear.threshold <= 0 ||
      !Number.isFinite(shear.span) || shear.span <= 0) return 0;
  const avg = channels.slice(0, 8).reduce((a, b) => a + b, 0) / 8;
  const normal = normalScore(channels);
  const score = channels.slice(0, 8).reduce((sum, value, i) =>
    sum + shear.weights[i] * (value - avg - shear.pressLeak[i] * normal), 0);
  const threshold = shear.threshold * (profile.mode === "qualitative" ? 1 : (active ? 0.7 : 1));
  return Math.sign(score) * Math.max(0,
    Math.min(1, (Math.abs(score) - threshold) / shear.span));
}

function createSurface(canvas) {
  const surface = { target: 0, level: 0, shearTarget: 0, shearLevel: 0,
                    set, clear, resize };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let frame = 0;

  function resize() {
    const bounds = canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(bounds.width * ratio);
    canvas.height = Math.round(bounds.height * ratio);
    draw();
  }

  function draw() {
    const bounds = canvas.getBoundingClientRect();
    const w = bounds.width, h = bounds.height;
    if (!w || !h) return;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(canvas.width / w, 0, 0, canvas.height / h, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const steps = 18;
    function point(i, j) {
      const u = i / steps * 2 - 1;
      const v = j / steps * 2 - 1;
      const bump = Math.exp(-(u * u + v * v) / 0.18);
      const shift = surface.shearLevel;
      return [w * (0.5 + (u - v) * 0.23 + shift * 0.02),
              h * (0.34 + (u + v) * 0.105 + bump * surface.level * 0.17
                   + u * shift * 0.018), bump];
    }
    for (let j = 0; j < steps; j++) {
      for (let i = 0; i < steps; i++) {
        const a = point(i, j), b = point(i + 1, j);
        const c = point(i + 1, j + 1), d = point(i, j + 1);
        const intensity = (a[2] + b[2] + c[2] + d[2]) * surface.level / 4;
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.lineTo(c[0], c[1]);
        ctx.lineTo(d[0], d[1]);
        ctx.closePath();
        ctx.fillStyle = `rgba(57,211,194,${0.04 + intensity * 0.55})`;
        ctx.fill();
        ctx.strokeStyle = intensity > 0.08 ? `rgba(99,238,211,${0.45 + intensity * 0.4})` : "#a6c6629c";
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }
    }
  }

  function animate() {
    frame = 0;
    surface.level += (surface.target - surface.level) * 0.2;
    surface.shearLevel += (surface.shearTarget - surface.shearLevel) * 0.2;
    if (Math.abs(surface.target - surface.level) < 0.003) surface.level = surface.target;
    if (Math.abs(surface.shearTarget - surface.shearLevel) < 0.003)
      surface.shearLevel = surface.shearTarget;
    draw();
    if (surface.level !== surface.target || surface.shearLevel !== surface.shearTarget)
      frame = requestAnimationFrame(animate);
  }

  function set(channels, profile = disabledSurfaceProfile) {
    surface.target = normalLevel(channels, profile);
    surface.shearTarget = shearLevel(channels, profile, Math.abs(surface.shearTarget) > 0);
    if (reduced.matches) {
      finish();
    } else if (!frame) frame = requestAnimationFrame(animate);
  }

  function finish() {
    cancelAnimationFrame(frame);
    frame = 0;
    surface.level = surface.target;
    surface.shearLevel = surface.shearTarget;
    draw();
  }

  reduced.addEventListener("change", () => {
    if (reduced.matches) finish();
  });

  function clear() {
    cancelAnimationFrame(frame);
    frame = 0;
    surface.target = 0;
    surface.level = 0;
    surface.shearTarget = 0;
    surface.shearLevel = 0;
    draw();
  }

  resize();
  return surface;
}
