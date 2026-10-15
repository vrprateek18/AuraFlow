import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class PalmSwipeDetectorTests: XCTestCase {
    func testSustainedPalmOpensCommandMenuThroughStateMachine() {
        let fsm = GestureStateMachine()
        let output = MockStateMachineDelegate()
        fsm.delegate = output
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0
        for frame in 0...40 {
            fsm.processFrame(sample: makeOpenPalmSample(x: 0.5, y: 0.5, time: 100 + Double(frame) / 30),
                             mappedCursorLocation: CGPoint(x: 400, y: 400), currentEpoch: 1, isInjectionAllowed: true)
        }
        XCTAssertTrue(fsm.commandMenu.isOpen)
        XCTAssertTrue(output.swipes.isEmpty)
        XCTAssertTrue(output.clickAnchors.isEmpty)
        fsm.isManualPaused = true
        fsm.processFrame(sample: makeOpenPalmSample(x: 0.5, y: 0.5, time: 102), mappedCursorLocation: .zero, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertFalse(fsm.commandMenu.isOpen)
    }

    private func makeOpenPalmSample(x: CGFloat, y: CGFloat, time: TimeInterval, confidence: Float = 0.9) -> HandSample {
        let joints: [HandJointName: HandJoint] = [
            .wrist: HandJoint(name: .wrist, position: CGPoint(x: x, y: y - 0.15), confidence: confidence),
            .middleMCP: HandJoint(name: .middleMCP, position: CGPoint(x: x, y: y), confidence: confidence),
            .indexMCP: HandJoint(name: .indexMCP, position: CGPoint(x: x - 0.04, y: y), confidence: confidence),
            .ringMCP: HandJoint(name: .ringMCP, position: CGPoint(x: x + 0.04, y: y), confidence: confidence),
            .littleMCP: HandJoint(name: .littleMCP, position: CGPoint(x: x + 0.08, y: y), confidence: confidence),
            .indexPIP: HandJoint(name: .indexPIP, position: CGPoint(x: x - 0.04, y: y + 0.08), confidence: confidence),
            .indexTip: HandJoint(name: .indexTip, position: CGPoint(x: x - 0.04, y: y + 0.18), confidence: confidence),
            .middlePIP: HandJoint(name: .middlePIP, position: CGPoint(x: x, y: y + 0.09), confidence: confidence),
            .middleTip: HandJoint(name: .middleTip, position: CGPoint(x: x, y: y + 0.20), confidence: confidence),
            .ringPIP: HandJoint(name: .ringPIP, position: CGPoint(x: x + 0.04, y: y + 0.08), confidence: confidence),
            .ringTip: HandJoint(name: .ringTip, position: CGPoint(x: x + 0.04, y: y + 0.18), confidence: confidence),
            .littlePIP: HandJoint(name: .littlePIP, position: CGPoint(x: x + 0.08, y: y + 0.07), confidence: confidence),
            .littleTip: HandJoint(name: .littleTip, position: CGPoint(x: x + 0.08, y: y + 0.16), confidence: confidence),
            .thumbTip: HandJoint(name: .thumbTip, position: CGPoint(x: x - 0.10, y: y), confidence: confidence)
        ]

        return HandSample(
            hostTimestamp: time,
            presentationTimeSeconds: time,
            isPresentationTimeEstimated: false,
            joints: joints,
            overallConfidence: confidence,
            estimatedHandedness: .right,
            trackingID: 1
        )
    }

    func testSwipeLeftDetectedWhenPalmMovesHorizontallyToLeft() {
        let detector = PalmSwipeDetector()

        // Move from right to left across camera (x: 0.60 -> 0.54 -> 0.40)
        let s1 = makeOpenPalmSample(x: 0.60, y: 0.50, time: 100.00)
        let s2 = makeOpenPalmSample(x: 0.54, y: 0.50, time: 100.05)
        let s3 = makeOpenPalmSample(x: 0.40, y: 0.51, time: 100.12)

        XCTAssertNil(detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 100.00))
        XCTAssertNil(detector.evaluate(sample: s2, isOpenPalm: true, timestamp: 100.05))
        let result = detector.evaluate(sample: s3, isOpenPalm: true, timestamp: 100.12)

        XCTAssertEqual(result, .left, "Horizontal movement to visual left (dx < 0) must detect as .left")
    }

    func testSwipeRightDetectedWhenPalmMovesHorizontallyToRight() {
        let detector = PalmSwipeDetector()

        // Move from left to right across camera (x: 0.40 -> 0.46 -> 0.60)
        let s1 = makeOpenPalmSample(x: 0.40, y: 0.50, time: 100.00)
        let s2 = makeOpenPalmSample(x: 0.46, y: 0.50, time: 100.05)
        let s3 = makeOpenPalmSample(x: 0.60, y: 0.51, time: 100.12)

        XCTAssertNil(detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 100.00))
        XCTAssertNil(detector.evaluate(sample: s2, isOpenPalm: true, timestamp: 100.05))
        let result = detector.evaluate(sample: s3, isOpenPalm: true, timestamp: 100.12)

        XCTAssertEqual(result, .right, "Horizontal movement to visual right (dx > 0) must detect as .right")
    }

    func testStationaryPalmDoesNotTriggerSwipeAndEntersRest() {
        let detector = PalmSwipeDetector()

        // Stationary palm hovering around (0.50, 0.50)
        let s1 = makeOpenPalmSample(x: 0.500, y: 0.50, time: 100.00)
        let s2 = makeOpenPalmSample(x: 0.504, y: 0.50, time: 100.10)
        let s3 = makeOpenPalmSample(x: 0.502, y: 0.50, time: 100.20)
        let s4 = makeOpenPalmSample(x: 0.501, y: 0.50, time: 100.30)

        XCTAssertNil(detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 100.00))
        XCTAssertNil(detector.evaluate(sample: s2, isOpenPalm: true, timestamp: 100.10))
        XCTAssertNil(detector.evaluate(sample: s3, isOpenPalm: true, timestamp: 100.20))
        XCTAssertNil(detector.evaluate(sample: s4, isOpenPalm: true, timestamp: 100.30))

        XCTAssertFalse(detector.isCandidateActive, "After candidateTimeout, stationary palm candidate must settle to rest")
    }

    func testDiagonalOrVerticalMotionRejected() {
        let detector = PalmSwipeDetector()

        // Diagonal motion with high vertical component: dx = 0.15, dy = 0.25
        let s1 = makeOpenPalmSample(x: 0.40, y: 0.25, time: 100.00)
        let s2 = makeOpenPalmSample(x: 0.48, y: 0.38, time: 100.09)
        let s3 = makeOpenPalmSample(x: 0.55, y: 0.50, time: 100.18)

        XCTAssertNil(detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 100.00))
        XCTAssertNil(detector.evaluate(sample: s2, isOpenPalm: true, timestamp: 100.09))
        let result = detector.evaluate(sample: s3, isOpenPalm: true, timestamp: 100.18)

        XCTAssertNil(result, "Vertical/diagonal hand movements must be rejected by horizontal dominance filter")
    }

    func testLowConfidenceOrMissingPalmDataResetsSafely() {
        let detector = PalmSwipeDetector()

        let s1 = makeOpenPalmSample(x: 0.60, y: 0.50, time: 100.00)
        _ = detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 100.00)

        // Drop confidence below threshold (0.15 < 0.30)
        let sLow = makeOpenPalmSample(x: 0.54, y: 0.50, time: 100.05, confidence: 0.15)
        let resultLow = detector.evaluate(sample: sLow, isOpenPalm: true, timestamp: 100.05)
        XCTAssertNil(resultLow)

        // Recovery frame: history must have been reset safely
        let sRecover = makeOpenPalmSample(x: 0.40, y: 0.50, time: 100.12)
        let resultRecover = detector.evaluate(sample: sRecover, isOpenPalm: true, timestamp: 100.12)
        XCTAssertNil(resultRecover, "Single frame after drop cannot complete a multi-frame swipe")
    }

    func testCooldownAndReturnStrokeCannotReverseTrigger() {
        let detector = PalmSwipeDetector()

        // 1. Initial swipe left (x: 0.60 -> 0.54 -> 0.40)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.60, y: 0.50, time: 100.00), isOpenPalm: true, timestamp: 100.00)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.54, y: 0.50, time: 100.05), isOpenPalm: true, timestamp: 100.05)
        let swipe1 = detector.evaluate(sample: makeOpenPalmSample(x: 0.40, y: 0.50, time: 100.12), isOpenPalm: true, timestamp: 100.12)
        XCTAssertEqual(swipe1, .left)

        // 2. Return stroke during cooldown (x: 0.40 -> 0.60 in 0.12s, t = 100.20 to 100.32)
        let r1 = detector.evaluate(sample: makeOpenPalmSample(x: 0.45, y: 0.50, time: 100.20), isOpenPalm: true, timestamp: 100.20)
        let r2 = detector.evaluate(sample: makeOpenPalmSample(x: 0.52, y: 0.50, time: 100.25), isOpenPalm: true, timestamp: 100.25)
        let r3 = detector.evaluate(sample: makeOpenPalmSample(x: 0.65, y: 0.50, time: 100.32), isOpenPalm: true, timestamp: 100.32)

        XCTAssertNil(r1)
        XCTAssertNil(r2)
        XCTAssertNil(r3, "Return stroke during cooldown must never trigger reverse swipe")

        // 3. Even after cooldown (t = 100.75), if hand did not re-arm, return motion must NOT trigger
        let r4 = detector.evaluate(sample: makeOpenPalmSample(x: 0.80, y: 0.50, time: 100.75), isOpenPalm: true, timestamp: 100.75)
        XCTAssertNil(r4, "Un-rearmed detector must not trigger swipe")
    }

    func testPalmMustReArmBeforeSecondSwipe() {
        let detector = PalmSwipeDetector()

        // First swipe: left (x: 0.60 -> 0.54 -> 0.40)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.60, y: 0.50, time: 100.00), isOpenPalm: true, timestamp: 100.00)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.54, y: 0.50, time: 100.05), isOpenPalm: true, timestamp: 100.05)
        let s1 = detector.evaluate(sample: makeOpenPalmSample(x: 0.40, y: 0.50, time: 100.12), isOpenPalm: true, timestamp: 100.12)
        XCTAssertEqual(s1, .left)

        // Hand leaves open-palm pose (e.g. relaxed fist or pointing pose)
        _ = detector.evaluate(sample: nil, isOpenPalm: false, timestamp: 100.30)

        // Hand re-enters open palm after cooldown and performs swipe right (x: 0.40 -> 0.46 -> 0.60)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.40, y: 0.50, time: 101.00), isOpenPalm: true, timestamp: 101.00)
        _ = detector.evaluate(sample: makeOpenPalmSample(x: 0.46, y: 0.50, time: 101.05), isOpenPalm: true, timestamp: 101.05)
        let s2 = detector.evaluate(sample: makeOpenPalmSample(x: 0.60, y: 0.50, time: 101.12), isOpenPalm: true, timestamp: 101.12)

        XCTAssertEqual(s2, .right, "Re-armed detector must cleanly detect second swipe")
    }

    func testCorrectKeyEventSequenceEmittedForEachDirection() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = { true }

        // Emit Left Swipe: Control-down, LeftArrow-down, LeftArrow-up, Control-up
        coordinator.enqueueSwipe(direction: .left, epoch: 1)

        let expLeft = expectation(description: "Swipe Left processed")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.15) {
            let events = poster.allEvents
            XCTAssertEqual(events.count, 4)
            XCTAssertEqual(events[0], .keyEvent(virtualKey: 59, keyDown: true, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[1], .keyEvent(virtualKey: 123, keyDown: true, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[2], .keyEvent(virtualKey: 123, keyDown: false, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[3], .keyEvent(virtualKey: 59, keyDown: false, flags: 0))
            expLeft.fulfill()
        }
        wait(for: [expLeft], timeout: 1.0)

        poster.reset()

        // Emit Right Swipe: Control-down, RightArrow-down, RightArrow-up, Control-up
        coordinator.enqueueSwipe(direction: .right, epoch: 1)

        let expRight = expectation(description: "Swipe Right processed")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.15) {
            let events = poster.allEvents
            XCTAssertEqual(events.count, 4)
            XCTAssertEqual(events[0], .keyEvent(virtualKey: 59, keyDown: true, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[1], .keyEvent(virtualKey: 124, keyDown: true, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[2], .keyEvent(virtualKey: 124, keyDown: false, flags: CGEventFlags.maskControl.rawValue))
            XCTAssertEqual(events[3], .keyEvent(virtualKey: 59, keyDown: false, flags: 0))
            expRight.fulfill()
        }
        wait(for: [expRight], timeout: 1.0)
    }

    func testStaleEpochDisabledInjectionDeniedPermissionArbitrationCauseZeroKeyEvents() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)

        // 1. Stale epoch
        coordinator.epochProvider = { 2 }
        coordinator.injectionAllowedProvider = { true }
        coordinator.enqueueSwipe(direction: .left, epoch: 1)

        // 2. Disabled injection
        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = { false }
        coordinator.enqueueSwipe(direction: .right, epoch: 1)

        let exp = expectation(description: "Wait queue drain")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.05) {
            XCTAssertEqual(poster.allEvents.count, 0, "Zero key events must be emitted when epoch is stale or injection disabled")
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
    }

    func testSwipeIsSuppressedDuringPinchDragScroll() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // Put state machine into .pinchArmed
        let thumbTip = CGPoint(x: 0.5, y: 0.5)
        let indexTip = CGPoint(x: 0.54, y: 0.5)
        let pinchSample = HandSample(
            hostTimestamp: 100.00,
            presentationTimeSeconds: 100.00,
            isPresentationTimeEstimated: false,
            joints: [
                .wrist: HandJoint(name: .wrist, position: CGPoint(x: 0.5, y: 0.2), confidence: 0.9),
                .middleMCP: HandJoint(name: .middleMCP, position: CGPoint(x: 0.5, y: 0.4), confidence: 0.9),
                .thumbTip: HandJoint(name: .thumbTip, position: thumbTip, confidence: 0.9),
                .indexTip: HandJoint(name: .indexTip, position: indexTip, confidence: 0.9),
                .indexMCP: HandJoint(name: .indexMCP, position: CGPoint(x: 0.5, y: 0.35), confidence: 0.9),
                .littleMCP: HandJoint(name: .littleMCP, position: CGPoint(x: 0.55, y: 0.35), confidence: 0.9)
            ],
            overallConfidence: 0.9,
            estimatedHandedness: .right,
            trackingID: 1
        )

        fsm.processFrame(sample: pinchSample, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // While in pinchArmed, feed an open-palm sample moving fast to the left
        let movingPalm = makeOpenPalmSample(x: 0.30, y: 0.50, time: 100.10)
        fsm.processFrame(sample: movingPalm, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)

        // Invariant: Must NOT emit any swipe while in active pinchArmed!
        XCTAssertEqual(delegate.swipes.count, 0, "Palm swipe must never trigger when transitioning from active pinch")
    }

    func testPoseClassifierRecognizesThreeExtendedFingersAsOpenPalm() {
        // Create sample with index, middle, ring extended, but pinky missing (natural hand posture / low conf pinky)
        let sample = makeOpenPalmSample(x: 0.50, y: 0.50, time: 100.00)
        var joints = sample.joints
        joints.removeValue(forKey: .littleTip)
        joints.removeValue(forKey: .littlePIP)

        let modifiedSample = HandSample(
            hostTimestamp: 100.00,
            presentationTimeSeconds: 100.00,
            isPresentationTimeEstimated: false,
            joints: joints,
            overallConfidence: 0.85,
            estimatedHandedness: .right,
            trackingID: 1
        )

        let features = PoseClassifier.classify(sample: modifiedSample)
        XCTAssertTrue(features.isOpenPalm, "Open palm must be reliably recognized when 3 out of 4 fingers are extended")
        XCTAssertFalse(features.isTwoFingerPointing)
    }

    func testPoseClassifierRejectsPinchAsOpenPalm() {
        // OK sign / pinch: thumb and index tips touch (pinchDist is tiny), other fingers extended
        let sample = makeOpenPalmSample(x: 0.50, y: 0.50, time: 100.00)
        var joints = sample.joints
        let indexTipPos = joints[.indexTip]!.position
        // Move thumb tip directly on top of index tip
        joints[.thumbTip] = HandJoint(name: .thumbTip, position: indexTipPos, confidence: 0.9)

        let okSignSample = HandSample(
            hostTimestamp: 100.00,
            presentationTimeSeconds: 100.00,
            isPresentationTimeEstimated: false,
            joints: joints,
            overallConfidence: 0.9,
            estimatedHandedness: .right,
            trackingID: 1
        )

        let features = PoseClassifier.classify(sample: okSignSample)
        XCTAssertFalse(features.isOpenPalm, "Active pinch / OK sign must never be classified as open palm")
    }

    func testStationaryPalmEntersPalmRestState() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // Stationary palm samples past candidate timeout (0.15s)
        let s1 = makeOpenPalmSample(x: 0.50, y: 0.50, time: 100.00)
        let s2 = makeOpenPalmSample(x: 0.501, y: 0.50, time: 100.10)
        let s3 = makeOpenPalmSample(x: 0.502, y: 0.50, time: 100.25)

        fsm.processFrame(sample: s1, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        fsm.processFrame(sample: s2, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        fsm.processFrame(sample: s3, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)

        XCTAssertEqual(fsm.currentState, .palmRest, "Stationary open palm must enter explicit .palmRest state")
    }

    func testOpenPalmGracePeriodBridgesSingleFrameDrop() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // Frame 1: Palm at x = 0.60
        let s1 = makeOpenPalmSample(x: 0.60, y: 0.50, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: CGPoint(x: 600, y: 500), currentEpoch: 1, isInjectionAllowed: true)

        // Frame 2: Transient blur frame at x = 0.52 where ring tip dropped, but hand is still open (33ms later)
        let s2 = makeOpenPalmSample(x: 0.52, y: 0.50, time: 100.04)
        var blurJoints = s2.joints
        blurJoints.removeValue(forKey: .ringTip)
        let sBlur = HandSample(
            hostTimestamp: 100.04,
            presentationTimeSeconds: 100.04,
            isPresentationTimeEstimated: false,
            joints: blurJoints,
            overallConfidence: 0.7,
            estimatedHandedness: .right,
            trackingID: 1
        )
        fsm.processFrame(sample: sBlur, mappedCursorLocation: CGPoint(x: 520, y: 500), currentEpoch: 1, isInjectionAllowed: true)

        // Frame 3: Recovery frame at x = 0.40 completing horizontal swipe left (100.10s)
        let s3 = makeOpenPalmSample(x: 0.40, y: 0.50, time: 100.10)
        fsm.processFrame(sample: s3, mappedCursorLocation: CGPoint(x: 400, y: 500), currentEpoch: 1, isInjectionAllowed: true)

        XCTAssertEqual(delegate.swipes.count, 1, "Grace period must allow swipe to complete despite 1-frame blur dropout")
        XCTAssertEqual(delegate.swipes.first, .left)
    }

    func testSwipeAfterStationaryRestPeriodIsDetectedWithoutVelocityDilution() {
        let detector = PalmSwipeDetector()

        // 1. Hand rests stationary at x = 0.50 for 1.0 second (t = 100.00 to 101.00)
        for t in stride(from: 100.00, through: 101.00, by: 0.05) {
            let sample = makeOpenPalmSample(x: 0.50, y: 0.50, time: t)
            XCTAssertNil(detector.evaluate(sample: sample, isOpenPalm: true, timestamp: t))
        }

        // 2. User immediately performs swipe to the left over 0.12s (x: 0.50 -> 0.44 -> 0.38)
        let s1 = makeOpenPalmSample(x: 0.44, y: 0.50, time: 101.06)
        let s2 = makeOpenPalmSample(x: 0.38, y: 0.50, time: 101.12)

        _ = detector.evaluate(sample: s1, isOpenPalm: true, timestamp: 101.06)
        let result = detector.evaluate(sample: s2, isOpenPalm: true, timestamp: 101.12)

        XCTAssertEqual(result, .left, "Swipe after resting must be detected without velocity being diluted by stationary history")
    }

    func testSwitchAppSequenceEmitsCommandTab() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = { true }

        // Emit Right Swipe with .switchApp
        coordinator.enqueueSwipe(direction: .right, action: .switchApp, epoch: 1)

        let exp = expectation(description: "Switch app processed")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.15) {
            let events = poster.allEvents
            XCTAssertEqual(events.count, 4)
            // Cmd down, Tab down, Tab up, Cmd up
            XCTAssertEqual(events[0], .keyEvent(virtualKey: 55, keyDown: true, flags: CGEventFlags.maskCommand.rawValue))
            XCTAssertEqual(events[1], .keyEvent(virtualKey: 48, keyDown: true, flags: CGEventFlags.maskCommand.rawValue))
            XCTAssertEqual(events[2], .keyEvent(virtualKey: 48, keyDown: false, flags: CGEventFlags.maskCommand.rawValue))
            XCTAssertEqual(events[3], .keyEvent(virtualKey: 55, keyDown: false, flags: 0))
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
    }

    func testTransitionFromPalmRestToPointerEngagesWithoutLagOnIndexLift() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = true
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // 1. Hand settles into .palmRest
        let sPalm1 = makeOpenPalmSample(x: 0.50, y: 0.50, time: 100.00)
        let sPalm2 = makeOpenPalmSample(x: 0.501, y: 0.50, time: 100.25)
        fsm.processFrame(sample: sPalm1, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        fsm.processFrame(sample: sPalm2, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .palmRest)

        // 2. User lifts index finger into pointing pose at t = 100.30
        let sPointer1 = makePointerSample(x: 0.50, y: 0.50, time: 100.30)
        fsm.processFrame(sample: sPointer1, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        // Must immediately leave .palmRest (open palm grace bypassed)
        XCTAssertNotEqual(fsm.currentState, .palmRest)

        // 3. Next frame at t = 100.36 (60ms later >= 50ms clutch dwell): pointer must engage!
        let sPointer2 = makePointerSample(x: 0.52, y: 0.50, time: 100.36)
        fsm.processFrame(sample: sPointer2, mappedCursorLocation: CGPoint(x: 520, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pointer, "Pointer tracking must engage within 60ms of lifting index finger")
        XCTAssertGreaterThanOrEqual(delegate.moves.count, 1, "Cursor movement must begin immediately without freeze")
    }

    func testThumbIndexContactArmsPinchAndReleaseEmitsClick() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let cursorLoc = CGPoint(x: 600, y: 400)

        // 1. User points at screen (pinch dist = 0.50)
        let sPoint = makePinchContactSample(x: 0.50, y: 0.50, time: 100.00, pinchDistRatio: 0.50)
        fsm.processFrame(sample: sPoint, mappedCursorLocation: cursorLoc, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pointer)

        // 2. Thumb and index finger join (pinch dist = 0.27 <= 0.28 startThreshold)
        let sPinch = makePinchContactSample(x: 0.50, y: 0.50, time: 100.05, pinchDistRatio: 0.27)
        fsm.processFrame(sample: sPinch, mappedCursorLocation: cursorLoc, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed, "Joining thumb and index finger at 0.27 ratio must reliably arm pinch")

        // 3. User releases fingers (pinch dist = 0.40 >= 0.38 releaseThreshold)
        let sRelease = makePinchContactSample(x: 0.50, y: 0.50, time: 100.12, pinchDistRatio: 0.40)
        fsm.processFrame(sample: sRelease, mappedCursorLocation: cursorLoc, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pointer)
        XCTAssertEqual(delegate.clickAnchors.count, 1, "Releasing pinch must emit clean click")
        XCTAssertEqual(delegate.dragStarts.count, 0, "No drag events should be emitted during click")
    }

    func testPalmCandidateSmoothlyMaintainsDetectedStateDuringEarlyMotion() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // 1. Stationary palm
        let s1 = makeOpenPalmSample(x: 0.50, y: 0.50, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .palmRest)

        // 2. Hand begins sweeping horizontally (dx = 0.025 >= 0.018)
        let s2 = makeOpenPalmSample(x: 0.475, y: 0.50, time: 100.06)
        fsm.processFrame(sample: s2, mappedCursorLocation: CGPoint(x: 475, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .palmCandidate, "Early horizontal movement must transition to .palmCandidate ('PALM DETECTED')")
    }

    private func makePointerSample(x: CGFloat, y: CGFloat, time: TimeInterval) -> HandSample {
        let indexTip = CGPoint(x: x, y: y)
        let indexMCP = CGPoint(x: x, y: y - 0.08)
        let wrist = CGPoint(x: x, y: y - 0.16)
        let middleMCP = CGPoint(x: x + 0.02, y: y - 0.08)
        let middleTip = CGPoint(x: x + 0.02, y: y - 0.10)
        let joints: [HandJointName: HandJoint] = [
            .wrist: HandJoint(name: .wrist, position: wrist, confidence: 0.9),
            .indexMCP: HandJoint(name: .indexMCP, position: indexMCP, confidence: 0.9),
            .indexTip: HandJoint(name: .indexTip, position: indexTip, confidence: 0.9),
            .middleMCP: HandJoint(name: .middleMCP, position: middleMCP, confidence: 0.9),
            .middleTip: HandJoint(name: .middleTip, position: middleTip, confidence: 0.9),
            .thumbTip: HandJoint(name: .thumbTip, position: CGPoint(x: x - 0.05, y: y - 0.04), confidence: 0.9)
        ]
        return HandSample(
            hostTimestamp: time,
            presentationTimeSeconds: time,
            isPresentationTimeEstimated: false,
            joints: joints,
            overallConfidence: 0.9,
            estimatedHandedness: .right,
            trackingID: 1
        )
    }

    private func makePinchContactSample(x: CGFloat, y: CGFloat, time: TimeInterval, pinchDistRatio: CGFloat) -> HandSample {
        let wrist = CGPoint(x: x, y: y - 0.10)
        let middleMCP = CGPoint(x: x, y: y)
        let indexTip = CGPoint(x: x + 0.02, y: y + 0.05)
        let thumbTip = CGPoint(x: x + 0.02 + pinchDistRatio * 0.10, y: y + 0.05)
        let joints: [HandJointName: HandJoint] = [
            .wrist: HandJoint(name: .wrist, position: wrist, confidence: 0.9),
            .middleMCP: HandJoint(name: .middleMCP, position: middleMCP, confidence: 0.9),
            .indexMCP: HandJoint(name: .indexMCP, position: CGPoint(x: x + 0.02, y: y), confidence: 0.9),
            .indexTip: HandJoint(name: .indexTip, position: indexTip, confidence: 0.9),
            .thumbTip: HandJoint(name: .thumbTip, position: thumbTip, confidence: 0.9)
        ]
        return HandSample(
            hostTimestamp: time,
            presentationTimeSeconds: time,
            isPresentationTimeEstimated: false,
            joints: joints,
            overallConfidence: 0.9,
            estimatedHandedness: .right,
            trackingID: 1
        )
    }
}
