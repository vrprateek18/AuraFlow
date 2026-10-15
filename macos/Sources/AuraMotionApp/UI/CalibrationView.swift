import SwiftUI
import AuraMotionCore

public struct CalibrationView: View {
    @State private var profile = AppEnvironment.shared.currentCalibration
    @State private var session = PersonalCalibration()
    @State private var collecting = false
    @State private var started = false
    @State private var notice = ""

    public init() {}

    public var body: some View {
        VStack(spacing: 16) {
            Text("Personal Gesture Calibration")
                .font(.headline)

            Text("Six short recordings personalize Click, Copy and Paste. Gesture control pauses during setup. Camera video is never saved.")
                .font(.caption)
                .foregroundColor(.secondary)

            if !started {
                Button("Start guided setup") {
                    session = PersonalCalibration()
                    started = true
                    AppEnvironment.shared.setCalibrationActive(true)
                }
            } else if !session.isComplete {
                Text("Step \(session.step.rawValue + 1) of 6")
                    .font(.headline)
                Text(session.step.instruction)
                ProgressView(value: Double(session.count), total: 30)
                Text(collecting ? "Hold steady: \(session.count) / 30 clear samples" : "Get into position, then start recording.")
                    .font(.caption)
                if let message = session.message { Text(message).foregroundColor(.orange) }
                Button(collecting ? "Recording…" : "Record this pose") {
                    collecting = true
                }.disabled(collecting)
            } else {
                Text(notice).foregroundColor(.secondary)
                Button("Start again") {
                    session = PersonalCalibration(); notice = ""
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Cursor Gain:")
                    Slider(value: $profile.cursorGain, in: 0.5...2.5, step: 0.1)
                    Text(String(format: "%.1fx", profile.cursorGain))
                        .monospacedDigit()
                }

                HStack {
                    Text("Pinch Sensitivity:")
                    Slider(value: Binding(
                        get: { Double(profile.pinchStartThreshold) },
                        set: { profile.pinchStartThreshold = CGFloat($0) }
                    ), in: 0.15...0.45, step: 0.02)
                    Text(String(format: "%.2f", profile.pinchStartThreshold))
                        .monospacedDigit()
                }
            }
            .padding()

            Button(started ? "Save and finish" : "Save adjustments") {
                if started {
                    guard let learned = session.applying(to: profile) else {
                        notice = "Complete all six steps. If open and touching poses overlap, start again with your fingertips clearly separated for the open poses."
                        return
                    }
                    profile = learned
                }
                // Preserve a release margin when adjusting sensitivity manually.
                profile.pinchReleaseThreshold = max(profile.pinchReleaseThreshold, profile.pinchStartThreshold + 0.08)
                AppEnvironment.shared.updateCalibration(profile)
                AppEnvironment.shared.setCalibrationActive(false)
                started = false
                notice = "Calibration saved. Gesture control restored."
            }
            .disabled(started && !session.isComplete)
            .keyboardShortcut(.defaultAction)
            if started {
                Button("Cancel setup") {
                    collecting = false; started = false
                    AppEnvironment.shared.setCalibrationActive(false)
                }
            } else if !notice.isEmpty { Text(notice).font(.caption) }
        }
        .padding(20)
        .frame(width: 420, height: 560)
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("HUDSnapshotUpdated"))) { note in
            guard collecting, let snapshot = note.object as? HUDSnapshot, let sample = snapshot.sample else { return }
            if session.add(sample) {
                collecting = false
                if session.isComplete {
                    notice = session.applying(to: profile) != nil
                        ? "Your finger contacts are distinguishable. Save to use these thresholds."
                        : "Open and touching poses overlap. Start again and separate the fingertips more during the open steps."
                }
            }
        }
        .onDisappear {
            collecting = false
            AppEnvironment.shared.setCalibrationActive(false)
            started = false
        }
        .onReceive(NotificationCenter.default.publisher(for: NSWindow.willCloseNotification)) { note in
            guard let window = note.object as? NSWindow,
                  window.title == "AuraFlow Calibration" || window.title == "AuraMotion Calibration" else { return }
            collecting = false; started = false
            AppEnvironment.shared.setCalibrationActive(false)
        }
    }
}
