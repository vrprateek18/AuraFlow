import SwiftUI
import AuraMotionCore

struct MovementCalibrationView: View {
    @State private var session = MovementCalibration()
    @State private var started = false
    @State private var collecting = false
    @State private var notice = ""
    var body: some View {
        VStack(spacing: 16) {
            Text("Personalize Cursor Movement").font(.title2)
            Text("Three short recordings learn your resting tremor and movement speeds. Control pauses during setup; camera video is not saved.")
                .font(.callout).foregroundStyle(.secondary)
            if !started {
                Button("Start movement setup") {
                    session = MovementCalibration(); notice = ""; started = true
                    AppEnvironment.shared.setCalibrationActive(true)
                }
            } else if !session.isComplete {
                Text("Step \(session.step.rawValue + 1) of 3").font(.headline)
                Text(session.step.instruction)
                ProgressView(value: Double(session.count), total: 60)
                Text("\(session.count) / 60 clear observations").font(.caption)
                if let message = session.message { Text(message).foregroundStyle(.orange) }
                Button(collecting ? "Recording…" : "Record this movement") { collecting = true }
                    .disabled(collecting)
            } else {
                Text("Your movement profile is ready.")
                Button("Save movement profile") {
                    let env = AppEnvironment.shared
                    guard let profile = session.applying(to: env.currentCalibration) else { return }
                    env.updateCalibration(profile)
                    finish()
                    notice = "Saved. Your personalized cursor response is active."
                }
            }
            if started { Button("Cancel") { finish() } }
            if !notice.isEmpty { Text(notice).font(.callout) }
        }
        .padding(24).frame(width: 440, height: 390)
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("HUDSnapshotUpdated"))) { note in
            guard collecting, let snapshot = note.object as? HUDSnapshot, let sample = snapshot.sample else { return }
            if session.add(sample) { collecting = false }
        }
        .onDisappear { finish() }
        .onReceive(NotificationCenter.default.publisher(for: NSWindow.willCloseNotification)) { note in
            let title = (note.object as? NSWindow)?.title
            if title == "AuraFlow Movement Calibration" || title == "AuraMotion Movement Calibration" { finish() }
        }
    }
    private func finish() {
        guard started else { return }
        collecting = false; started = false
        AppEnvironment.shared.setCalibrationActive(false)
    }
}
