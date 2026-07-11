# SmartCrop Pro — How It Works

SmartCrop Pro is a desktop app for cropping and cleaning up photos of objects
or documents. It has three main files, and each one has a clear, separate job.
This document explains what each file does and how they work together, aimed
at someone new to reading code.

## The Big Picture

Think of the app like a restaurant:

- **main.py** is the front door. It checks that the kitchen has everything it
  needs before opening, then lets people in.
- **app.py** is the dining room and the waiter. It's everything you see and
  click on — buttons, image previews, sliders — and it takes your order.
- **processor.py** is the kitchen. It doesn't know anything about buttons or
  windows; it just takes an image in, does the actual image processing work,
  and hands a finished image back.

```
main.py  --launches-->  app.py (the window)  --calls-->  processor.py (the logic)
```

None of the actual cropping or background removal happens in main.py or
app.py. Those two files are only concerned with showing a window and reacting
to clicks. All the real image processing lives in processor.py.

---

## main.py — The Starting Point

This is the file you run to start the program (`python main.py`). It does
three simple things, in order:

1. **Checks dependencies.** Before anything else, `check_dependencies()` tries
   to import the libraries the app needs (PyQt for the window, OpenCV and
   numpy for image processing, Pillow for image handling). If something is
   missing, it prints a friendly message telling you what to install with
   `pip install ...` and exits, instead of crashing with a confusing error
   later on.

2. **Imports the app window.** Once it knows the dependencies exist, it
   imports `SmartCropApp` from `app.py`. This import happens *after* the
   dependency check on purpose — if it happened first and PyQt was missing,
   the program would crash immediately with a hard-to-read error.

3. **Creates and shows the window.** It creates a `QApplication` (required by
   PyQt for any GUI to run), creates a `SmartCropApp` window, shows it, and
   hands control over to Qt's event loop (`app.exec()`), which is what keeps
   the window open and responsive to clicks until you close it.

This file also quietly supports two versions of the PyQt library (PyQt6 or
PyQt5) — it tries PyQt6 first, and falls back to PyQt5 if that's not
installed. You'll see this same fallback pattern repeated in app.py.

---

## app.py — The User Interface

This file builds everything you see on screen and connects it to actions.
It's the largest file because a GUI has a lot of small pieces, but it's built
from a few repeating ideas:

**Reusable widgets.** Near the top of the file are small custom UI pieces
used throughout the app:
- `ImgLabel` — a box that displays an image and shows a placeholder text when
  empty.
- `DropZone` — a box you can drag-and-drop an image file onto.
- `Canvas` — the interactive drawing area used for Manual Crop mode, where
  you click to place points and trace an outline around an object.

**Three modes.** The app supports three ways of cropping an image, chosen
with the mode buttons on the left:
- **Mode 1 — Smart Crop:** Automatically detects an object or document and
  crops it out, straightening it if it was photographed at an angle.
- **Mode 2 — Remove Background:** Uses AI to cut an object out and make the
  background transparent.
- **Mode 3 — Manual Crop:** You draw the outline yourself by clicking points
  around the object, and the app fits a precise crop to your outline.

**Background workers.** Image processing can take a second or two, and doing
it directly in a button's click handler would freeze the whole window while
it works. To avoid that, the app uses a `Worker` class that runs the
processing on a separate thread. When it finishes, it "signals" back to the
main window with the result, and the window updates the preview. This is why
you see a progress bar while an image is processing instead of the app
appearing frozen.

**Wiring.** The `_wire()` method is where buttons get connected to the
functions that should run when you click them — for example, clicking
"Process" calls `_process()`, which picks the right processor.py function
based on the current mode and hands it off to a Worker.

Importantly, **app.py never processes an image itself.** Every button that
does real work (`Process`, `Confirm & Crop`, `Preview CFAD Detection`) simply
calls a function imported from `processor.py` and displays whatever comes
back.

---

## processor.py — The Image Processing Engine

This is where the actual computer-vision work happens, using OpenCV
(`cv2`) and Pillow. It has no idea a GUI exists — you could delete app.py
entirely and still use these functions from a plain script. The key
functions, grouped by what they do:

