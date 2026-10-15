import XCTest
import CoreMedia
@testable import AuraMotionCore

final class ConcurrencyTests: XCTestCase {
    func testMailboxEnforcesSingleInFlightInference() {
        let mailbox = FrameMailbox()

        // Create dummy sample buffer
        var pixelBuffer: CVPixelBuffer?
        CVPixelBufferCreate(kCFAllocatorDefault, 640, 480, kCVPixelFormatType_32BGRA, nil, &pixelBuffer)
        var formatDesc: CMVideoFormatDescription?
        CMVideoFormatDescriptionCreateForImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer!, formatDescriptionOut: &formatDesc)
        var timing = CMSampleTimingInfo(duration: .invalid, presentationTimeStamp: CMTime(value: 1, timescale: 60), decodeTimeStamp: .invalid)
        var sampleBuffer: CMSampleBuffer?
        CMSampleBufferCreateReadyWithImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer!, formatDescription: formatDesc!, sampleTiming: &timing, sampleBufferOut: &sampleBuffer)

        let carrier1 = SampleCarrier(buffer: sampleBuffer!, hostPresentationTime: 1.0, isEstimatedTime: false)
        let carrier2 = SampleCarrier(buffer: sampleBuffer!, hostPresentationTime: 2.0, isEstimatedTime: false)

        mailbox.postFrame(carrier1)
        // Begin first inference: acquires carrier1 and marks in-flight = true
        let acquired1 = mailbox.beginNextInference()
        XCTAssertNotNil(acquired1)

        // While in-flight, a second attempt to beginNextInference must return NIL
        mailbox.postFrame(carrier2)
        let acquiredWhileBusy = mailbox.beginNextInference()
        XCTAssertNil(acquiredWhileBusy, "Mailbox must strictly enforce <= 1 in-flight inference")

        // Once completed, endInferenceAndAcquireNext immediately hands the waiting carrier2
        let acquired2 = mailbox.endInferenceAndAcquireNext()
        XCTAssertNotNil(acquired2)
        XCTAssertEqual(acquired2?.hostPresentationTime, 2.0)

        // Clean up
        mailbox.clear()
    }

    func testMailboxZeroBufferLeaksUnderHighFrameRate() {
        let mailbox = FrameMailbox()

        var pixelBuffer: CVPixelBuffer?
        CVPixelBufferCreate(kCFAllocatorDefault, 640, 480, kCVPixelFormatType_32BGRA, nil, &pixelBuffer)
        var formatDesc: CMVideoFormatDescription?
        CMVideoFormatDescriptionCreateForImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer!, formatDescriptionOut: &formatDesc)
        var timing = CMSampleTimingInfo(duration: .invalid, presentationTimeStamp: CMTime(value: 1, timescale: 60), decodeTimeStamp: .invalid)
        var sampleBuffer: CMSampleBuffer?
        CMSampleBufferCreateReadyWithImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer!, formatDescription: formatDesc!, sampleTiming: &timing, sampleBufferOut: &sampleBuffer)

        // Post 100 frames rapidly without inference
        for i in 0..<100 {
            let carrier = SampleCarrier(buffer: sampleBuffer!, hostPresentationTime: Double(i), isEstimatedTime: false)
            mailbox.postFrame(carrier)
        }

        XCTAssertEqual(mailbox.droppedFrames, 99)

        // Mailbox should still hold only the newest 1 frame
        let newest = mailbox.beginNextInference()
        XCTAssertEqual(newest?.hostPresentationTime, 99.0)
    }
}
