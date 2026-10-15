import Foundation
import CoreGraphics

/// An immutable, timestamped capture of hand landmarks from a single video frame.
/// Handles missing or low-confidence joints gracefully.
public struct HandSample: Sendable, Codable, Equatable {
    public let hostTimestamp: TimeInterval
    public let presentationTimeSeconds: Double
    public let isPresentationTimeEstimated: Bool
    public let joints: [HandJointName: HandJoint]
    public let overallConfidence: Float
    public let estimatedHandedness: EstimatedHandedness
    public let trackingID: Int

    public init(
        hostTimestamp: TimeInterval,
        presentationTimeSeconds: Double,
        isPresentationTimeEstimated: Bool,
        joints: [HandJointName: HandJoint],
        overallConfidence: Float,
        estimatedHandedness: EstimatedHandedness,
        trackingID: Int
    ) {
        self.hostTimestamp = hostTimestamp
        self.presentationTimeSeconds = presentationTimeSeconds
        self.isPresentationTimeEstimated = isPresentationTimeEstimated
        self.joints = joints
        self.overallConfidence = overallConfidence
        self.estimatedHandedness = estimatedHandedness
        self.trackingID = trackingID
    }

    /// Safe accessor for a joint with a confidence threshold.
    /// Returns nil if the joint is missing or its confidence falls below threshold.
    public func joint(_ name: HandJointName, minConfidence: Float = 0.3) -> CGPoint? {
        guard let j = joints[name], j.confidence >= minConfidence else {
            return nil
        }
        return j.position
    }

    /// Computes the scale reference of the hand (Euclidean distance between wrist and middle MCP).
    /// Used to normalize pinch distances and thresholds across different hand-camera distances.
    public var scaleReference: CGFloat? {
        guard let wrist = joint(.wrist, minConfidence: 0.2),
              let middleMCP = joint(.middleMCP, minConfidence: 0.2) else {
            return nil
        }
        let dx = middleMCP.x - wrist.x
        let dy = middleMCP.y - wrist.y
        let dist = sqrt(dx * dx + dy * dy)
        return dist > 0.02 ? dist : nil
    }
}
