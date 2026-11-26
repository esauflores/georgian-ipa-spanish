"""Exercise the dictionary with a real browser and an isolated local server."""

import re
import shutil
import socket
import threading
import time
import wave
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.sync_api import expect

import main
from dictionary import page as dictionary_page
from dictionary.audio import clip_name


@pytest.fixture
def dictionary_url(tmp_path, monkeypatch):
    static = tmp_path / "static"
    audio = static / "audio"
    audio.mkdir(parents=True)
    for filename in ("dictionary.css", "audio.js"):
        shutil.copyfile(main.STATIC_DIR / filename, static / filename)
    for phrase in ("ქართული არ ვიცი.", "ვერ გავიგე."):
        with wave.open(str(audio / clip_name(phrase)), "wb") as clip:
            clip.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            clip.writeframes(b"\0" * 2 * 8000 * 10)
    monkeypatch.setattr(main, "STATIC_DIR", static)
    monkeypatch.setattr(dictionary_page, "AUDIO_DIR", audio)

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                main.create_app(tmp_path / "entries.json"),
                log_level="warning",
                lifespan="off",
                ws="none",
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    pytest.fail("The dictionary test server failed to start.")
                time.sleep(0.01)
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "The dictionary test server failed to stop."


def test_language_switch_preserves_category_and_search(page, dictionary_url):
    page.goto(dictionary_url)
    page.get_by_role("link", name="Comunicación", exact=True).click()
    expect(page.get_by_role("article")).to_have_count(4)
    page.get_by_role("link", name="English", exact=True).click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_role("link", name="Communication", exact=True)).to_have_attribute("aria-current", "true")
    expect(page.get_by_role("article")).to_have_count(4)

    page.get_by_role("searchbox").fill("repeat")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_role("article")).to_have_count(1)
    expect(page.get_by_role("article")).to_contain_text(re.compile("repeat", re.IGNORECASE))
    expect(page.get_by_role("link", name="Communication", exact=True)).to_have_attribute("aria-current", "true")


@pytest.mark.parametrize("width", [320, 390, 430])
def test_mobile_cards_and_audio_controls_fit(browser, dictionary_url, width):
    context = browser.new_context(viewport={"width": width, "height": 844}, is_mobile=True, has_touch=True)
    try:
        page = context.new_page()
        page.goto(f"{dictionary_url}/?tag=communication")
        cards = page.get_by_role("article")
        expect(cards).to_have_count(4)
        expect(page.get_by_role("button", name=re.compile("^Escuchar:"))).to_have_count(2)
        assert page.evaluate("document.documentElement.scrollWidth") <= width
        positions = [card.bounding_box() for card in cards.all()]
        assert all(position is not None for position in positions)
        assert all(second["y"] >= first["y"] + first["height"] for first, second in zip(positions, positions[1:]))
        for button in page.get_by_role("button", name=re.compile("^Escuchar:")).all():
            rect = button.bounding_box()
            assert rect is not None and 0 <= rect["x"] < rect["x"] + rect["width"] <= width
    finally:
        context.close()


def test_listen_loads_expected_clip_and_toggles_playback(page, dictionary_url):
    page.add_init_script("""
        window.Audio = class extends window.Audio {
          constructor(...args) {
            super(...args);
            window.testAudio = this;
            this.addEventListener("playing", () => { window.testAudioPlayed = true; });
          }
        };
        """)
    page.goto(f"{dictionary_url}/?tag=communication")
    phrase = "ქართული არ ვიცი."
    button = page.get_by_role("button", name=f"Escuchar: {phrase}", exact=True)
    expect(button).to_have_attribute("aria-pressed", "false")
    expected_path = f"/static/audio/{clip_name(phrase)}"
    with page.expect_response(lambda response: urlparse(response.url).path == expected_path) as pending:
        button.click()
    assert pending.value.ok
    expect(button).to_have_attribute("aria-pressed", "true")
    page.wait_for_function("window.testAudioPlayed === true")
    button.click()
    expect(button).to_have_attribute("aria-pressed", "false")
    assert page.evaluate("window.testAudio.paused")
    expect(page.get_by_role("status")).to_be_empty()


def test_audio_boost_routes_playing_clip_through_gain_and_back(page, dictionary_url):
    page.add_init_script("""
        const connect = AudioNode.prototype.connect;
        AudioNode.prototype.connect = function (destination, ...args) {
          if (this instanceof MediaElementAudioSourceNode) {
            window.testAudioRoute = {
              kind: destination.constructor.name,
              gain: destination.gain?.value,
            };
          }
          return connect.call(this, destination, ...args);
        };
        """)
    page.goto(f"{dictionary_url}/?tag=communication")
    boost = page.get_by_role("button", name="Amplificar audio", exact=True)
    expect(boost).to_have_attribute("aria-pressed", "false")
    listen = page.get_by_role("button", name="Escuchar: ქართული არ ვიცი.", exact=True)
    listen.click()
    expect(listen).to_have_attribute("aria-pressed", "true")

    boost.click()
    expect(boost).to_have_attribute("aria-pressed", "true")
    page.wait_for_function("window.testAudioRoute?.kind === 'GainNode' && window.testAudioRoute.gain === 3")

    boost.click()
    expect(boost).to_have_attribute("aria-pressed", "false")
    page.wait_for_function("window.testAudioRoute?.kind === 'AudioDestinationNode'")
    expect(listen).to_have_attribute("aria-pressed", "true")
    listen.click()
    expect(listen).to_have_attribute("aria-pressed", "false")
    expect(page.get_by_role("status")).to_be_empty()
