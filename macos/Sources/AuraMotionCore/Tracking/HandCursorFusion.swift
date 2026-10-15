import Foundation
import CoreGraphics

/// Palm translation carries fast motion; a slowly varying fingertip offset keeps
/// absolute index aiming while attenuating independent finger wobble.
public final class HandCursorFusion: @unchecked Sendable {
    private var previousTime: Double?
    private var identity: Int?
    private var offset: CGPoint?
    private var palmJoints: [HandJointName] = []

    public init() {}
    public func reset() {
        previousTime = nil; identity = nil; offset = nil; palmJoints = []
    }

    public func update(_ sample: HandSample) -> CGPoint? {
        guard sample.hostTimestamp.isFinite,
              let tip = sample.joint(.indexTip, minConfidence: 0.45),
              tip.x.isFinite, tip.y.isFinite else { return nil }
        if let time = previousTime, sample.hostTimestamp <= time { return nil }
        if identity != sample.trackingID || previousTime.map({ sample.hostTimestamp - $0 > 0.25 }) == true { reset() }
        let dt = min(0.1, max(0.001, sample.hostTimestamp - (previousTime ?? sample.hostTimestamp)))
        previousTime = sample.hostTimestamp; identity = sample.trackingID
        let names: [HandJointName] = [.wrist, .indexMCP, .middleMCP, .ringMCP, .littleMCP]
        let available = names.filter { name in
            guard let p = sample.joint(name, minConfidence: 0.55) else { return false }
            return p.x.isFinite && p.y.isFinite
        }
        // Use a fixed landmark set per uninterrupted observation span. Changing
        // the centroid without re-anchoring would introduce an artificial jump.
        guard available.count >= 3 else { offset = nil; palmJoints = []; return tip }
        let points = available.compactMap { sample.joint($0, minConfidence: 0.55) }
        let palm = CGPoint(x: points.map(\.x).reduce(0, +) / CGFloat(points.count),
                           y: points.map(\.y).reduce(0, +) / CGFloat(points.count))
        let measured = CGPoint(x: tip.x - palm.x, y: tip.y - palm.y)
        if offset == nil || available != palmJoints { offset = measured; palmJoints = available }
        let previous = offset ?? measured
        let pose = PoseClassifier.classify(sample: sample)
        if pose.isPinchApproach || pose.isTwoFingerPointing {
            // Finger articulation for clicking or scrolling is not translation.
            // Keep the last pointing offset and let palm motion carry the action.
            return CGPoint(x: palm.x + previous.x, y: palm.y + previous.y)
        }
        let alpha = CGFloat(1 - exp(-dt / 0.085))
        let learned = CGPoint(x: previous.x + alpha * (measured.x - previous.x),
                              y: previous.y + alpha * (measured.y - previous.y))
        offset = learned
        return CGPoint(x: palm.x + learned.x, y: palm.y + learned.y)
    }
}
