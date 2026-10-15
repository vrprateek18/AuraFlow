# Gesture responsiveness corrections

## Whole-hand stabilization and movement setup

Validation: all 104 tests pass, including whole-hand translation, fingertip
wobble, pinch articulation, calibration persistence/rejection, and scroll-entry
confirmation. Live camera comfort and accuracy still require user testing.

- Cursor tracking combines a confident palm/knuckle centroid with a smoothly
  learned fingertip offset. Thumb-index contact and two-finger scrolling freeze
  the offset so finger articulation does not become cursor translation.
- Palm landmark-set changes and hand identity changes re-anchor the fusion;
  missing or low-confidence fingertip observations cannot steer it.
- Two-finger scroll entry requires consistent observations for 40 ms; brief
  ambiguous scroll poses freeze output for up to 80 ms. Explicit index pointing
  still stops scrolling immediately.
- Menu bar → Movement Calibration records still, slow, and quicker movements.
  Each stage needs 60 clear samples. Saved profiles tune rest stability and speed
  response; existing click/copy/paste thresholds remain intact. Cancel/close
  restores the previous pause state. No video is saved by calibration.
- Diagnostics includes a raw-versus-filtered horizontal cursor trace and fingertip
  confidence. Timing is labelled Capture → Vision result because it excludes
  output-queue and display delay.

## Cursor refinement

- Stronger adaptive smoothing at rest and a 1.25-point soft radial dead zone
  reduce small hand tremors while retaining accumulated slow movement.
- Large one-frame fingertip jumps require a confirming nearby observation.
- Cursor tracking requires fingertip confidence of at least 0.45, and brief
  missing observations preserve the filter instead of restarting it.
- Output preserves quarter-point movement instead of one-point steps.
- All 98 tests pass. Synthetic cursor regressions cover resting noise at 30/60
  FPS, slow aiming, fast movement, isolated spikes, and brief occlusion.
  These checks do not measure live-camera performance.

## Final interaction corrections

- Cursor movement requires an extended index finger on every pointer frame, and
  the clutch now observes pose loss after activation.
- A stable thumb-index contact clicks after 45 ms while still held. Release does
  not click again. Holding and moving can subsequently start dragging.
- The command-menu pointer is adaptively smoothed; tile boundaries have a small
  margin to prevent selection flicker from hand tremor.
- HUD visibility and click-ripple settings now drive their actual windows.
- Sleep/wake state changes are serialized with gesture processing.

## Hand command menu

Hold an open palm still for about 0.9 seconds to open the command menu. Raise your
index finger, move your hand to highlight a tile, then pinch thumb and index for
80 ms to confirm. Lower or withdraw the hand to cancel; the menu also closes after
12 seconds. Normal palm swipes continue to switch apps.

The nine commands are Right click, Double click, All windows (Mission Control),
Previous app, Next app, Minimize, Full screen, Left half, and Right half. Clicks
target the cursor location before opening the menu. The menu does not take keyboard
focus and does not inject cursor movement while selecting a command.

The menu also dismisses immediately when tracking sees a folded/lowered hand, so
it cannot remain as a stale overlay while the user returns to a neutral pose.

Window halves use Accessibility and the display's usable bounds, excluding the
menu bar and Dock. Apps may impose minimum sizes or not permit window resizing;
the HUD reports requests that cannot be applied. Mission Control, minimize, and
full-screen actions use standard macOS shortcuts and depend on app/system support:
https://support.apple.com/en-au/102650

Input permission checks, arbitration, drag exclusion, and epoch validation apply
to menu commands. Contact must release before it can become a normal click again.
User testing with a live hand is still needed to assess recognition and comfort.

## Personal calibration and temporal confirmation

- Open the menu-bar **Calibration…** window and choose **Start guided setup**.
  Record six poses (apart and touching for index, middle, and ring), then save.
  Each step requires 30 clear landmark samples. Control pauses during setup and
  restores its previous pause state on save, cancel, or closing the window.
- The profile stores separate Click, Copy, and Paste contact/release thresholds.
  Shaky or overlapping poses cannot replace the existing profile. Old profiles
  remain readable. Only derived thresholds are saved; no new recordings occur
  without starting the guided setup.
- Copy/Paste require at least two consistent frames over 60 ms for contact and
  release. Missing landmarks do not count as a release. Click rejects contacts
  shorter than 45 ms. This deliberately filters momentary false detections.
- The HUD identifies recognized Click/Copy/Paste/swipes and reports permission,
  calibration, and mouse-arbitration blocking. Recognition does not claim that
  the receiving app executed the command.
- Validation: 95 tests pass, covering calibration separation, persistence,
  compatibility, interrupted observation, contact clicking, folded-hand stopping,
  menu boundary stability, and noisy contact/release regressions. The updated
  release app has been built and its code signature verified.
  Live-camera accuracy still requires the user's calibration and real examples.

- Two extended fingers with a raised thumb now classify as scroll, rather than palm.
- Finger curl checks use hand-relative distances and returning fingertip geometry.
- Copy/Paste choose the closest contacting fingertip. Held contacts suppress pointer,
  scrolling, and palm actions; shortcut detection cannot interrupt an active drag.
- Returning to pointing immediately stops scroll momentum.
- Slow scroll movement is preserved after activation; the detector now actually uses
  the intended 1.8x default gain rather than overriding it with 3.2x.
- Cursor filtering uses consecutive raw positions for velocity and camera timestamps
  for timing, rejects out-of-order samples, and resets after long gaps.
- Missing index landmarks no longer switch cursor tracking to the palm center.
- Hand reacquisition delay is 80 ms; HUD updates are limited to 30 per second.
- Camera selection prefers smaller frames at equal usable frame rates.
- Disabled output cancels active gestures; scroll coalescing cannot combine epochs.

Earlier regression validation covered 72 automated tests, including realistic two-finger-to-pointer,
held Copy, subpixel scroll, and filter timestamp regression tests. These tests verify
software behavior; they do not establish live-camera recognition accuracy or measured
end-to-end latency. Click now uses confirmed contact, with sustained pinch for drag.
