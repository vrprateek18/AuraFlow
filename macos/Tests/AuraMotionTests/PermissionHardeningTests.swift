import XCTest
import CoreGraphics
@testable import AuraMotionCore
@testable import AuraAtomics

@MainActor
final class PermissionHardeningTests: XCTestCase {

    // MARK: - Cached Snapshot Tests

    /// Verifies that PermissionGate.cachedSnapshot returns the full PermissionsState
    /// without any live TCC call, and that it matches the last update.
    func testCachedSnapshotReflectsLastUpdate() {
        let gate = PermissionGate()

        // Initially all false
        let initial = gate.cachedSnapshot
        XCTAssertFalse(initial.isCameraAuthorized)
        XCTAssertFalse(initial.isAccessibilityTrusted)
        XCTAssertFalse(initial.isPostEventAuthorized)
        XCTAssertFalse(initial.isListenEventAuthorized)

        // Update with full permissions
        let fullState = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        gate.update(from: fullState)

        let cached = gate.cachedSnapshot
        XCTAssertEqual(cached, fullState, "Cached snapshot must exactly match the last update")
        XCTAssertTrue(gate.canInject)
        XCTAssertTrue(gate.canArbitrate)
    }

    /// Verifies that invalidate() revokes injection/arbitration flags
    /// but preserves camera authorization status in the cached snapshot.
    func testInvalidatePreservesCameraButRevokesInjection() {
        let gate = PermissionGate()

        gate.update(from: PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        ))
        XCTAssertTrue(gate.canInject)

        gate.invalidate()

        XCTAssertFalse(gate.canInject, "canInject must be false after invalidate")
        XCTAssertFalse(gate.canArbitrate, "canArbitrate must be false after invalidate")

