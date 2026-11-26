const status = document.querySelector(".audio-status");
const boostButton = document.querySelector(".audio-boost");
const listenButtons = document.querySelectorAll("button[data-audio]");
const AudioContextType = window.AudioContext || window.webkitAudioContext;
let currentPlayback = null;
let boostEnabled = false;
let boostGraph = null;

function createBoostGraph() {
  const context = new AudioContextType();
  const gain = context.createGain();
  gain.gain.value = 3;
  const compressor = context.createDynamicsCompressor();
  compressor.threshold.value = -7;
  compressor.knee.value = 6;
  compressor.ratio.value = 16;
  compressor.attack.value = 0.003;

  // Leave headroom for the compressor's attack transients.
  const limiter = context.createWaveShaper();
  limiter.curve = Float32Array.from({ length: 2049 }, (_, index) => {
    const input = index / 1024 - 1;
    const level = Math.abs(input);
    return level <= 0.85
      ? input
      : Math.sign(input) * (0.85 + 0.13 * Math.tanh((level - 0.85) / 0.13));
  });
  gain.connect(compressor);
  compressor.connect(limiter);
  limiter.connect(context.destination);
  return { context, gain };
}

function setBoost(enabled) {
  boostEnabled = enabled;
  boostButton.setAttribute("aria-pressed", String(enabled));
}

async function applyBoost(playback) {
  if (!boostEnabled) {
    if (playback.source) {
      playback.source.disconnect();
      playback.source.connect(boostGraph.context.destination);
    }
    return;
  }

  try {
    boostGraph ??= createBoostGraph();
    await boostGraph.context.resume();
    if (!boostEnabled || playback !== currentPlayback) return;
    playback.source ??= boostGraph.context.createMediaElementSource(playback.player);
    playback.source.disconnect();
    playback.source.connect(boostGraph.gain);
  } catch {
    if (playback !== currentPlayback) return;
    setBoost(false);
    await applyBoost(playback);
  }
}

if (AudioContextType && listenButtons.length) {
  boostButton.hidden = false;
  boostButton.addEventListener("click", () => {
    setBoost(!boostEnabled);
    if (currentPlayback) void applyBoost(currentPlayback);
  });
}

function stopPlayback(playback) {
  playback.player.pause();
  playback.source?.disconnect();
  playback.button.setAttribute("aria-pressed", "false");
  if (currentPlayback === playback) {
    currentPlayback = null;
  }
}

listenButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    status.textContent = "";

    if (currentPlayback) {
      const sameButton = currentPlayback.button === button;
      stopPlayback(currentPlayback);
      if (sameButton) {
        return;
      }
    }

    const player = new Audio(button.dataset.audio);
    const playback = { player, button };
    currentPlayback = playback;
    button.setAttribute("aria-pressed", "true");

    player.addEventListener("ended", () => stopPlayback(playback), { once: true });
    player.addEventListener("error", () => {
      if (currentPlayback === playback) {
        status.textContent = status.dataset.error;
        stopPlayback(playback);
      }
    }, { once: true });

    if (boostEnabled) void applyBoost(playback);
    try {
      await player.play();
    } catch {
      if (currentPlayback === playback) {
        status.textContent = status.dataset.error;
        stopPlayback(playback);
      }
    }
  });
});
