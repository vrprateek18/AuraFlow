import SwiftUI
import AuraMotionCore

public struct HUDView: View {
    @State private var snapshot: HUDSnapshot?
    @State private var isCompact = false

    public init() {}

    public var body: some View {
        VStack(spacing: 8) {
            // Header Bar
            HStack {
                Circle()
                    .fill(statusColor)
                    .frame(width: 8, height: 8)
                Text("AuraFlow")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(.white.opacity(0.9))

                Spacer()

                Button(action: { isCompact.toggle() }) {
                    Image(systemName: isCompact ? "chevron.down" : "chevron.up")
                        .font(.system(size: 9))
                        .foregroundColor(.white.opacity(0.6))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 10)
            .padding(.top, 8)

            // Status Pill
            HStack {
                Text(snapshot?.feedback ?? snapshot?.state.displayName ?? "INITIALIZING")
                    .font(.system(size: 10, weight: .bold, design: .rounded))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(statusColor.opacity(0.25))
                    .foregroundColor(statusColor)
                    .cornerRadius(6)

                Spacer()

                if let p95 = snapshot?.performance.inferenceDurationP95Ms {
                    Text(String(format: "%.1f ms", p95))
                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                        .foregroundColor(.white.opacity(0.7))
                }
            }
            .padding(.horizontal, 10)

            if !isCompact {
                // Live Hand Skeleton Canvas
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.black.opacity(0.4))
                        .frame(height: 140)

                    if let sample = snapshot?.sample {
                        SkeletonView(sample: sample)
                            .frame(height: 130)
                    } else {
                        VStack(spacing: 4) {
                            Image(systemName: "hand.raised.slash")
                                .font(.system(size: 20))
                                .foregroundColor(.white.opacity(0.3))
                            Text("No Hand Detected")
                                .font(.system(size: 10))
                                .foregroundColor(.white.opacity(0.4))
                        }
                    }
                }
                .padding(.horizontal, 10)

                // Telemetry Footer
                HStack(spacing: 12) {
                    MetricLabel(title: "CAP", value: String(format: "%.0f", snapshot?.performance.captureFPS ?? 0))
                    MetricLabel(title: "INF", value: String(format: "%.0f", snapshot?.performance.inferenceFPS ?? 0))
                    MetricLabel(title: "DROP", value: "\(snapshot?.performance.droppedFrames ?? 0)")
                    Spacer()
                    if let permissionLabel = snapshot?.permissions.compactStatusLabel {
                        Text(permissionLabel)
                            .font(.system(size: 8, weight: .bold))
                            .foregroundColor(.orange)
                    }
                }
                .padding(.horizontal, 10)
                .padding(.bottom, 8)
            }
        }
        .frame(width: 220)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.white.opacity(0.12), lineWidth: 1)
                )
        )
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("HUDSnapshotUpdated"))) { note in
            if let snap = note.object as? HUDSnapshot {
                self.snapshot = snap
            }
        }
    }

    private var statusColor: Color {
        guard let state = snapshot?.state else { return .gray }
        switch state {
        case .pointer: return .cyan
        case .pinchArmed: return .yellow
        case .dragging: return .orange
        case .scrolling: return .purple
        case .clutch: return .blue
        case .paused: return .red
        case .trackingLost: return .pink
        case .idle, .scrollCandidate: return .gray
        case .palmCandidate: return .yellow
        case .palmRest: return .teal
        case .palmSwipeLeft, .palmSwipeRight: return .green
        }
    }
}

struct MetricLabel: View {
    let title: String
    let value: String

    var body: some View {
        HStack(spacing: 2) {
            Text(title)
                .font(.system(size: 8, weight: .semibold))
                .foregroundColor(.white.opacity(0.4))
            Text(value)
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(.white.opacity(0.8))
        }
    }
}

struct SkeletonView: View {
    let sample: HandSample

    // Bone connections
    private let bones: [(HandJointName, HandJointName)] = [
        (.wrist, .thumbCMC), (.thumbCMC, .thumbMP), (.thumbMP, .thumbIP), (.thumbIP, .thumbTip),
        (.wrist, .indexMCP), (.indexMCP, .indexPIP), (.indexPIP, .indexDIP), (.indexDIP, .indexTip),
        (.wrist, .middleMCP), (.middleMCP, .middlePIP), (.middlePIP, .middleDIP), (.middleDIP, .middleTip),
        (.wrist, .ringMCP), (.ringMCP, .ringPIP), (.ringPIP, .ringDIP), (.ringDIP, .ringTip),
        (.wrist, .littleMCP), (.littleMCP, .littlePIP), (.littlePIP, .littleDIP), (.littleDIP, .littleTip),
        (.indexMCP, .middleMCP), (.middleMCP, .ringMCP), (.ringMCP, .littleMCP)
    ]

    var body: some View {
        GeometryReader { geo in
            Path { path in
                for (fromName, toName) in bones {
                    if let fromPt = sample.joint(fromName, minConfidence: 0.2),
                       let toPt = sample.joint(toName, minConfidence: 0.2) {
                        let p1 = convert(fromPt, size: geo.size)
                        let p2 = convert(toPt, size: geo.size)
                        path.move(to: p1)
                        path.addLine(to: p2)
                    }
                }
            }
            .stroke(
                LinearGradient(
                    colors: [Color.cyan.opacity(0.8), Color.purple.opacity(0.8)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ),
                lineWidth: 2
            )

            // Landmarks
            ForEach(HandJointName.allCases, id: \.self) { name in
                if let pt = sample.joint(name, minConfidence: 0.25) {
                    Circle()
                        .fill(name == .indexTip || name == .thumbTip ? Color.yellow : Color.cyan)
                        .frame(width: name == .indexTip ? 6 : 4, height: name == .indexTip ? 6 : 4)
                        .position(convert(pt, size: geo.size))
                }
            }
        }
    }

    private func convert(_ pt: CGPoint, size: CGSize) -> CGPoint {
        // Vision coordinates: [0, 1] bottom-left origin
        return CGPoint(x: pt.x * size.width, y: (1.0 - pt.y) * size.height)
    }
}
