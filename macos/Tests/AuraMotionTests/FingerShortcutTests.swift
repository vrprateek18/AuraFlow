import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class FingerShortcutTests: XCTestCase {
    func testMiddleFingerContactEmitsCopyOnlyOnceUntilReleased() {
        let detector = FingerShortcutDetector()
        let contact = makeSample(middleTip: CGPoint(x: 0.55, y: 0.50), ringTip: CGPoint(x: 0.78, y: 0.50))

        XCTAssertNil(detector.evaluate(sample: contact))
        XCTAssertEqual(detector.evaluate(sample: at(contact, time: 1.07)), .copy)
        XCTAssertNil(detector.evaluate(sample: contact), "Holding a contact must not repeat Copy")

        let released = makeSample(middleTip: CGPoint(x: 0.70, y: 0.50), ringTip: CGPoint(x: 0.78, y: 0.50))
        XCTAssertNil(detector.evaluate(sample: at(released, time: 1.1)))
        XCTAssertNil(detector.evaluate(sample: at(released, time: 1.17)))
        XCTAssertNil(detector.evaluate(sample: at(contact, time: 1.2)))
        XCTAssertEqual(detector.evaluate(sample: at(contact, time: 1.27)), .copy)
    }

    func testRingFingerContactEmitsPasteAndIndexContactIsReservedForClick() {
        let detector = FingerShortcutDetector()
        let paste = makeSample(middleTip: CGPoint(x: 0.75, y: 0.50), ringTip: CGPoint(x: 0.55, y: 0.50))
        XCTAssertNil(detector.evaluate(sample: paste))
        XCTAssertEqual(detector.evaluate(sample: at(paste, time: 1.07)), .paste)

        detector.reset()
        let indexPinch = makeSample(
            indexTip: CGPoint(x: 0.54, y: 0.50),
            middleTip: CGPoint(x: 0.55, y: 0.50),
            ringTip: CGPoint(x: 0.75, y: 0.50)
        )
        XCTAssertNil(detector.evaluate(sample: indexPinch), "Index pinch must remain click/drag")
    }

    func testShortcutPostingUsesCommandCAndCommandV() {
        let poster = RecordingEventPoster()
        poster.postShortcut(.copy)
        poster.postShortcut(.paste)

        XCTAssertEqual(poster.allEvents, [
            .keyEvent(virtualKey: 55, keyDown: true, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 8, keyDown: true, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 8, keyDown: false, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 55, keyDown: false, flags: 0),
            .keyEvent(virtualKey: 55, keyDown: true, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 9, keyDown: true, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 9, keyDown: false, flags: CGEventFlags.maskCommand.rawValue),
            .keyEvent(virtualKey: 55, keyDown: false, flags: 0)
        ])
    }

    private func makeSample(
        indexTip: CGPoint = CGPoint(x: 0.80, y: 0.50),
        middleTip: CGPoint,
        ringTip: CGPoint
    ) -> HandSample {
        let joints: [HandJointName: HandJoint] = [
            .wrist: HandJoint(name: .wrist, position: CGPoint(x: 0.5, y: 0.2), confidence: 0.9),
            .middleMCP: HandJoint(name: .middleMCP, position: CGPoint(x: 0.5, y: 0.4), confidence: 0.9),
            .thumbTip: HandJoint(name: .thumbTip, position: CGPoint(x: 0.5, y: 0.5), confidence: 0.9),
            .indexTip: HandJoint(name: .indexTip, position: indexTip, confidence: 0.9),
            .middleTip: HandJoint(name: .middleTip, position: middleTip, confidence: 0.9),
            .ringTip: HandJoint(name: .ringTip, position: ringTip, confidence: 0.9)
        ]
        return HandSample(hostTimestamp: 1, presentationTimeSeconds: 1, isPresentationTimeEstimated: false, joints: joints, overallConfidence: 0.9, estimatedHandedness: .right, trackingID: 1)
    }

    private func at(_ sample: HandSample, time: Double) -> HandSample {
        HandSample(hostTimestamp: time, presentationTimeSeconds: time, isPresentationTimeEstimated: false,
                   joints: sample.joints, overallConfidence: sample.overallConfidence, estimatedHandedness: .right, trackingID: 1)
    }

    func testContactSpikeAndBriefReleaseDoNotRepeatPaste() {
        let detector = FingerShortcutDetector()
        let paste = makeSample(middleTip: CGPoint(x: 0.75, y: 0.5), ringTip: CGPoint(x: 0.51, y: 0.5))
        let released = makeSample(middleTip: CGPoint(x: 0.75, y: 0.5), ringTip: CGPoint(x: 0.8, y: 0.5))
        XCTAssertNil(detector.evaluate(sample: paste))
        XCTAssertNil(detector.evaluate(sample: at(released, time: 1.03)))
        XCTAssertNil(detector.evaluate(sample: at(paste, time: 1.06)))
        XCTAssertEqual(detector.evaluate(sample: at(paste, time: 1.13)), .paste)
        XCTAssertNil(detector.evaluate(sample: at(released, time: 1.16)))
        for frame in 0..<10 {
            XCTAssertNil(detector.evaluate(sample: at(paste, time: 1.19 + Double(frame) / 30)))
        }
    }
}
