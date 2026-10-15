import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class MockStateMachineDelegate: GestureStateMachineDelegate, @unchecked Sendable {
    var states: [GestureState] = []
    var moves: [CGPoint] = []
    var clickAnchors: [CGPoint] = []
    var dragStarts: [CGPoint] = []
    var dragMoves: [CGPoint] = []
    var dragEnds: [CGPoint] = []
    var scrolls: [ScrollDelta] = []
    var swipes: [PalmSwipeDirection] = []
    var shortcuts: [FingerShortcut] = []
    var commands: [GestureCommand] = []
    func stateMachine(_ fsm: GestureStateMachine, emitCommand command: GestureCommand, at target: CGPoint, epoch: UInt64) {
        commands.append(command)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitShortcut shortcut: FingerShortcut, epoch: UInt64) {
        shortcuts.append(shortcut)
    }
    var emergencyReleaseCount: Int = 0

    func stateMachine(_ fsm: GestureStateMachine, didTransitionTo state: GestureState) {
        states.append(state)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitMoveTo location: CGPoint, epoch: UInt64) {
        moves.append(location)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitClickAt anchor: CGPoint, epoch: UInt64) {
        clickAnchors.append(anchor)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitDragStartAt anchor: CGPoint, epoch: UInt64) {
        dragStarts.append(anchor)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitDragMoveTo location: CGPoint, epoch: UInt64) {
        dragMoves.append(location)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitDragEndAt location: CGPoint, epoch: UInt64) {
        dragEnds.append(location)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitScroll delta: ScrollDelta, epoch: UInt64) {
        scrolls.append(delta)
    }
    func stateMachine(_ fsm: GestureStateMachine, emitSwipe direction: PalmSwipeDirection, epoch: UInt64) {
        swipes.append(direction)
    }
    func stateMachineTriggerEmergencyRelease(_ fsm: GestureStateMachine) {
        emergencyReleaseCount += 1
    }
}

