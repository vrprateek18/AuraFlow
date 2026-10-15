import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class PersonalCalibrationTests: XCTestCase {
    private func sample(step: PersonalCalibration.Step, distance: CGFloat, time: Double, confidence: Float = 0.9) -> HandSample {
        let positions: [HandJointName: CGPoint] = [
            .wrist: CGPoint(x: 0.5, y: 0.2), .middleMCP: CGPoint(x: 0.5, y: 0.4),
            .thumbTip: CGPoint(x: 0.5, y: 0.6), step.finger: CGPoint(x: 0.5 + distance * 0.2, y: 0.6)
        ]
        return HandSample(hostTimestamp: time, presentationTimeSeconds: time, isPresentationTimeEstimated: false,
            joints: Dictionary(uniqueKeysWithValues: positions.map { name, point in (name, HandJoint(name: name, position: point, confidence: confidence)) }),
            overallConfidence: confidence, estimatedHandedness: .right, trackingID: 1)
    }

    private func session(open: CGFloat, closed: CGFloat) -> PersonalCalibration {
        var session = PersonalCalibration()
        for step in PersonalCalibration.Step.allCases {
            for frame in 0..<30 {
                _ = session.add(sample(step: step, distance: step.rawValue % 2 == 0 ? open : closed,
                    time: Double(step.rawValue * 100 + frame) / 30))
            }
        }
        return session
    }

    func testLearnsSeparatedContactsAndPersistsAllFingerThresholds() throws {
        let session = session(open: 0.9, closed: 0.18)
        XCTAssertTrue(session.isComplete)
        let profile = try XCTUnwrap(session.applying(to: CalibrationProfile()))
        XCTAssertGreaterThan(profile.pinchStartThreshold, 0.18)
        XCTAssertLessThan(profile.pinchStartThreshold, profile.pinchReleaseThreshold)
        XCTAssertNotNil(profile.copyContactThreshold)
        XCTAssertNotNil(profile.pasteReleaseThreshold)
        XCTAssertEqual(try JSONDecoder().decode(CalibrationProfile.self, from: JSONEncoder().encode(profile)), profile)
    }

    func testOverlappingPosesCannotReplaceCalibration() {
        XCTAssertNil(session(open: 0.3, closed: 0.25).applying(to: CalibrationProfile()))
    }

    func testLowConfidenceAndDuplicateFramesDoNotCompleteStep() {
        var session = PersonalCalibration()
        for frame in 0..<100 {
            _ = session.add(sample(step: .indexOpen, distance: 0.9, time: Double(frame) / 30, confidence: 0.2))
        }
        XCTAssertEqual(session.count, 0)
        for _ in 0..<100 { _ = session.add(sample(step: .indexOpen, distance: 0.9, time: 10)) }
        XCTAssertEqual(session.count, 1)
    }

    func testLegacyProfileLoadsWithoutNewFields() throws {
        let data = try JSONEncoder().encode(CalibrationProfile())
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        for key in ["copyContactThreshold", "copyReleaseThreshold", "pasteContactThreshold", "pasteReleaseThreshold"] { json.removeValue(forKey: key) }
        let decoded = try JSONDecoder().decode(CalibrationProfile.self, from: JSONSerialization.data(withJSONObject: json))
        XCTAssertNil(decoded.copyContactThreshold)
        XCTAssertEqual(decoded.pinchStartThreshold, 0.28)
    }

    func testConfirmationRestartsAfterTrackingGap() {
        var confirmation = ContactConfirmation()
        XCTAssertFalse(confirmation.update(matches: true, timestamp: 1))
        XCTAssertFalse(confirmation.update(matches: true, timestamp: 2))
        XCTAssertTrue(confirmation.update(matches: true, timestamp: 2.07))
    }

    func testSingleFramePinchDoesNotClick() {
        let detector = PinchDetector()
        _ = detector.evaluate(normalizedDistance: 0.1, currentLocation: .zero, timestamp: 1)
        XCTAssertEqual(detector.evaluate(normalizedDistance: 0.6, currentLocation: .zero, timestamp: 1.033), .cancelled)
    }
}
