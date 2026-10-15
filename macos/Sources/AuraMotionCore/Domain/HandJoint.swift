import Foundation
import CoreGraphics

/// Strongly typed identifiers for the 21 landmarks of a human hand.
public enum HandJointName: String, CaseIterable, Sendable, Codable, CodingKeyRepresentable {
    case wrist
    // Thumb
    case thumbCMC
    case thumbMP
    case thumbIP
    case thumbTip
    // Index
    case indexMCP
    case indexPIP
    case indexDIP
    case indexTip
    // Middle
    case middleMCP
    case middlePIP
    case middleDIP
    case middleTip
    // Ring
    case ringMCP
    case ringPIP
    case ringDIP
    case ringTip
    // Little (Pinky)
    case littleMCP
    case littlePIP
    case littleDIP
    case littleTip
}

/// A single detected 2D hand joint observation.
/// Note: Apple Vision provides 2D normalized points in [0, 1] relative to the image frame.
public struct HandJoint: Sendable, Codable, Equatable {
    public let name: HandJointName
    public let position: CGPoint
    public let confidence: Float

    public init(name: HandJointName, position: CGPoint, confidence: Float) {
        self.name = name
        self.position = position
        self.confidence = confidence
    }
}
