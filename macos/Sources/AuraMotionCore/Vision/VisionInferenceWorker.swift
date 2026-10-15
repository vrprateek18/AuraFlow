import QuartzCore
import Foundation
import Vision
import CoreMedia

public protocol VisionInferenceWorkerDelegate: AnyObject, Sendable {
    func visionWorker(
        _ worker: VisionInferenceWorker,
        didProduce sample: HandSample?,
        carrier: SampleCarrier,
        inferenceDuration: TimeInterval,
        mailboxWaitDuration: TimeInterval
    )
}

/// Executes VNDetectHumanHandPoseRequest on a dedicated .userInitiated queue.
/// Strictly enforces <= 1 in-flight Vision request via FrameMailbox.
public final class VisionInferenceWorker: @unchecked Sendable {
    private let visionQueue = DispatchQueue(label: "com.auramotion.vision", qos: .userInitiated)
    private let handPoseRequest: VNDetectHumanHandPoseRequest
    public let activeRevision: Int

    public weak var delegate: VisionInferenceWorkerDelegate?
    public var isMirrored: Bool = true

    public init() {
        let rev = VisionRevisionPolicy.selectActiveRevision()
        self.activeRevision = rev
        self.handPoseRequest = VNDetectHumanHandPoseRequest()
        self.handPoseRequest.revision = rev
        self.handPoseRequest.maximumHandCount = 1
    }

    /// Triggers the worker to evaluate waiting frames from the mailbox.
    public func processMailbox(mailbox: FrameMailbox) {
        visionQueue.async { [weak self] in
            guard let self = self else { return }
            guard let carrier = mailbox.beginNextInference() else {
                return
            }
            self.executeInference(carrier: carrier, mailbox: mailbox)
        }
    }

    private func executeInference(carrier: SampleCarrier, mailbox: FrameMailbox) {
        var currentCarrier = carrier

        while true {
            let tStart = CACurrentMediaTime()
            let mailboxWait = max(0, tStart - currentCarrier.hostPresentationTime)

            let sampleBuffer = currentCarrier.buffer
            guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
                let next = mailbox.endInferenceAndAcquireNext()
                if let n = next {
                    currentCarrier = n
                    continue
                } else {
                    break
                }
            }

            let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])
            var producedSample: HandSample?

            do {
                try handler.perform([handPoseRequest])
                if let observation = handPoseRequest.results?.first {
                    producedSample = HandObservationDecoder.decode(
                        observation: observation,
                        hostTimestamp: currentCarrier.hostPresentationTime,
                        presentationTime: currentCarrier.hostPresentationTime,
                        isEstimatedTime: currentCarrier.isEstimatedTime,
                        trackingID: 1,
                        isMirrored: isMirrored
                    )
                }
            } catch {
                producedSample = nil
            }

            let tDone = CACurrentMediaTime()
            let inferenceDuration = max(0, tDone - tStart)

            delegate?.visionWorker(
                self,
                didProduce: producedSample,
                carrier: currentCarrier,
                inferenceDuration: inferenceDuration,
                mailboxWaitDuration: mailboxWait
            )

            // Loop immediately if a newer frame arrived while inference was running
            if let next = mailbox.endInferenceAndAcquireNext() {
                currentCarrier = next
            } else {
                break
            }
        }
    }
}
