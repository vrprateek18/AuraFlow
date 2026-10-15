import Foundation

/// Estimated hand chirality for UI rendering and telemetry only.
/// Invariant: Handedness is NEVER safety-critical. All safety, pointer,
/// and click actions operate identically regardless of estimated handedness.
public enum EstimatedHandedness: String, Sendable, Codable {
    case left
    case right
    case unknown
}
