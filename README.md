# CD Background Studio

A dark-themed **offline Creative Destruction lobby wallpaper design utility** for Windows. Import a wallpaper (including 4K), import a lobby screenshot, protect the character/UI/platform with a paintable mask, preview the result, and export a 3840×2160 wallpaper pack.

> **Honest limitation:** This is a wallpaper **preview and export** tool, **not yet an in-game lobby background replacer**. No one can determine a safe, correct wallpaper asset patch from a lobby screenshot alone. It does not inject code, modify .npk archives, evade anti-cheat or alter your game files. Importing a lobby screenshot is optional.

## Features
- PNG, JPEG, BMP and WEBP wallpapers, exported at **3840×2160** with center crop to preserve aspect ratio.
- Lobby screenshot preview with an editable, approximate starter mask to preserve visible UI/player/platform pixels.
- Brush modes: **Keep original** / **Show wallpaper**; mouse wheel adjusts brush size.
- Undo and reset mask; scrollable control panel.
- Exports `wallpaper_4k.png`, `lobby_preview.png` and `protection_mask.png` (when a screenshot is provided), plus a `pack_info.json` explaining that this is an offline pack.
- Manual GitHub Release update check. No updater silently runs executables.
- No network access except when explicitly clicking **Check updates**.

## Running from Python
Install Python 3.11+ and run:

```powershell
python -m pip install -r requirements.txt
python cd_background_studio.py
```

## Windows executable
Download the `CD-Background-Studio.exe` attached to [Releases](https://github.com/samimustafaa/background-changer-cd/releases), once the build succeeds.

Build locally (Windows):

```powershell
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name CD-Background-Studio cd_background_studio.py
```

## What's needed for real in-game integration?
1. Official confirmation that **lobby background asset replacement** is supported (a permission to mod does not guarantee anti-cheat compatibility).
2. The **unmodified source assets** for the game's lobby background (or official modding interface and instructions) and a list of specifically editable asset paths.
3. The Creative Destruction client build/version and offline installation folder.

Once a supported offline method is verified, **Apply while game is closed**, **Backup**, and **Restore** workflows can be added. This project will not bypass security systems or write to running game memory.

## Notes
The starter mask is a rough fit for the supplied lobby screenshot, not automatic pixel-perfect segmentation. Manually refine the character, weapon, UI and platform.
Large 4K PNGs take memory and disk space.
This is an independent fan utility and is not affiliated with Creative Destruction.
