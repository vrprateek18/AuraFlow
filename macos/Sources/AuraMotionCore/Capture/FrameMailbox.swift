import Foundation
import CoreMedia
import os

/// Thread-safe, lock-protected bounded mailbox holding at most ONE unconsumed video frame.
/// Enforces strictly <= 1 Vision inference in flight.
public final class FrameMailbox: @unchecked Sendable {
    private var lock = os_unfair_lock_s()
    private var latestCarrier: SampleCarrier?
    private var isInFlight: Bool = false
    private var droppedFrameCount: Int = 0

    public init() {}

    /// Called on captureQueue. Stores newest frame, dropping any previously unconsumed frame.
    @discardableResult
    public func postFrame(_ carrier: SampleCarrier) -> Bool {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }

        if latestCarrier != nil {
            droppedFrameCount += 1
        }
        latestCarrier = carrier
        return true
    }

    /// Atomically checks if Vision is idle and a frame is available.
    /// If so, marks in-flight and returns the frame.
    public func beginNextInference() -> SampleCarrier? {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }

        guard !isInFlight, let carrier = latestCarrier else {
            return nil
        }
        isInFlight = true
        latestCarrier = nil
        return carrier
    }

    /// Called on visionQueue upon completion. Clears in-flight flag and
    /// immediately acquires the next frame if one arrived during inference.
    public func endInferenceAndAcquireNext() -> SampleCarrier? {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }

        if let next = latestCarrier {
            latestCarrier = nil
            isInFlight = true
            return next
        } else {
            isInFlight = false
            return nil
        }
    }

    /// Idempotently clears mailbox contents and resets in-flight flag.
    public func clear() {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        latestCarrier = nil
        isInFlight = false
    }

    /// Returns current drop stats.
    public var droppedFrames: Int {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return droppedFrameCount
    }
}