### Converting between image formats
`pil_to_cv2` / `cv2_to_pil` — Pillow (PIL) and OpenCV represent images
differently internally, so the code constantly converts between the two
formats depending on which library's tools it needs for a given step.

### Mode 1: Smart Crop — `auto_crop_document()`
This is the most involved part of the file. The core idea is called **CFAD**
(Color Frequency Anomaly Detection), and the intuition behind it is simple:

> In most photos, the background is made of a few colors that repeat a lot
> (a desk, a wall, a sheet of paper). The object you're photographing is
> usually made of colors that are comparatively rare in the image. So: group
> pixels by color, treat the most common colors as "background," and treat
> the leftover, less common colors as "the object."

To make this reliable, the code doesn't rely on color alone. It also runs a
saliency detector (a model that guesses which part of an image draws the
eye) and a watershed segmentation (a classic technique that separates
touching regions), then blends all three results together and refines the
edges with GrabCut (an algorithm that iteratively improves a rough
foreground/background guess). This layered approach is what makes detection
work across very different kinds of photos.

Once the object's outline is found:
- If it looks like a four-cornered shape (like a document or a card),
  `_four_point_warp()` mathematically "unwarps" it into a perfectly
  rectangular, straight-on view — this is what makes a photo taken at an
  angle look like a flat scan.
- Otherwise, it just crops tightly around the detected shape.
- If detection fails entirely, it falls back to a simple border crop so the
  app never just gives up with an error.

`get_cfad_debug_overlay()` is a helper used by the "Preview CFAD Detection"
button — it draws the detected outline in color on top of the original image
so you can see what the algorithm found before committing to a crop.

### Mode 2: Remove Background — `remove_background()`
This mode hands the image to `rembg`, a separate AI library built for
background removal, and returns an image with a transparent background. If
`rembg` isn't installed, it automatically falls back to a GrabCut-based
approximation (`_grabcut_rembg`) so the feature degrades gracefully instead
of breaking.

### Mode 3: Manual Crop — `manual_polygon_crop()`
When you click points around an object yourself, this function takes those
rough points and refines them:
1. It fills the polygon you drew to make a rough mask.
2. It runs GrabCut using your rough mask as a starting hint, which lets the
   algorithm snap to the object's real edges instead of your imprecise
   clicks.
3. It cleans up the resulting mask (removing stray specks, smoothing edges)
   and crops to it.

If you clicked exactly 4 points, it treats it like a document corner and
applies the same perspective-warp used in Mode 1.

### Finishing touches
- `enhance_image()` — applies denoising, contrast enhancement (CLAHE),
  brightness, contrast, sharpness, and saturation adjustments. This is the
  optional "cleanup" step applied after cropping in Modes 1 and 3.
- `upscale_image()` — resizes an image up, used for the "2x Upscale for
  print" option.
- `save_image()` — writes the final image to disk in whatever format and DPI
  you chose.

---

## Putting It All Together — A Typical Run

1. You run `python main.py`. It checks your dependencies, then opens the
   `SmartCropApp` window defined in app.py.
2. You drag in a photo. app.py's `DropZone` catches the drop and loads it
   into memory with Pillow.
3. You pick Mode 1 and click **Process**. app.py starts a background
   `Worker` that calls `auto_crop_document()` from processor.py.
4. processor.py analyzes the photo's colors and edges, finds the object,
   straightens it if needed, and returns the result.
5. The Worker signals app.py that it's done. app.py displays the result and
   re-enables the Save/Print buttons.
6. You click **Save Image**. app.py collects your chosen format and DPI and
   calls `save_image()` in processor.py to write the file.

At every step, app.py is only responsible for *asking* processor.py to do
work and *displaying* what comes back — the actual image intelligence lives
entirely in processor.py.

---

## Dependencies

- **PyQt6** (or PyQt5) — the GUI toolkit that draws the window
- **OpenCV** (`opencv-python`) — core image processing (color analysis, edge
  detection, GrabCut, perspective warping)
- **numpy** — numerical arrays that OpenCV operates on
- **Pillow** — general-purpose image loading/saving
- **rembg** + **onnxruntime** (optional) — enables AI background removal in
  Mode 2; without it, the app falls back to a simpler method automatically
