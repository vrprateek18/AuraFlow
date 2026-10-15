import Foundation
import CoreGraphics

/// Maps normalized Vision space [0, 1] x [0, 1] to canonical Quartz global display coordinates.
/// Handles soft margin easing and negative-origin multi-display setups.
public struct CoordinateMapper: Sendable {
    public let profile: CalibrationProfile

    public init(profile: CalibrationProfile) {
        self.profile = profile
    }

    /// Maps a normalized point (u, v) in Vision coordinates (origin bottom-left, [0, 1])
    /// to Quartz Global Display coordinates (origin primary display top-left, Y downwards).
    public func mapToQuartzGlobal(visionPoint: CGPoint) -> CGPoint {
        let region = profile.activeRegion

        // 1. Normalize relative to active interaction box
        let u = (visionPoint.x - region.minX) / max(region.width, 0.01)
        let v = (visionPoint.y - region.minY) / max(region.height, 0.01)

        // 2. Linear mapping clamped to [0, 1] active region
        let clampedU = min(max(u, 0.0), 1.0)
        let clampedV = min(max(v, 0.0), 1.0)

        // 3. Apply cursor gain centered at (0.5, 0.5)
        let gain = CGFloat(max(0.1, profile.cursorGain))
        let gainedU = 0.5 + (clampedU - 0.5) * gain
        let gainedV = 0.5 + (clampedV - 0.5) * gain
        let finalU = min(max(gainedU, 0.0), 1.0)
        let finalV = min(max(gainedV, 0.0), 1.0)

        // 4. Map to target display bounds (Quartz coordinates: Y is flipped, Y=0 is top)
        let bounds = profile.displayBounds
        let quartzX = bounds.minX + finalU * bounds.width
        let quartzY = bounds.minY + (1.0 - finalV) * bounds.height

        // 5. Clamp to display bounds to avoid straying into unintended spaces
        let clampedX = min(max(quartzX, bounds.minX), bounds.maxX)
        let clampedY = min(max(quartzY, bounds.minY), bounds.maxY)

        return CGPoint(x: clampedX, y: clampedY)
    }
}
