import Foundation
import CoreGraphics


/// Coordinates 1€ filter smoothing, coordinate mapping, and display boundary clamping.
public final class CursorController: @unchecked Sendable {
    private let filter = OneEuroFilter2D(minCutoff: 0.85, beta: 0.008, dCutoff: 1.0)
    private var lastRaw: CGPoint?
    private var pendingJump: CGPoint?
    private var lastOutput: CGPoint?
    private var lastTimestamp: TimeInterval?
    public var mapper: CoordinateMapper
    private let handFusion = HandCursorFusion()

    public init(profile: CalibrationProfile) {
        self.mapper = CoordinateMapper(profile: profile)
        applyTuning(profile)
    }

    public func reset() {
        filter.reset()
        handFusion.reset()
        lastRaw = nil
        pendingJump = nil
        lastOutput = nil
        lastTimestamp = nil
    }

    public func updateProfile(_ profile: CalibrationProfile) {
        self.mapper = CoordinateMapper(profile: profile)
        applyTuning(profile)
        reset()
    }

    private func applyTuning(_ profile: CalibrationProfile) {
        filter.minCutoff = min(1.5, max(0.5, profile.cursorMinCutoff ?? 0.85))
        filter.beta = min(0.025, max(0.004, profile.cursorMotionBeta ?? 0.008))
    }

    public func processHand(_ sample: HandSample) -> CGPoint? {
        // Reset before fusion, so a long capture gap cannot discard a fresh anchor.
        if let time = lastTimestamp, sample.hostTimestamp - time > 0.25 { reset() }
        return processIndexTip(normalizedPoint: handFusion.update(sample), timestamp: sample.hostTimestamp)
    }

    /// Maps normalized index-finger tip and applies 1€ adaptive filtering.
    public func processIndexTip(normalizedPoint: CGPoint?, timestamp: TimeInterval) -> CGPoint? {
        guard let rawPt = normalizedPoint else {
            // A single missing landmark should not discard the stabilizer.
            return lastOutput
        }
        guard rawPt.x.isFinite, rawPt.y.isFinite, timestamp.isFinite else { return lastOutput }
        if let previous = lastTimestamp {
            guard timestamp > previous else { return lastOutput }
            if timestamp - previous > 0.25 { reset() }
        }

        // 1. Map to Quartz global coordinates
        let mapped = mapper.mapToQuartzGlobal(visionPoint: rawPt)
        lastTimestamp = timestamp

        // One-frame landmark mistakes can look like very fast intentional motion
        // to an adaptive filter. Require a second nearby observation for big jumps.
        let bounds = mapper.profile.displayBounds
        let jumpThreshold = max(80, hypot(bounds.width, bounds.height) * 0.04)
        if let previous = lastRaw, hypot(mapped.x - previous.x, mapped.y - previous.y) > jumpThreshold {
            if let pending = pendingJump, hypot(mapped.x - pending.x, mapped.y - pending.y) <= jumpThreshold {
                pendingJump = nil
            } else {
                pendingJump = mapped
                return lastOutput
            }
        } else { pendingJump = nil }
        lastRaw = mapped

        // 2. Smooth with 1€ filter
        let smoothed = filter.filter(point: mapped, timestamp: timestamp)

        // A soft radial dead zone arrests resting tremor without rounding slow
        // motion into whole-pixel jumps. Deliberate movement accumulates naturally.
        if let previous = lastOutput {
            let dx = smoothed.x - previous.x
            let dy = smoothed.y - previous.y
            let distance = hypot(dx, dy)
            let radius = min(4, max(0.5, mapper.profile.cursorRestRadius ?? 1.25))
            if distance <= radius { return previous }
            let fraction = (distance - radius) / distance
            let result = CGPoint(x: previous.x + dx * fraction, y: previous.y + dy * fraction)
            lastOutput = result
            return result
        }
        lastOutput = smoothed
        return smoothed
    }
}