final class GestureStateMachineTests: XCTestCase {
    func testContactClicksBeforeReleaseAndNeverRepeatsWhileHeld() {
        let fsm = GestureStateMachine()
        let output = MockStateMachineDelegate()
        fsm.delegate = output
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0
        for frame in 0..<20 {
            fsm.processFrame(sample: makeSample(pinchDist: 0.1, time: 100 + Double(frame) / 30), mappedCursorLocation: CGPoint(x: 400, y: 300), currentEpoch: 1, isInjectionAllowed: true)
            if frame == 2 { XCTAssertEqual(output.clickAnchors.count, 1) }
        }
        XCTAssertEqual(output.clickAnchors.count, 1)
        fsm.processFrame(sample: makeSample(pinchDist: 0.6, time: 100.7), mappedCursorLocation: CGPoint(x: 400, y: 300), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(output.clickAnchors.count, 1)
        XCTAssertTrue(output.dragStarts.isEmpty)
    }

    func testFoldedHandStopsPointerAfterClutchEngagement() {
        let fsm = GestureStateMachine()
        let output = MockStateMachineDelegate()
        fsm.delegate = output
        fsm.confidenceGate.reacquisitionDwellSeconds = 0
        for frame in 0..<10 {
            fsm.processFrame(sample: makeSample(pinchDist: 0.6, time: 100 + Double(frame) / 30), mappedCursorLocation: .zero, currentEpoch: 1, isInjectionAllowed: true)
        }
        XCTAssertFalse(output.moves.isEmpty)
        output.moves.removeAll()
        for frame in 0..<15 {
            let sample = makeSample(pinchDist: 0.6, time: 101 + Double(frame) / 30)
            var joints = sample.joints
            joints[.indexTip] = HandJoint(name: .indexTip, position: CGPoint(x: 0.5, y: 0.3), confidence: 0.9)
            let folded = HandSample(hostTimestamp: sample.hostTimestamp, presentationTimeSeconds: sample.hostTimestamp, isPresentationTimeEstimated: false, joints: joints, overallConfidence: 0.9, estimatedHandedness: .right, trackingID: 1)
            fsm.processFrame(sample: folded, mappedCursorLocation: CGPoint(x: frame * 10, y: 100), currentEpoch: 1, isInjectionAllowed: true)
        }
        XCTAssertTrue(output.moves.isEmpty)
    }

    func testConfiguredClutchDelayIsApplied() {
        let fsm = GestureStateMachine()
        fsm.clutchDwellDuration = 0.08

        XCTAssertEqual(fsm.clutchDwellDuration, 0.08, accuracy: 0.0001)
    }

    func testCleanPinchClickGeneratesZeroDragEvents() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let anchor = CGPoint(x: 500, y: 500)

        // Frame 1: Pointer pointing
        let sample1 = makeSample(pinchDist: 0.5, time: 100.0)
        fsm.processFrame(sample: sample1, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pointer)

        // Frame 2: Pinch down (pinchDist = 0.20 <= 0.28)
        let sample2 = makeSample(pinchDist: 0.20, time: 100.05)
        fsm.processFrame(sample: sample2, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // Frame 3: Pinch release at 100.12 (dwell = 70ms < 250ms, displacement = 0 <= 10pt)
        let sample3 = makeSample(pinchDist: 0.45, time: 100.12)
        fsm.processFrame(sample: sample3, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)

        // Invariant: Exactly 1 click, exactly 0 drag events!
        XCTAssertEqual(delegate.clickAnchors.count, 1)
        XCTAssertEqual(delegate.clickAnchors.first, anchor)
        XCTAssertEqual(delegate.dragStarts.count, 0, "Zero drag events must be emitted during click within deadband")
        XCTAssertEqual(delegate.dragMoves.count, 0)
    }

    func testDwellAndMotionEntersDrag() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let anchor = CGPoint(x: 500, y: 500)

        // Start pinch
        let s1 = makeSample(pinchDist: 0.20, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // Dwell > 250ms AND displacement > 10pt (t = 100.35, moved to (550, 500))
        let dragLoc = CGPoint(x: 550, y: 500)
        let s2 = makeSample(pinchDist: 0.20, time: 100.35)
        fsm.processFrame(sample: s2, mappedCursorLocation: dragLoc, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .dragging)
        XCTAssertEqual(delegate.dragStarts.count, 1)

        // Release pinch
        let s3 = makeSample(pinchDist: 0.45, time: 100.40)
        fsm.processFrame(sample: s3, mappedCursorLocation: dragLoc, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(delegate.dragEnds.count, 1)
    }

    func testScrollMutualExclusionWithPinch() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        // In pinchArmed, two-finger gesture must NOT trigger scroll
        let s1 = makeSample(pinchDist: 0.20, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: CGPoint(x: 500, y: 500), currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)
        XCTAssertEqual(delegate.scrolls.count, 0)
    }

    func testCursorMotionWhilePointingNeverAccidentallyDragsOrSelectsText() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let anchor = CGPoint(x: 500, y: 500)

        // Frame 1: Pointer pointing, thumb momentarily dips close (dist = 0.20)
        let s1 = makeSample(pinchDist: 0.20, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // Frame 2: Hand moves 40px across screen within 50ms (displacement > deadband without dwelling)
        let movingLoc = CGPoint(x: 540, y: 500)
        let s2 = makeSample(pinchDist: 0.20, time: 100.05)
        fsm.processFrame(sample: s2, mappedCursorLocation: movingLoc, currentEpoch: 1, isInjectionAllowed: true)

        // Invariant: MUST cancel false pinch, return to .pointer, and emit ZERO drag events!
        XCTAssertEqual(fsm.currentState, .pointer)
        XCTAssertEqual(delegate.dragStarts.count, 0, "Moving cursor must never accidentally start drag or select text")
        XCTAssertEqual(delegate.clickAnchors.count, 0)
    }

    func testPrePinchAnchorStabilizationLocksTargetPositionDuringFingerCurl() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let targetButton = CGPoint(x: 500, y: 500)

        // Frame 1: User hovers over target button (pinchDist = 0.50)
        let s1 = makeSample(pinchDist: 0.50, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: targetButton, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pointer)

        // Frame 2: Fingers begin closing (pinchDist = 0.32 <= 0.36 prePinchThreshold)
        let s2 = makeSample(pinchDist: 0.32, time: 100.04)
        fsm.processFrame(sample: s2, mappedCursorLocation: targetButton, currentEpoch: 1, isInjectionAllowed: true)

        // Frame 3: Finger flexes towards thumb, drifting by 23px, and contacts (pinchDist = 0.18 <= 0.25)
        let driftedTip = CGPoint(x: 518, y: 515)
        let s3 = makeSample(pinchDist: 0.18, time: 100.08)
        fsm.processFrame(sample: s3, mappedCursorLocation: driftedTip, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // Frame 4: Fingers release (pinchDist = 0.40 >= 0.35)
        let s4 = makeSample(pinchDist: 0.40, time: 100.15)
        fsm.processFrame(sample: s4, mappedCursorLocation: driftedTip, currentEpoch: 1, isInjectionAllowed: true)

        // Invariant: Click must land at targetButton (500, 500), NOT drifted position (518, 515)!
        XCTAssertEqual(delegate.clickAnchors.count, 1)
        XCTAssertEqual(delegate.clickAnchors.first, targetButton)
        XCTAssertEqual(delegate.dragStarts.count, 0)
    }

    func testMidAirTapWithinDeadbandEmitsCleanClick() {
        let fsm = GestureStateMachine()
        let delegate = MockStateMachineDelegate()
        fsm.delegate = delegate
        fsm.isClutchEnabled = false
        fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

        let anchor = CGPoint(x: 600, y: 400)

        // Frame 1: Pinch down
        let s1 = makeSample(pinchDist: 0.20, time: 100.00)
        fsm.processFrame(sample: s1, mappedCursorLocation: anchor, currentEpoch: 1, isInjectionAllowed: true)
        XCTAssertEqual(fsm.currentState, .pinchArmed)

        // Frame 2: Hand natural mid-air recoil shifts by 20px (dx=15, dy=13 => dist=19.8 <= 32pt) and releases at 100ms
        let recoiledLoc = CGPoint(x: 615, y: 413)
        let s2 = makeSample(pinchDist: 0.45, time: 100.10)
        fsm.processFrame(sample: s2, mappedCursorLocation: recoiledLoc, currentEpoch: 1, isInjectionAllowed: true)

        // Invariant: Natural mid-air hand shift must NOT cancel click!
        XCTAssertEqual(delegate.clickAnchors.count, 1)
        XCTAssertEqual(delegate.clickAnchors.first, anchor)
        XCTAssertEqual(delegate.dragStarts.count, 0)
    }

    private func makeSample(pinchDist: CGFloat, time: TimeInterval) -> HandSample {
        let thumbTip = CGPoint(x: 0.5, y: 0.5)
        let indexTip = CGPoint(x: 0.5 + pinchDist * 0.2, y: 0.5)
        let joints: [HandJointName: HandJoint] = [
            .wrist: HandJoint(name: .wrist, position: CGPoint(x: 0.5, y: 0.2), confidence: 0.9),
            .middleMCP: HandJoint(name: .middleMCP, position: CGPoint(x: 0.5, y: 0.4), confidence: 0.9),
            .thumbTip: HandJoint(name: .thumbTip, position: thumbTip, confidence: 0.9),
            .indexTip: HandJoint(name: .indexTip, position: indexTip, confidence: 0.9),
            .indexMCP: HandJoint(name: .indexMCP, position: CGPoint(x: 0.5, y: 0.35), confidence: 0.9),
            .littleMCP: HandJoint(name: .littleMCP, position: CGPoint(x: 0.55, y: 0.35), confidence: 0.9)
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
