import Foundation
import CoreMedia

/// SampleCarrier holds a CMSampleBuffer for pipeline transport.
///
/// Invariant: The wrapped CMSampleBuffer is immutable after creation and
/// is never accessed concurrently. Ownership passes strictly from captureQueue
/// to visionQueue via FrameMailbox.
public final class SampleCarrier: @unchecked Sendable {
    public let buffer: CMSampleBuffer
    public let hostPresentationTime: TimeInterval
    public let isEstimatedTime: Bool

    public init(buffer: CMSampleBuffer, hostPresentationTime: TimeInterval, isEstimatedTime: Bool) {
        self.buffer = buffer
        self.hostPresentationTime = hostPresentationTime
        self.isEstimatedTime = isEstimatedTime
    }
}
