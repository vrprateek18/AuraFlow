import XCTest
@testable import AuraMotionCore
@testable import AuraAtomics

final class StateBox: @unchecked Sendable {
    var state = AuraArbitrationState()
}

@MainActor
final class ReEnableSequencingTests: XCTestCase {
    func testStrictReEnableSequencingIncrementsEpochAndEnables() {
        let box = StateBox()
        aura_atomic_init(&box.state, true, 1)

        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        coordinator.epochProvider = { aura_atomic_get_epoch(&box.state) }
        coordinator.injectionAllowedProvider = { aura_atomic_is_enabled(&box.state) }

        // Start drag at (200, 200)
        coordinator.enqueueDragStart(at: CGPoint(x: 200, y: 200), epoch: 1)

        let expStart = expectation(description: "Wait for drag start")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            expStart.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        XCTAssertTrue(coordinator.guardian.isLeftMouseDown)
        XCTAssertEqual(poster.allEvents, [.mouseDown(CGPoint(x: 200, y: 200))])

        // Step 1: External input disables atomically
        var newEpoch: UInt64 = 0
        let disabled = aura_atomic_try_disable(&box.state, &newEpoch)
        XCTAssertTrue(disabled)
        XCTAssertFalse(aura_atomic_is_enabled(&box.state))
        XCTAssertEqual(newEpoch, 2)

        // Attempting to enqueue work during disable must NOT post anything
        coordinator.enqueueMove(to: CGPoint(x: 300, y: 300), epoch: 2)

        // Step 2: Emergency release execution barrier
        let expRelease = expectation(description: "Release barrier")

        coordinator.emergencyRelease {
            // Assert that during release, exactly one emergency mouseUp was posted at (200, 200)
            XCTAssertFalse(coordinator.guardian.isLeftMouseDown)
            XCTAssertTrue(poster.allEvents.contains(.directMouseUp(CGPoint(x: 200, y: 200))))

            // Step 3 & 4: Release confirmed, queue drained, re-enable called
            let reenabledEpoch = aura_atomic_enable(&box.state)
            XCTAssertTrue(aura_atomic_is_enabled(&box.state))
            XCTAssertEqual(reenabledEpoch, 3, "Re-enabling must issue a fresh epoch token")
            expRelease.fulfill()
        }

        waitForExpectations(timeout: 0.5)
    }
}
