import Foundation
import CoreGraphics

public enum PalmSwipeDirection: String, Sendable, Codable, Equatable {
    case left
    case right
}

/// Robust detector for open-palm horizontal swipe gestures.
/// Detects ballistic left/right hand sweeps while rejecting stationary rest, diagonal motion,
/// low-confidence tracking, and accidental return strokes.
public final class PalmSwipeDetector: @unchecked Sendable {
    public var minDisplacement: CGFloat
    public var maxDurationSeconds: TimeInterval
    public var cooldownDurationSeconds: TimeInterval
    public var minVelocity: CGFloat
    public var candidateTimeoutSeconds: TimeInterval
    public var horizontalDominanceRatio: CGFloat

    private struct PalmSample {
        let position: CGPoint
        let timestamp: TimeInterval
    }

    private var history: [PalmSample] = []
    private var lastSwipeTime: TimeInterval = 0
    private var isArmedForSwipe: Bool = true
    private var lastNonPalmTime: TimeInterval = 0
    private var lastCandidateActiveTime: TimeInterval = 0

    public init(
        minDisplacement: CGFloat = 0.070,
        maxDurationSeconds: TimeInterval = 0.45,
        cooldownDurationSeconds: TimeInterval = 0.35,
        minVelocity: CGFloat = 0.20,
        candidateTimeoutSeconds: TimeInterval = 0.20,
        horizontalDominanceRatio: CGFloat = 1.15
    ) {
        self.minDisplacement = minDisplacement
        self.maxDurationSeconds = maxDurationSeconds
        self.cooldownDurationSeconds = cooldownDurationSeconds
        self.minVelocity = minVelocity
        self.candidateTimeoutSeconds = candidateTimeoutSeconds
        self.horizontalDominanceRatio = horizontalDominanceRatio
    }

    public var isCandidateActive: Bool {
        guard let newest = history.last else { return false }
        for candidate in history {
            let dt = newest.timestamp - candidate.timestamp
            guard dt >= 0.02 && dt <= 0.35 else { continue }
            let dx = abs(newest.position.x - candidate.position.x)
            let dy = abs(newest.position.y - candidate.position.y)
            if dx >= 0.018 && dx > (dy * 0.90) {
                return true
            }
        }
        if (newest.timestamp - lastCandidateActiveTime) < candidateTimeoutSeconds && lastCandidateActiveTime > 0 {
            return true
        }
        return false
    }

    public func reset() {
        history.removeAll()
        lastCandidateActiveTime = 0
    }

    public func notifyHandLeftOpenPalm(timestamp: TimeInterval) {
        lastNonPalmTime = timestamp
        isArmedForSwipe = true
        reset()
    }

    /// Safely extracts the anatomical palm center (midpoint between middleMCP and wrist, or MCP centroid).
    public static func extractPalmCenter(from sample: HandSample) -> CGPoint? {
        let conf: Float = 0.18
        if let middle = sample.joint(.middleMCP, minConfidence: conf) {
            if let wrist = sample.joint(.wrist, minConfidence: conf) {
                return CGPoint(x: (middle.x + wrist.x) * 0.5, y: (middle.y + wrist.y) * 0.5)
            }
            return middle
        }

        // Fallback: Centroid of available MCPs
        let mcpNames: [HandJointName] = [.indexMCP, .middleMCP, .ringMCP, .littleMCP]
        let availableMCPs = mcpNames.compactMap { sample.joint($0, minConfidence: conf) }
        if !availableMCPs.isEmpty {
            let avgX = availableMCPs.map(\.x).reduce(0, +) / CGFloat(availableMCPs.count)
            let avgY = availableMCPs.map(\.y).reduce(0, +) / CGFloat(availableMCPs.count)
            if let wrist = sample.joint(.wrist, minConfidence: conf) {
                return CGPoint(x: (avgX + wrist.x) * 0.5, y: (avgY + wrist.y) * 0.5)
            }
            return CGPoint(x: avgX, y: avgY)
        }

        return sample.joint(.wrist, minConfidence: conf)
    }

    /// Evaluates incoming hand sample for open palm horizontal swipe.
    public func evaluate(
        sample: HandSample?,
        isOpenPalm: Bool,
        timestamp: TimeInterval
    ) -> PalmSwipeDirection? {
        guard isOpenPalm, let sample = sample else {
            notifyHandLeftOpenPalm(timestamp: timestamp)
            return nil
        }

        guard let palmCenter = Self.extractPalmCenter(from: sample) else {
            reset()
            return nil
        }

        // Check cooldown
        let timeSinceSwipe = timestamp - lastSwipeTime
        if timeSinceSwipe < cooldownDurationSeconds {
            return nil
        }

        // Check if hand came to rest after cooldown, which re-arms swipe
        if !isArmedForSwipe {
            let elapsedSinceSwipe = timestamp - lastSwipeTime
            if elapsedSinceSwipe >= (cooldownDurationSeconds + 0.30) {
                isArmedForSwipe = true
                reset()
            } else if let first = history.first {
                let dt = timestamp - first.timestamp
                let dx = palmCenter.x - first.position.x
                let dy = palmCenter.y - first.position.y
                let dist = sqrt(dx * dx + dy * dy)
                let velocity = (dt > 0.001) ? (dist / CGFloat(dt)) : 1.0
                if dt >= 0.10 && (velocity < 0.25 || dist < 0.06) {
                    isArmedForSwipe = true
                    reset()
                }
            }
            history.append(PalmSample(position: palmCenter, timestamp: timestamp))
            history.removeAll { timestamp - $0.timestamp > maxDurationSeconds }
            return nil
        }

        history.append(PalmSample(position: palmCenter, timestamp: timestamp))
        history.removeAll { timestamp - $0.timestamp > maxDurationSeconds }

        guard let newest = history.last, history.count >= 2 else {
            return nil
        }

        // Update candidate active timestamp if horizontal motion is observed
        for candidate in history {
            let dt = newest.timestamp - candidate.timestamp
            guard dt >= 0.02 && dt <= 0.35 else { continue }
            let dx = abs(newest.position.x - candidate.position.x)
            let dy = abs(newest.position.y - candidate.position.y)
            if dx >= 0.018 && dx > (dy * 0.90) {
                lastCandidateActiveTime = timestamp
                break
            }
        }

        // Search through history buffer for a valid swipe stroke ending at 'newest'.
        // Checking across candidates prevents stationary resting frames from diluting the velocity calculation.
        for candidate in history {
            let dt = newest.timestamp - candidate.timestamp
            guard dt >= 0.04 && dt <= maxDurationSeconds else { continue }

            let dx = newest.position.x - candidate.position.x
            let dy = newest.position.y - candidate.position.y
            let absDx = abs(dx)
            let absDy = abs(dy)
            let velocityX = absDx / CGFloat(dt)

            // Validate swipe criteria:
            // 1. Minimum displacement
            // 2. Minimum velocity
            // 3. Horizontal dominance
            if absDx >= minDisplacement && velocityX >= minVelocity && absDx >= (absDy * horizontalDominanceRatio) {
                lastSwipeTime = timestamp
                isArmedForSwipe = false
                reset()
                // In mirror-normalized coordinates: dx < 0 is visual left, dx > 0 is visual right
                return dx < 0 ? .left : .right
            }
        }

        return nil
    }
}
