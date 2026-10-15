import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class SafetyPolicyTests: XCTestCase {
    func testMouseButtonGuardianIdempotentRelease() {
        let guardian = MouseButtonGuardian()
        let synth = EventSynthesizer()

        XCTAssertFalse(guardian.isLeftMouseDown)

        // Mark mouse down
        guardian.markLeftMouseDown(at: CGPoint(x: 500, y: 500))
        XCTAssertTrue(guardian.isLeftMouseDown)

        // Emergency release
        guardian.releaseAllButtons(synthesizer: synth)
        XCTAssertFalse(guardian.isLeftMouseDown, "Button must be released immediately")

        // Second call must be idempotent (no duplicate release)
        guardian.releaseAllButtons(synthesizer: synth)
        XCTAssertFalse(guardian.isLeftMouseDown)
    }
}
