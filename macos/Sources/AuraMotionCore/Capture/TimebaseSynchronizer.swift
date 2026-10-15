import Foundation
import CoreMedia
import AVFoundation

/// Synchronizes camera presentation timestamps to the host monotonic clock.
public final class TimebaseSynchronizer: @unchecked Sendable {
    private let lock = NSLock()
    private var anchorHostTime: TimeInterval?
    private var anchorPresentationTime: Double?

    public init() {}

    /// Resets the timebase synchronization anchors (called upon interruption, sleep, or reconfig).
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        anchorHostTime = nil
        anchorPresentationTime = nil
    }

    /// Converts a sample buffer presentation timestamp to host monotonic seconds.
    public func hostPresentationTime(
        for sampleBuffer: CMSampleBuffer,
        session: AVCaptureSession?,
        arrivalHostTime: TimeInterval
    ) -> (hostTime: TimeInterval, isEstimated: Bool) {
        let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        guard pts.isValid else {
            return (arrivalHostTime, true)
        }

        // 1. Attempt official CoreMedia synchronization if the capture session exposes a clock
        if let session = session, session.isRunning, let captureClock = session.synchronizationClock {
            let hostClock = CMClockGetHostTimeClock()
            let convertedTime = CMSyncConvertTime(pts, from: captureClock, to: hostClock)
            if convertedTime.isValid {
                let seconds = CMTimeGetSeconds(convertedTime)
                return (seconds, false)
            }
        }

        // 2. Fallback: Anchored host offset
        lock.lock()
        defer { lock.unlock() }

        let ptsSeconds = CMTimeGetSeconds(pts)
        if let aHost = anchorHostTime, let aPts = anchorPresentationTime {
            let delta = ptsSeconds - aPts
            return (aHost + delta, true)
        } else {
            anchorHostTime = arrivalHostTime
            anchorPresentationTime = ptsSeconds
            return (arrivalHostTime, true)
        }
    }
}
