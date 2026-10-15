import XCTest
@testable import AuraMotionCore

final class LandmarkReplayTests: XCTestCase {
    func testReplayCleanPinchClickFixture() {
        guard let url = Bundle.module.url(forResource: "clean_pinch_click", withExtension: "json", subdirectory: "Fixtures") else {
            XCTFail("Fixture clean_pinch_click.json not found")
            return
        }

        let replayer = LandmarkReplayer()
        do {
            let session = try replayer.loadSession(from: url)
            XCTAssertEqual(session.samples.count, 3)

            let fsm = GestureStateMachine()
            let delegate = MockStateMachineDelegate()
            fsm.delegate = delegate
            fsm.isClutchEnabled = false
            fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

            for sample in session.samples {
                fsm.processFrame(
                    sample: sample,
                    mappedCursorLocation: CGPoint(x: 500, y: 500),
                    currentEpoch: 1,
                    isInjectionAllowed: true
                )
            }

            // Assert clean click occurred with zero drag events
            XCTAssertEqual(delegate.clickAnchors.count, 1)
            XCTAssertEqual(delegate.dragStarts.count, 0)
        } catch {
            XCTFail("Failed to load session JSON: \(error)")
        }
    }

    func testReplaySuddenHandLossFixture() {
        guard let url = Bundle.module.url(forResource: "sudden_hand_loss", withExtension: "json", subdirectory: "Fixtures") else {
            XCTFail("Fixture sudden_hand_loss.json not found")
            return
        }

        let replayer = LandmarkReplayer()
        do {
            let session = try replayer.loadSession(from: url)
            let fsm = GestureStateMachine()
            let delegate = MockStateMachineDelegate()
            fsm.delegate = delegate
            fsm.isClutchEnabled = false
            fsm.confidenceGate.reacquisitionDwellSeconds = 0.0

            for sample in session.samples {
                fsm.processFrame(
                    sample: sample,
                    mappedCursorLocation: CGPoint(x: 500, y: 500),
                    currentEpoch: 1,
                    isInjectionAllowed: true
                )
            }

            // After low confidence frames, tracking must be lost and emergency release triggered
            XCTAssertEqual(fsm.currentState, .trackingLost)
            XCTAssertGreaterThanOrEqual(delegate.emergencyReleaseCount, 1)
        } catch {
            XCTFail("Failed to load session JSON: \(error)")
        }
    }
}
