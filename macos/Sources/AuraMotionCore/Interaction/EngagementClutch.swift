import Foundation

/// Requires a deliberate ready pose held for dwell time before cursor control engages,
/// with hysteresis grace duration to prevent momentary pose drops from stalling the cursor.
public final class EngagementClutch: @unchecked Sendable {
    /// Tunable activation delay. This is read only from the serialized interaction queue.
    public var dwellDuration: TimeInterval
    public let disengageGraceDuration: TimeInterval

    private var clutchStartTime: TimeInterval?
    private var disengageStartTime: TimeInterval?
    private var isEngagedState = false

    public init(dwellDuration: TimeInterval = 0.05, disengageGraceDuration: TimeInterval = 0.25) {
        self.dwellDuration = dwellDuration
        self.disengageGraceDuration = disengageGraceDuration
    }

    public var isEngaged: Bool {
        return isEngagedState
    }

    public func reset() {
        clutchStartTime = nil
        disengageStartTime = nil
        isEngagedState = false
    }

    public func evaluate(isReadyPose: Bool, timestamp: TimeInterval) -> Bool {
        if isEngagedState {
            if isReadyPose {
                disengageStartTime = nil
                return true
            } else {
                // Momentary pose loss: do not disengage immediately
                if let start = disengageStartTime {
                    if (timestamp - start) >= disengageGraceDuration {
                        isEngagedState = false
                        disengageStartTime = nil
                        clutchStartTime = nil
                        return false
                    }
                    return true
                } else {
                    disengageStartTime = timestamp
                    return true
                }
            }
        }

        // Not yet engaged: evaluate dwell duration
        disengageStartTime = nil
        guard isReadyPose else {
            clutchStartTime = nil
            return false
        }

        if let start = clutchStartTime {
            if (timestamp - start) >= dwellDuration {
                isEngagedState = true
                clutchStartTime = nil
                return true
            }
        } else {
            clutchStartTime = timestamp
        }

        return false
    }
}