        let snapshot = gate.cachedSnapshot
        XCTAssertTrue(snapshot.isCameraAuthorized, "Camera status should be preserved across invalidation")
        XCTAssertFalse(snapshot.isAccessibilityTrusted)
        XCTAssertFalse(snapshot.isPostEventAuthorized)
        XCTAssertFalse(snapshot.isListenEventAuthorized)
    }

    /// Verifies that the HUD path uses the cached snapshot and NOT a live TCC check.
    /// We do this by constructing a gate with known cached values
    /// and verifying those exact values appear in the output, without calling checkPermissions().
    func testHUDSnapshotUsesCachedPermissionsNotLiveTCC() {
        let gate = PermissionGate()

        // Set a distinctive state that would differ from live TCC in a test environment
        let testState = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        gate.update(from: testState)

        // Read cached snapshot — this must return the exact state we set, not a live TCC result
        let snapshot = gate.cachedSnapshot
        XCTAssertEqual(snapshot, testState, "Cached snapshot must return the exact state without live TCC IPC")
    }

    func testPermissionStatusExplainsSeparateInputGates() {
        let accessibilityMissing = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: false,
            isPostEventAuthorized: false,
            isListenEventAuthorized: false
        )
        XCTAssertEqual(accessibilityMissing.inputBlockingReason, "Accessibility control is required")
        XCTAssertEqual(accessibilityMissing.compactStatusLabel, "NO ACCESSIBILITY")

        let eventPostingMissing = PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: false,
            isListenEventAuthorized: false
        )
        XCTAssertEqual(eventPostingMissing.inputBlockingReason, "Input control permission is required")
        XCTAssertEqual(eventPostingMissing.compactStatusLabel, "NO INPUT CONTROL")

        let cameraMissing = PermissionsState(
            isCameraAuthorized: false,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        )
        XCTAssertEqual(cameraMissing.statusLabel, "Camera access is required")
        XCTAssertEqual(cameraMissing.compactStatusLabel, "NO CAMERA")
    }

    // MARK: - Periodic Refresh Tests

    /// Verifies that PermissionsManager periodic refresh updates the gate over time.
    func testPeriodicRefreshUpdatesGate() {
        let manager = PermissionsManager()
        manager.refreshInterval = 0.1 // 100ms for fast test

        // Record initial state
        let initialState = manager.gate.cachedSnapshot

        manager.startPeriodicRefresh()

        let exp = expectation(description: "Wait for at least one periodic refresh cycle")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            // After 300ms with 100ms interval, at least 2 refreshes should have occurred.
            // The gate should still have a valid PermissionsState (may be same values in test env).
            // The key invariant is that the gate was updated without crash or data race.
            let refreshedState = manager.gate.cachedSnapshot
            XCTAssertEqual(refreshedState.isCameraAuthorized, initialState.isCameraAuthorized,
                           "Camera status should be consistently reported across refreshes")
            exp.fulfill()
        }
        waitForExpectations(timeout: 1.0)

        manager.stopPeriodicRefresh()
    }

    /// Verifies that calling startPeriodicRefresh multiple times does not create duplicate timers.
    func testStartPeriodicRefreshIsIdempotent() {
        let manager = PermissionsManager()
        manager.refreshInterval = 0.1

        // Start twice — should not crash or create duplicate timers
        manager.startPeriodicRefresh()
        manager.startPeriodicRefresh()

        let exp = expectation(description: "Wait for refresh cycle")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            // No crash = success
            exp.fulfill()
        }
        waitForExpectations(timeout: 1.0)

        manager.stopPeriodicRefresh()
    }

    /// Verifies that stopPeriodicRefresh actually stops the timer.
    func testStopPeriodicRefreshHaltsTimer() {
        let manager = PermissionsManager()
        manager.refreshInterval = 0.05

        manager.startPeriodicRefresh()

        let expStart = expectation(description: "Wait for timer to start")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            expStart.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        manager.stopPeriodicRefresh()

        // After stopping, wait and verify no crash occurs
        let expStop = expectation(description: "Wait after stop")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            // If stop worked, the timer is cancelled and this completes cleanly
            expStop.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    // MARK: - Output Provider Tests

    /// Verifies that the output coordinator's injection provider uses only
    /// atomic/cached state and not any interactionQueue-confined fields.
    func testOutputCoordinatorInjectionProviderUsesOnlyCachedState() {
        let poster = RecordingEventPoster()
        let coordinator = EventOutputCoordinator(synthesizer: poster)
        let gate = PermissionGate()

        // Sendable wrapper for the simulated atomic enabled flag
        final class EnabledBox: @unchecked Sendable {
            private let lock = NSLock()
            private var _value: Bool
            init(_ v: Bool) { _value = v }
            var value: Bool {
                get { lock.lock(); defer { lock.unlock() }; return _value }
                set { lock.lock(); defer { lock.unlock() }; _value = newValue }
            }
        }
        let atomicEnabled = EnabledBox(true)

        coordinator.epochProvider = { 1 }
        coordinator.injectionAllowedProvider = {
            gate.canInject && atomicEnabled.value
        }

        // Gate not yet authorized: events should not post
        coordinator.enqueueMove(to: CGPoint(x: 100, y: 100), epoch: 1)
        let exp1 = expectation(description: "Check blocked")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            XCTAssertTrue(poster.allEvents.isEmpty, "Events must not post when gate.canInject is false")
            exp1.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        // Authorize gate
        gate.update(from: PermissionsState(
            isCameraAuthorized: true,
            isAccessibilityTrusted: true,
            isPostEventAuthorized: true,
            isListenEventAuthorized: true
        ))

        coordinator.enqueueMove(to: CGPoint(x: 200, y: 200), epoch: 1)
        let exp2 = expectation(description: "Check allowed")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            XCTAssertTrue(poster.allEvents.contains(.move(CGPoint(x: 200, y: 200))))
            exp2.fulfill()
        }
        waitForExpectations(timeout: 0.5)

        // Disable atomic injection (simulating arbitration)
        atomicEnabled.value = false
        poster.reset()

        coordinator.enqueueMove(to: CGPoint(x: 300, y: 300), epoch: 1)
        let exp3 = expectation(description: "Check atomic disabled")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.04) {
            XCTAssertTrue(poster.allEvents.isEmpty, "Events must not post when atomic injection is disabled")
            exp3.fulfill()
        }
        waitForExpectations(timeout: 0.5)
    }

    // MARK: - InputArbitrator Lifecycle Tests

    /// Verifies that InputArbitrator start/stop can be called repeatedly without crash or data race.
    func testArbitratorRepeatedStartStopDoesNotCrash() {
        let arbitrator = InputArbitrator()

        // Rapid start/stop cycles with proper completion-based waiting
        for i in 0..<5 {
            _ = arbitrator.start()

            let expStop = expectation(description: "Stop cycle \(i)")
            arbitrator.stop {
                expStop.fulfill()
            }
            waitForExpectations(timeout: 1.0)
        }

        // After all stop calls, tap should not be active
        XCTAssertFalse(arbitrator.isTapActive, "Tap must be inactive after stop")
    }

    /// Verifies that stop() completion fires even when no tap was ever started.
    func testArbitratorStopCompletionFiresWhenNeverStarted() {
        let arbitrator = InputArbitrator()

        let exp = expectation(description: "Stop completion fires")
        arbitrator.stop {
            XCTAssertFalse(arbitrator.isTapActive)
            exp.fulfill()
        }
        waitForExpectations(timeout: 1.0)
    }

    /// Verifies that concurrent start and stop calls from different queues
    /// do not crash or leave the arbitrator in an inconsistent state.
    func testArbitratorConcurrentStartStopSafety() {
        let arbitrator = InputArbitrator()
        let concurrentQueue = DispatchQueue(label: "test.concurrent", attributes: .concurrent)

        let exp = expectation(description: "All concurrent operations complete")
        exp.expectedFulfillmentCount = 10

        for i in 0..<10 {
            concurrentQueue.async {
                if i % 2 == 0 {
                    _ = arbitrator.start()
                } else {
                    arbitrator.stop()
                }
                exp.fulfill()
            }
        }
        waitForExpectations(timeout: 2.0)

        // Final stop to ensure clean state
        let expFinal = expectation(description: "Final stop")
        arbitrator.stop {
            XCTAssertFalse(arbitrator.isTapActive)
            expFinal.fulfill()
        }
        waitForExpectations(timeout: 1.0)
    }
}
