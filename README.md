# CD Background Studio v0.2.0

An independent Windows utility to **apply a wallpaper visually to the Creative Destruction lobby while the game is running**, using an optional, click-through on-screen overlay. It follows the **blue-marked sky/background region** in the supplied reference and cuts out the player, the UI, the platform and foreground props.

### Important distinction

**Live Apply = desktop overlay, NOT a 3D asset replacement.** The overlay uses a static mask, so character animations can expose a little of the original scenery near their edges. The wallpaper is clipped to the approximate blue outline and transparent everywhere else. The actual game environment, lighting, 3D geometry and scene resources remain unchanged. The app **does not inject into the game, modify its files, or bypass anti-cheat**. Some games disallow third-party overlays or do not render them above exclusive fullscreen; verify your server's rules.

## Quick start (Windows 10/11)

1. Download `CD-Background-Studio.exe` from [Releases](https://github.com/samimustafaa/background-changer-cd/releases).
2. Start Creative Destruction in **windowed or borderless** mode (not exclusive fullscreen).
3. Open CD Background Studio, click **Choose wallpaper**, select a PNG/JPG/WEBP/BMP (4K supported).
4. Leave **Game EXE** as `client.exe` unless your actual game EXE has a different name.
5. Click **APPLY TO LOBBY (LIVE)**, then switch to the game window.
6. The wallpaper appears clipped to the marked **background area** when the game is focused; it hides when you alt-tab away.
7. Click **REMOVE LIVE BACKGROUND** to turn it off. You can import a lobby screenshot and use the Keep Original / Show Wallpaper brushes to refine the transparent protection mask; press Apply again after editing.

**Lobby-only safeguard:** enabled by default; checks that the yellow **Start** button is visible near the bottom-right of the lobby. When you start a match or leave the lobby, the overlay hides. If your lobby uses a different UI and it doesn't activate, turn off **Auto-hide outside lobby**. With this toggle off you must remove the overlay manually before gameplay.

**How the blue selection works:** the overlay uses a normalized, approximate trace of the user's blue-marked region from the provided screenshot. It preserves the live character/UI by leaving those pixels *completely transparent* so the game shows through. Different skins, poses, resolutions or a different lobby design may require mask adjustments.

**Limitations:** 16:9 composition only; supports borderless/windowed on Windows. You should test in your own environment; this release's live overlay was not verified against a running Creative Destruction client. It may not appear in exclusive fullscreen or when games block overlays. Automatic lobby detection is a heuristic.

## Extras

- Preview what parts of the screenshot would receive the background image.
- Offline export: `wallpaper_4k.png` (3840×2160), `lobby_preview.png`, `protection_mask.png`, and `pack_info.json`.
- Manual check for newer GitHub releases (no silent updater).

## Python installation

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 cd_background_studio.py
```

## Build the Windows .exe

```powershell
py -3.12 -m pip install -r requirements.txt pyinstaller pytest
py -3.12 -m pytest -q
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name CD-Background-Studio cd_background_studio.py
```

The GitHub Actions workflow builds and attaches the executable to the tagged release.

## True background asset replacement (future)

A genuine **in-engine** change behind the animated player, rather than a screen-space approximation, requires **supported lobby asset replacement tools/documentation** from the game/server owner. Please provide the permitted lobby image/texture files or documented mod interface and the client version. An owner's permission does not automatically mean an anti-cheat exemption. We won't add bypasses.

This fan-made utility is not affiliated with Creative Destruction.
