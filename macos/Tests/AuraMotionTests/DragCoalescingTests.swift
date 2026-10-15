import XCTest
import CoreGraphics
@testable import AuraMotionCore

@MainActor
final class DragCoalescingTests: XCTestCase {
    func testEmergencyReleasePostsAtLastActuallyPostedDragCoordinate() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        let activeEpochBox = EpochBox(1)
        coordinator.epochProvider = { activeEpochBox.epoch }
        coordinator.injectionAllowedProvider = { true }

        // Start drag at (100, 100)
        coordinator.enqueueDragStart(at: CGPoint(x: 100, y: 100), epoch: 1)

        // Enqueue drag move to (150, 150) and let it drain
        coordinator.enqueueDragMove(to: CGPoint(x: 150, y: 150), epoch: 1)

        let expDrain = expectation(description: "Wait for drag move to post")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            expDrain.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        // Verify drag move was actually posted to (150, 150)
        XCTAssertTrue(poster.allEvents.contains(.mouseDragged(CGPoint(x: 150, y: 150))))

        // Now advance epoch to 2 (arbitration occurred) before next drag move
        activeEpochBox.epoch = 2

        // Enqueue unposted drag move to (999, 999) with stale epoch 1
        coordinator.enqueueDragMove(to: CGPoint(x: 999, y: 999), epoch: 1)

        // Emergency release should release at the LAST ACTUALLY POSTED coordinate (150, 150), NOT (999, 999)!
        let expRelease = expectation(description: "Emergency release completion")
        coordinator.emergencyRelease {
            XCTAssertFalse(coordinator.guardian.isLeftMouseDown)
            // Released location must match the last validated and posted position
            XCTAssertEqual(coordinator.guardian.currentLocation.x, 150, accuracy: 1.0)
            XCTAssertEqual(coordinator.guardian.currentLocation.y, 150, accuracy: 1.0)

            // Verify exactly one directMouseUp was posted at (150, 150)
            let mouseUpEvents = poster.allEvents.filter {
                if case .directMouseUp(let loc) = $0, loc == CGPoint(x: 150, y: 150) { return true }
                return false
            }
            XCTAssertEqual(mouseUpEvents.count, 1, "Must post exactly one mouseUp at the last actually posted drag coordinate")
            expRelease.fulfill()
        }

        waitForExpectations(timeout: 0.5)
    }
}
