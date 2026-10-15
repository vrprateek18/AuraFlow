import Foundation

/// Hysteresis confidence gate with reacquisition dwell.
public final class ConfidenceGate: @unchecked Sendable {
    public let enterConfidence: Float
    public let exitConfidence: Float
    public let dropConsecutiveFramesThreshold: Int
    public var reacquisitionDwellSeconds: TimeInterval

    private var isTracking = false
    private var lowConfidenceFrameCount = 0
    private var reacquisitionStartTime: TimeInterval?

    public init(
        enterConfidence: Float = 0.60,
        exitConfidence: Float = 0.35,
        dropConsecutiveFramesThreshold: Int = 3,
        reacquisitionDwellSeconds: TimeInterval = 0.08
    ) {
        self.enterConfidence = enterConfidence
        self.exitConfidence = exitConfidence
        self.dropConsecutiveFramesThreshold = dropConsecutiveFramesThreshold
        self.reacquisitionDwellSeconds = reacquisitionDwellSeconds
    }

    public func reset() {
        isTracking = false
        lowConfidenceFrameCount = 0
        reacquisitionStartTime = nil
    }

    /// Evaluates whether the sample is admitted through the confidence gate.
    public func evaluate(sample: HandSample?, timestamp: TimeInterval) -> Bool {
        guard let sample = sample, sample.overallConfidence >= exitConfidence else {
            // No sample or confidence below floor
            lowConfidenceFrameCount += 1
            if lowConfidenceFrameCount >= dropConsecutiveFramesThreshold {
                isTracking = false
                reacquisitionStartTime = nil
            }
            return false
        }

        if isTracking {
            // Already tracking: maintain tracking unless confidence drops below exit floor
            if sample.overallConfidence < exitConfidence {
                lowConfidenceFrameCount += 1
                if lowConfidenceFrameCount >= dropConsecutiveFramesThreshold {
                    isTracking = false
                    reacquisitionStartTime = nil
                    return false
                }
            } else {
                lowConfidenceFrameCount = 0
            }
            return true
        } else {
            // Reacquisition phase: requires enterConfidence and dwell time
            if sample.overallConfidence >= enterConfidence {
                if reacquisitionDwellSeconds <= 0.0 {
                    isTracking = true
                    lowConfidenceFrameCount = 0
                    reacquisitionStartTime = nil
                    return true
                }

                if let start = reacquisitionStartTime {
                    if (timestamp - start) >= reacquisitionDwellSeconds {
                        isTracking = true
                        lowConfidenceFrameCount = 0
                        reacquisitionStartTime = nil
                        return true
                    }
                } else {
                    reacquisitionStartTime = timestamp
                }
            } else {
                reacquisitionStartTime = nil
            }
            return false
        }
    }
}
