# Building a Windows Installer for Universal POS

This guide walks you through turning the Universal POS Python project into a
single **`UniversalPOS_Setup.exe`** file that you can copy to a USB drive,
send over the network, or upload somewhere — and install on any Windows
computer **without that computer needing Python installed at all.**

There are two stages:

1. **PyInstaller** — bundles Python + your code + all dependencies into a
   standalone folder with a `UniversalPOS.exe` inside it.
2. **Inno Setup** — wraps that folder into a proper installer with a setup
   wizard, Start Menu shortcuts, a desktop icon, and an uninstaller.

You only need to do this on **one** computer (your "build machine" — the one
with PyCharm where you've been developing). The resulting `UniversalPOS_Setup.exe`
is what you copy to other computers.

---

## Part 1 — Prepare your build machine

### Step 1.1 — Confirm your project runs normally first

Before building anything, make sure `main.py` still runs fine as usual in
PyCharm (right-click → Run). If it doesn't, fix that first — PyInstaller will
faithfully bundle whatever bugs exist too.

### Step 1.2 — Install PyInstaller

Open the PyCharm terminal (make sure it shows your project's venv is active —
you should see something like `(universal_pos)` or `(.venv)` at the start of
the prompt) and run:

```
pip install -r requirements-dev.txt
```

This installs PyInstaller into your virtual environment.

### Step 1.3 — Confirm the icon and spec files are present

Your project folder should now contain (in addition to the usual `.py`
files):

```
assets/icon.ico          ← the app icon
UniversalPOS.spec        ← PyInstaller build configuration
build_exe.bat             ← one-click build script
installer.iss              ← Inno Setup script
requirements-dev.txt
```

If any of these are missing, re-download the latest project zip.

---

## Part 2 — Build the standalone EXE with PyInstaller

### Step 2.1 — Run the build

In the PyCharm terminal (venv active, in your project folder), run:

```
build_exe.bat
```

(Or double-click `build_exe.bat` directly in File Explorer.)

This runs PyInstaller using the pre-configured `UniversalPOS.spec` file,
which already handles the trickiest part of bundling a `customtkinter` app —
making sure its internal theme and font files get included. (A plain
`pyinstaller main.py` without this spec often produces an app that launches
to a blank or broken window, because those asset files get silently skipped.)

This takes anywhere from 30 seconds to a few minutes depending on your PC.
Note: with the camera-barcode-scanning and report-export features, the
bundled app now includes OpenCV, PDF/Word/Excel libraries, and printer
support — so the build takes noticeably longer than a minimal app (a few
minutes is normal) and the output folder will be roughly 200–400 MB instead
of a few dozen MB. This is expected and not a sign anything went wrong.
You'll see a lot of scrolling text — that's normal.

### Step 2.2 — Check for a successful build

When it finishes, you should see:

```
Build complete! Output is in: dist\UniversalPOS
```

And a new folder structure will appear:

```
dist/
└── UniversalPOS/
    ├── UniversalPOS.exe     ← the actual program
    └── _internal/           ← all bundled dependencies (DLLs, Python runtime, etc.)
```

### Step 2.3 — Test the standalone EXE *before* making an installer

This step matters — test now while it's easy to fix, rather than after
distributing a broken installer to five computers.

1. Double-click `dist\UniversalPOS\UniversalPOS.exe`.
2. The Universal POS login screen should appear, exactly like it does when
   you run it from PyCharm.
3. Log in, ring up a test sale, check that the receipt saves properly.
4. Close the app, then check that a `UniversalPOS` folder was created under
   `C:\Users\<YourName>\AppData\Local\` containing `pos_system.db` and a
   `receipts` folder. (This is the per-user data folder — separate from the
   Program Files install — so multiple users on the same PC, or reinstalls,
   never lose sales data.)

If it opens and works, you're ready for Part 3. If it crashes immediately,
see the **Troubleshooting** section at the bottom before continuing.

---

## Part 3 — Install Inno Setup (one-time setup)

Inno Setup is a free, widely-used tool for building Windows installers. You
only need to install this once on your build machine.

1. Go to **https://jrsoftware.org/isdl.php**
2. Download the latest **"Inno Setup"** installer (not "Inno Download
   Plugin" or anything else — just the main installer, usually named
   something like `innosetup-6.x.x.exe`).
3. Run it and click through the setup wizard with default options (Next →
   Next → Install → Finish). No special configuration needed.

---

## Part 4 — Compile the installer

### Step 4.1 — Open the Inno Setup script

1. Launch **Inno Setup Compiler** from your Start Menu.
2. File → Open → navigate to your project folder → select `installer.iss`.

### Step 4.2 — Review the settings (optional but recommended)

Near the top of the file you'll see:

```
#define MyAppName "Universal POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Universal POS"
```

Feel free to edit these — for example, change `MyAppPublisher` to your own
name or your store's name, and bump `MyAppVersion` each time you rebuild
(e.g. `"1.1.0"`) so you can tell installer versions apart later.

### Step 4.3 — Compile

Click **Build → Compile** (or press `Ctrl+F9`, or click the green "Play"-style
▶ button in the toolbar).

Inno Setup will read your `dist\UniversalPOS` folder (built in Part 2) and
package everything into a single installer file.

### Step 4.4 — Find your installer

When compiling finishes, you'll find:

```
installer_output/
└── UniversalPOS_Setup.exe
```

**This one file is your complete, distributable installer.** It contains
everything needed to run Universal POS — no internet connection, no Python
installation, and no PyCharm required on the target computer.

---

## Part 5 — Install on another computer

1. Copy `UniversalPOS_Setup.exe` to the target computer (USB drive, shared
   folder, email, cloud drive — however you'd normally transfer a file).
2. Double-click it to run.
3. Windows may show a **SmartScreen warning** ("Windows protected your PC")
   because the installer isn't digitally signed with a paid certificate —
   this is expected and normal for small/independent software. Click
   **"More info"** → **"Run anyway"** to proceed.
4. Follow the setup wizard: choose whether to create a desktop icon, then
   click **Install**. Administrator permission will be requested (normal,
   since it installs into Program Files).
5. When finished, click **Finish** — the app can launch immediately, or
   later via the Start Menu / desktop shortcut.
6. Log in with the default accounts (`admin` / `admin123` or `cashier` /
   `cashier123`) and change the passwords right away, per the main README.

Each computer gets its own independent database (stored per-user under
`%LOCALAPPDATA%\UniversalPOS\`), so sales data does **not** sync between
computers automatically — this is a standalone single-terminal installer,
not a networked multi-terminal system.

---

## Updating the app later

When you make code changes and want to push out an updated version:

1. Repeat Part 2 (rebuild with `build_exe.bat`) and Part 4 (recompile with
   Inno Setup) — bump `MyAppVersion` in `installer.iss` first.
2. Distribute the new `UniversalPOS_Setup.exe` the same way.
3. Running the new installer over an existing install will update the
   program files automatically. Because the database lives in
   `%LOCALAPPDATA%`, **existing sales data, users, and settings are
   preserved** across the update — only the program itself gets replaced.

---

## Troubleshooting

**"Camera Scan" says no camera found even though this PC has a webcam.**
Windows may be blocking camera access at the OS level. Check Settings →
Privacy & security → Camera, and make sure "Let desktop apps access your
camera" is turned on. Also close any other app that might be using the
camera (video call apps, other scanner software) — most webcams only allow
one program to use them at a time.

**The standalone EXE (Step 2.3) closes instantly / does nothing when
double-clicked.**
Open Command Prompt, `cd` into the `dist\UniversalPOS` folder, and run
`UniversalPOS.exe` directly from there instead of double-clicking. This
keeps the window open so you can actually read the error message, and tells
us what's actually failing.

**"Failed to execute script main" or a missing-module error during Step 2.3.**
A dependency wasn't picked up by PyInstaller. Open `UniversalPOS.spec`, find
the `hiddenimports=[...]` line, and add the missing module name to that
list (ask if you're not sure which one), then rebuild.

**Antivirus deletes or flags `UniversalPOS.exe` right after building.**
This is a well-known false positive with PyInstaller-built executables
(some antivirus engines are suspicious of any single .exe that bundles a
whole Python runtime). Add an exclusion for your project's `dist` folder in
your antivirus settings, or submit the file to your antivirus vendor as a
false positive.

**SmartScreen or antivirus blocks `UniversalPOS_Setup.exe` on the target
computer.**
Same cause as above, just at the installer stage instead of the exe stage.
"Run anyway" after clicking "More info" is the normal workaround for
unsigned installers. If you plan to distribute this widely, look into
getting a code-signing certificate to remove this warning permanently — but
for personal/small business use, this step is optional.

**The installed app opens but looks broken/blank (no buttons, wrong
colors).**
This means the `customtkinter` theme/asset files didn't get bundled. Make
sure you built using `UniversalPOS.spec` (via `build_exe.bat`), **not** a
plain `pyinstaller main.py` command — the spec file is what handles this
correctly.
