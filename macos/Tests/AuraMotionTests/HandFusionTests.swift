import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class HandFusionTests: XCTestCase {
    private func sample(time: Double, shift: Double = 0, wobble: Double = 0, identity: Int = 1, confidence: Float = 0.9) -> HandSample {
        let positions: [HandJointName: CGPoint] = [
            .wrist: CGPoint(x: 0.5 + shift, y: 0.2),
            .indexMCP: CGPoint(x: 0.44 + shift, y: 0.4),
            .middleMCP: CGPoint(x: 0.5 + shift, y: 0.4),
            .ringMCP: CGPoint(x: 0.56 + shift, y: 0.4),
            .littleMCP: CGPoint(x: 0.62 + shift, y: 0.4),
            .indexTip: CGPoint(x: 0.44 + shift + wobble, y: 0.7),
            .indexPIP: CGPoint(x: 0.44 + shift, y: 0.52),
            .middleTip: CGPoint(x: 0.5 + shift, y: 0.35),
            .thumbTip: CGPoint(x: 0.2 + shift, y: 0.5)
        ]
        return HandSample(hostTimestamp: time, presentationTimeSeconds: time, isPresentationTimeEstimated: false,
            joints: Dictionary(uniqueKeysWithValues: positions.map { ($0.key, HandJoint(name: $0.key, position: $0.value, confidence: confidence)) }),
            overallConfidence: confidence, estimatedHandedness: .right, trackingID: identity)
    }

    func testFusionSuppressesFingerWobbleWithoutDelayingPalmTranslation() throws {
        let fusion = HandCursorFusion()
        var error = 0.0
        for i in 0..<90 {
            let shift = Double(i) * 0.002
            let result = try XCTUnwrap(fusion.update(sample(time: 1 + Double(i) / 30, shift: shift, wobble: sin(Double(i) * 1.7) * 0.006)))
            if i > 10 { error += pow(result.x - (0.44 + shift), 2) }
        }
        XCTAssertLessThan(sqrt(error / 79), 0.0015)
        fusion.reset()
        _ = fusion.update(sample(time: 10))
        let translated = try XCTUnwrap(fusion.update(sample(time: 10.033, shift: 0.08)))
        XCTAssertEqual(translated.x, 0.52, accuracy: 0.00001)
    }

    func testFusionReanchorsAfterLandmarkSetOrIdentityChanges() throws {
        let fusion = HandCursorFusion()
        _ = fusion.update(sample(time: 1))
        let source = sample(time: 1.033)
        var joints = source.joints
        joints.removeValue(forKey: .wrist)
        let partial = HandSample(hostTimestamp: source.hostTimestamp, presentationTimeSeconds: source.hostTimestamp, isPresentationTimeEstimated: false, joints: joints, overallConfidence: 0.9, estimatedHandedness: .right, trackingID: 1)
        XCTAssertEqual(try XCTUnwrap(fusion.update(partial)).x, 0.44, accuracy: 0.00001)
        XCTAssertEqual(try XCTUnwrap(fusion.update(sample(time: 1.067, shift: 0.1, identity: 2))).x, 0.54, accuracy: 0.00001)
        XCTAssertNil(fusion.update(sample(time: 1.01)))
        XCTAssertNil(fusion.update(sample(time: 1.1, confidence: 0.2)))
    }

    func testFingerCurlForPinchDoesNotMoveCursorButPalmTranslationDoes() throws {
        let fusion = HandCursorFusion()
        let start = try XCTUnwrap(fusion.update(sample(time: 1)))
        let source = sample(time: 1.033, shift: 0.03)
        var joints = source.joints
        joints[.indexTip] = HandJoint(name: .indexTip, position: CGPoint(x: 0.47, y: 0.5), confidence: 0.9)
        joints[.thumbTip] = HandJoint(name: .thumbTip, position: CGPoint(x: 0.47, y: 0.5), confidence: 0.9)
        let pinched = HandSample(hostTimestamp: source.hostTimestamp, presentationTimeSeconds: source.hostTimestamp, isPresentationTimeEstimated: false, joints: joints, overallConfidence: 0.9, estimatedHandedness: .right, trackingID: 1)
        let result = try XCTUnwrap(fusion.update(pinched))
        XCTAssertEqual(result.x, start.x + 0.03, accuracy: 0.00001)
        XCTAssertEqual(result.y, start.y, accuracy: 0.00001)
    }

    func testMovementCalibrationLearnsAndPersistsWithoutChangingContacts() throws {
        var session = MovementCalibration()
        for step in 0..<3 {
            for i in 0..<60 {
                let shift: Double
                if step == 0 { shift = sin(Double(i) * 1.7) * 0.001 }
                else { shift = (step == 1 ? 0.1 : 0.18) * sin(Double(i) / 59 * Double.pi * (step == 1 ? 2 : 4)) }
                _ = session.add(sample(time: 10 + Double(step) * 3 + Double(i) * 0.04, shift: shift))
            }
        }
        XCTAssertTrue(session.isComplete)
        let original = CalibrationProfile()
        let learned = try XCTUnwrap(session.applying(to: original))
        XCTAssertNotNil(learned.cursorRestRadius)
        XCTAssertNotNil(learned.cursorMotionBeta)
        XCTAssertEqual(learned.pinchStartThreshold, original.pinchStartThreshold)
        XCTAssertEqual(learned.activeRegion, original.activeRegion)
        XCTAssertEqual(try JSONDecoder().decode(CalibrationProfile.self, from: JSONEncoder().encode(learned)), learned)
        var old = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(learned)) as? [String: Any])
        for name in ["cursorRestRadius", "cursorMinCutoff", "cursorMotionBeta"] { old.removeValue(forKey: name) }
        XCTAssertNil(try JSONDecoder().decode(CalibrationProfile.self, from: JSONSerialization.data(withJSONObject: old)).cursorRestRadius)
    }

    func testMovementCalibrationRejectsMovingRestAndInterruptedRecording() {
        var session = MovementCalibration()
        for i in 0..<60 { _ = session.add(sample(time: 1 + Double(i) * 0.04, shift: Double(i) * 0.003)) }
        XCTAssertEqual(session.step, .still)
        XCTAssertNotNil(session.message)
        XCTAssertNil(session.applying(to: CalibrationProfile()))
        _ = session.add(sample(time: 10))
        _ = session.add(sample(time: 11))
        XCTAssertEqual(session.count, 1)
    }
}
