import XCTest
import CoreGraphics
import AppKit
@testable import AuraMotionCore

@MainActor
final class LifecycleTests: XCTestCase {
    func testInterruptionTriggersEmergencyRelease() {
        let env = AppEnvironment.shared
        env.outputCoordinator.guardian.markLeftMouseDown(at: CGPoint(x: 100, y: 100))
        XCTAssertTrue(env.outputCoordinator.guardian.isLeftMouseDown)

        // Simulate capture pipeline interruption
        env.capturePipelineDidInterrupted(env.capturePipeline)

        let exp = expectation(description: "Interruption release")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            XCTAssertFalse(env.outputCoordinator.guardian.isLeftMouseDown, "Button must be released on interruption")
            XCTAssertEqual(env.stateMachine.currentState, .trackingLost)
            exp.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    func testAppStopReleasesButtons() {
        let env = AppEnvironment.shared
        env.outputCoordinator.guardian.markLeftMouseDown(at: CGPoint(x: 100, y: 100))
        XCTAssertTrue(env.outputCoordinator.guardian.isLeftMouseDown)

        env.stop()

        let exp = expectation(description: "Stop release")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            XCTAssertFalse(env.outputCoordinator.guardian.isLeftMouseDown, "Button must be released on stop")
            exp.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    func testCapturePipelineAsyncLifecycle() {
        let pipeline = CapturePipeline()
        XCTAssertEqual(pipeline.state, .idle)
        XCTAssertFalse(pipeline.isRunning)

        let expConfigure = expectation(description: "Pipeline configure")
        pipeline.configure { result in
            // May succeed if camera is available or fail gracefully in headless environment
            expConfigure.fulfill()
        }
        waitForExpectations(timeout: 1.0)

        let expStop = expectation(description: "Pipeline stop")
        pipeline.stop {
            XCTAssertEqual(pipeline.state, .idle)
            XCTAssertFalse(pipeline.isRunning)
            expStop.fulfill()
        }
        waitForExpectations(timeout: 1.0)
    }

    func testCapturePipelineRapidStartStopEndsInIdle() {
        let pipeline = CapturePipeline()
        let exp = expectation(description: "Rapid start and stop serialized on captureQueue")

        pipeline.start { _ in }
        pipeline.stop {
            XCTAssertEqual(pipeline.state, .idle)
            XCTAssertFalse(pipeline.isRunning)
            exp.fulfill()
        }

        waitForExpectations(timeout: 1.0)
    }
}
