const status = document.querySelector(".audio-status");
let currentPlayback = null;

function stopPlayback(playback) {
  playback.player.pause();
  playback.button.setAttribute("aria-pressed", "false");
  if (currentPlayback === playback) {
    currentPlayback = null;
  }
}

document.querySelectorAll("button[data-audio]").forEach((button) => {
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
