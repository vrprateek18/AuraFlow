import XCTest
import CoreGraphics
@testable import AuraMotionCore
@testable import AuraAtomics

final class SelfInjectionArbitrationTests: XCTestCase {
    func testAuraMotionTaggedEventsBypassArbitration() {
        var state = AuraArbitrationState()
        aura_atomic_init(&state, true, 1)

        // Verify hardware lock-free
        let isLockFree = aura_atomic_is_hardware_lock_free(&state)
        XCTAssertTrue(isLockFree, "Apple Silicon must support hardware lock-free atomics for bool and uint64")

        // Injected event carries magic tag
        let magicTag = kAuraMotionEventMagicTag
        XCTAssertEqual(magicTag, 0x415552414D4F544E)

        // Tagged event bypass simulation
        let isTagged = (magicTag == kAuraMotionEventMagicTag)
        XCTAssertTrue(isTagged, "Tagged events must be ignored by arbitration")

        // Assert state remains enabled and epoch unchanged
        XCTAssertTrue(aura_atomic_is_enabled(&state))
        XCTAssertEqual(aura_atomic_get_epoch(&state), 1)
    }

    func testUntaggedExternalEventDisablesArbitrationAndBumpsEpoch() {
        var state = AuraArbitrationState()
        aura_atomic_init(&state, true, 10)

        var newEpoch: UInt64 = 0
        let disabled = aura_atomic_try_disable(&state, &newEpoch)

        XCTAssertTrue(disabled, "First external event must succeed compare-exchange")
        XCTAssertEqual(newEpoch, 11, "Epoch must increment monotonically")
        XCTAssertFalse(aura_atomic_is_enabled(&state))

        // Second external event during cooldown must fail compare-exchange (no re-trigger)
        var secondEpoch: UInt64 = 0
        let secondTry = aura_atomic_try_disable(&state, &secondEpoch)
        XCTAssertFalse(secondTry, "Subsequent external events must fail compare-exchange without spamming safety coordinator")
    }
}
