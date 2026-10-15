import Foundation
import CoreGraphics

/// Maintains primary hand tracking ID continuity via spatial-temporal proximity.
public final class IdentityContinuityTracker: @unchecked Sendable {
    private var lastKnownPosition: CGPoint?
    private var lastSeenTime: TimeInterval = 0
    private var currentTrackingID: Int = 1
    private let maxJumpDistance: CGFloat = 0.40 // normalized distance
    private let timeoutSeconds: TimeInterval = 1.0

    public init() {}

    public func reset() {
        lastKnownPosition = nil
        lastSeenTime = 0
        currentTrackingID += 1
    }

    public func update(sample: HandSample, timestamp: TimeInterval) -> HandSample {
        guard let indexTip = sample.joint(.indexTip, minConfidence: 0.2) ?? sample.joint(.wrist, minConfidence: 0.2) else {
            return sample
        }

        if let prevPos = lastKnownPosition {
            let dt = timestamp - lastSeenTime
            let dx = indexTip.x - prevPos.x
            let dy = indexTip.y - prevPos.y
            let dist = sqrt(dx * dx + dy * dy)

            if dt > timeoutSeconds || dist > maxJumpDistance {
                // Hand was lost or hopped too far; assign new ID
                currentTrackingID += 1
            }
        }

        lastKnownPosition = indexTip
        lastSeenTime = timestamp

        return HandSample(
            hostTimestamp: sample.hostTimestamp,
            presentationTimeSeconds: sample.presentationTimeSeconds,
            isPresentationTimeEstimated: sample.isPresentationTimeEstimated,
            joints: sample.joints,
            overallConfidence: sample.overallConfidence,
            estimatedHandedness: sample.estimatedHandedness,
            trackingID: currentTrackingID
        )
    }
}
