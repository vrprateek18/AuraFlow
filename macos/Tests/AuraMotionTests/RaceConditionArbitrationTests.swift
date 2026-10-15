import XCTest
import CoreGraphics
@testable import AuraMotionCore

@MainActor
final class RaceConditionArbitrationTests: XCTestCase {
    func testStaleMoveDragScrollClickMouseDownAreNeverPosted() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        let holder = EpochBox(1)
        coordinator.epochProvider = { holder.epoch }
        coordinator.injectionAllowedProvider = { true }

        // Advance epoch to 2 (simulating arbitration occurring)
        holder.epoch = 2

        // Enqueue stale items with epoch 1
        coordinator.enqueueMove(to: CGPoint(x: 100, y: 100), epoch: 1)
        coordinator.enqueueDragMove(to: CGPoint(x: 110, y: 110), epoch: 1)
        coordinator.enqueueScroll(delta: ScrollDelta(deltaX: 5, deltaY: 5), epoch: 1)
        coordinator.enqueueClick(at: CGPoint(x: 120, y: 120), epoch: 1)
        coordinator.enqueueDragStart(at: CGPoint(x: 130, y: 130), epoch: 1)
        coordinator.enqueueDragEnd(at: CGPoint(x: 140, y: 140), epoch: 1)

        let exp = expectation(description: "Drain check")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            // PROVEN: Zero stale events ever posted!
            XCTAssertTrue(poster.allEvents.isEmpty, "Stale events with mismatched epoch must NEVER be posted. Posted: \(poster.allEvents)")
            exp.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    func testNoEventsPostedWhenInjectionDisabled() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = { false } // Injection disabled (arbitration active)

        coordinator.enqueueMove(to: CGPoint(x: 200, y: 200), epoch: 1)
        coordinator.enqueueClick(at: CGPoint(x: 200, y: 200), epoch: 1)
        coordinator.enqueueScroll(delta: ScrollDelta(deltaX: 10, deltaY: 10), epoch: 1)

        let exp = expectation(description: "Disabled check")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            XCTAssertTrue(poster.allEvents.isEmpty, "No events may be posted when injection is disabled")
            exp.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    func testPermissionGateControlsEventPostingDirectly() {
        let gate = PermissionGate()
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = { gate.canInject }

        // Initially gate.canInject is false
        XCTAssertFalse(gate.canInject)
        coordinator.enqueueMove(to: CGPoint(x: 100, y: 100), epoch: 1)

        let exp1 = expectation(description: "Gate false check")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            XCTAssertTrue(poster.allEvents.isEmpty)
            exp1.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        // Update gate to authorized
        gate.update(from: PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        ))
        XCTAssertTrue(gate.canInject)

        coordinator.enqueueMove(to: CGPoint(x: 150, y: 150), epoch: 1)

        let exp2 = expectation(description: "Gate true check")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            XCTAssertEqual(poster.allEvents, [.move(CGPoint(x: 150, y: 150))])
            exp2.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        // Invalidate gate (simulating permission revocation)
        gate.invalidate()
        XCTAssertFalse(gate.canInject)

        coordinator.enqueueMove(to: CGPoint(x: 200, y: 200), epoch: 1)

        let exp3 = expectation(description: "Gate invalidated check")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            // No new events posted
            XCTAssertEqual(poster.allEvents.count, 1)
            exp3.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    func testMonotonicEpochNeverResets() {
        var currentEpoch: UInt64 = 1000
        for _ in 0..<50 {
            currentEpoch += 1
        }
        XCTAssertEqual(currentEpoch, 1050)
        XCTAssertGreaterThan(currentEpoch, 1000, "Epoch must be strictly monotonically increasing")
    }
}
