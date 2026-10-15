import Foundation
import Vision

public struct VisionRevisionPolicy: Sendable {
    /// Explicit, tested candidate revisions ordered by preference (highest to lowest).
    public static let testedRevisions: [Int] = [
        VNDetectHumanHandPoseRequestRevision1
    ]

    /// Selects the highest eligible tested revision supported by the active macOS version.
    public static func selectActiveRevision() -> Int {
        let supported = VNDetectHumanHandPoseRequest.supportedRevisions
        for rev in testedRevisions {
            if supported.contains(rev) {
                return rev
            }
        }
        // Fallback to the minimum supported revision if none of the tested match
        return supported.first ?? VNDetectHumanHandPoseRequestRevision1
    }
}
