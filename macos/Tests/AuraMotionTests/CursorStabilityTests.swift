import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class CursorStabilityTests: XCTestCase {
    private func controller() -> CursorController {
        CursorController(profile: CalibrationProfile(activeRegion: CGRect(x: 0, y: 0, width: 1, height: 1), displayBounds: CGRect(x: 0, y: 0, width: 1000, height: 1000)))
    }
    private func point(_ x: Double, _ y: Double = 500) -> CGPoint {
        CGPoint(x: x / 1000, y: 1 - y / 1000)
    }

    func testStationaryTremorIsSuppressedAtDifferentFrameRates() throws {
        for fps in [30.0, 60.0] {
            let cursor = controller()
            var squaredError = 0.0
            for frame in 0..<120 {
                let noisy = point(500 + sin(Double(frame) * 1.7) * 6, 500 + sin(Double(frame) * 2.1) * 6)
                let result = try XCTUnwrap(cursor.processIndexTip(normalizedPoint: noisy, timestamp: 1 + Double(frame) / fps))
                if frame >= 20 { squaredError += pow(result.x - 500, 2) + pow(result.y - 500, 2) }
            }
            XCTAssertLessThan(sqrt(squaredError / 100), 2, "Resting RMS error should be below two points at \(fps) FPS")
        }
    }

    func testSlowMotionAccumulatesAndFastMotionRemainsResponsive() throws {
        for speed in [12.0, 600.0] {
            let cursor = controller()
            var result = CGPoint.zero
            for frame in 0...30 {
                result = try XCTUnwrap(cursor.processIndexTip(normalizedPoint: point(100 + speed * Double(frame) / 60), timestamp: 1 + Double(frame) / 60))
            }
            if speed == 12 { XCTAssertGreaterThan(result.x, 102) }
            else { XCTAssertGreaterThan(result.x, 370) }
        }
    }

    func testSingleFrameSpikeAndBriefOcclusionDoNotJumpCursor() throws {
        let cursor = controller()
        let initial = try XCTUnwrap(cursor.processIndexTip(normalizedPoint: point(500), timestamp: 1))
        XCTAssertEqual(cursor.processIndexTip(normalizedPoint: point(800), timestamp: 1.033), initial)
        XCTAssertEqual(cursor.processIndexTip(normalizedPoint: nil, timestamp: 1.05), initial)
        XCTAssertEqual(cursor.processIndexTip(normalizedPoint: point(500), timestamp: 1.067), initial)
        _ = cursor.processIndexTip(normalizedPoint: point(800), timestamp: 1.1)
        let confirmed = try XCTUnwrap(cursor.processIndexTip(normalizedPoint: point(805), timestamp: 1.133))
        XCTAssertGreaterThan(confirmed.x, 500, "A confirmed large movement must not be permanently rejected")
        XCTAssertEqual(cursor.processIndexTip(normalizedPoint: point(200), timestamp: 1.01), confirmed)
    }
}
