import SwiftUI
import AuraMotionCore

public struct DiagnosticsView: View {
    @State private var snapshot: HUDSnapshot?
    @State private var isRecording = false
    @State private var lastSavedURL: URL?
    @State private var cursorHistory: [CGPoint] = []

    public init() {}

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("System Telemetry & Diagnostics")
                .font(.headline)

            Divider()

            // Latency Metrics
            GroupBox(label: Text("Latency & Timing")) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Vision Inference p50:")
                        Spacer()
                        Text(String(format: "%.2f ms", snapshot?.performance.inferenceDurationP50Ms ?? 0))
                            .monospacedDigit()
                    }
                    HStack {
                        Text("Vision Inference p95:")
                        Spacer()
                        Text(String(format: "%.2f ms", snapshot?.performance.inferenceDurationP95Ms ?? 0))
                            .monospacedDigit()
                    }
                    HStack {
                        Text("Mailbox Wait Time:")
                        Spacer()
                        Text(String(format: "%.2f ms", snapshot?.performance.mailboxWaitMs ?? 0))
                            .monospacedDigit()
                    }
                    HStack {
                        Text("Capture → Vision result:")
                        Spacer()
                        Text(String(format: "%.2f ms", snapshot?.performance.pipelineToEventMs ?? 0))
                            .monospacedDigit()
                    }
                    if snapshot?.performance.isLatencyEstimated == true {
                        Text("* Presentation timestamp anchored to host arrival clock")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(4)
            }

            // Quality & System State
            GroupBox(label: Text("Cursor Stability")) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Horizontal motion: orange is raw; cyan is smoothed. Hold still to compare jitter.")
                        .font(.caption).foregroundStyle(.secondary)
                    Canvas { context, size in
                        guard cursorHistory.count > 1 else { return }
                        let values = cursorHistory.flatMap { [$0.x, $0.y] }
                        let low = (values.min() ?? 0) - 2
                        let span = max(10, (values.max() ?? 0) - low + 2)
                        for raw in [true, false] {
                            var path = Path()
                            for (i, value) in cursorHistory.enumerated() {
                                let position = CGPoint(x: CGFloat(i) / CGFloat(cursorHistory.count - 1) * size.width,
                                    y: size.height * (1 - ((raw ? value.x : value.y) - low) / span))
                                if i == 0 { path.move(to: position) } else { path.addLine(to: position) }
                            }
                            context.stroke(path, with: .color(raw ? .orange : .cyan), lineWidth: 1.5)
                        }
                    }.frame(height: 70)
                    Text(String(format: "Index confidence: %.0f%%", Double(snapshot?.sample?.joints[.indexTip]?.confidence ?? 0) * 100))
                        .font(.caption).monospacedDigit()
                }.padding(4)
            }

            GroupBox(label: Text("System Health")) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Thermal Quality Stage:")
                        Spacer()
                        Text("\(snapshot?.thermalStage.rawValue ?? 0)")
                    }
                    HStack {
                        Text("Dropped Frames:")
                        Spacer()
                        Text("\(snapshot?.performance.droppedFrames ?? 0)")
                    }
                    HStack {
                        Text("Physical Arbitration Tap:")
                        Spacer()
                        Text(snapshot?.isArbitrationActive == true ? "Active" : "Disabled/Cooldown")
                            .foregroundColor(snapshot?.isArbitrationActive == true ? .green : .orange)
                    }
                }
                .padding(4)
            }

            // Opt-in Landmark Recording
            GroupBox(label: Text("Landmark Recording (Privacy-Safe)")) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Records anonymized 2D joint coordinates for regression testing. No camera video is ever saved.")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    HStack {
                        Button(action: toggleRecording) {
                            Text(isRecording ? "Stop & Save Recording" : "Start Recording")
                        }
                        if isRecording {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 8, height: 8)
                            Text("Recording...")
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                    }

                    if let url = lastSavedURL {
                        Text("Saved to: \(url.lastPathComponent)")
                            .font(.caption2)
                            .foregroundColor(.green)
                    }
                }
                .padding(4)
            }

            Spacer()
        }
        .padding(20)
        .frame(width: 420, height: 640)
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("HUDSnapshotUpdated"))) { note in
            if let snap = note.object as? HUDSnapshot {
                self.snapshot = snap
                if let raw = snap.rawCursorLocation, let filtered = snap.cursorLocation {
                    cursorHistory.append(CGPoint(x: raw.x, y: filtered.x))
                    if cursorHistory.count > 90 { cursorHistory.removeFirst(cursorHistory.count - 90) }
                } else { cursorHistory.removeAll() }
            }
        }
    }

    private func toggleRecording() {
        let env = AppEnvironment.shared
        if isRecording {
            lastSavedURL = env.landmarkRecorder.stopAndSave()
            isRecording = false
        } else {
            env.landmarkRecorder.start()
            isRecording = true
            lastSavedURL = nil
        }
    }
}
