import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class CoordinateTransformTests: XCTestCase {
    func testPrimaryDisplayTransform() {
        let bounds = CGRect(x: 0, y: 0, width: 1920, height: 1080)
        let profile = CalibrationProfile(
            activeRegion: CGRect(x: 0.1, y: 0.1, width: 0.8, height: 0.8),
            displayBounds: bounds
        )
        let mapper = CoordinateMapper(profile: profile)

        // Center of active region (0.5, 0.5) should map to center of display
        let center = mapper.mapToQuartzGlobal(visionPoint: CGPoint(x: 0.5, y: 0.5))
        XCTAssertEqual(center.x, 960, accuracy: 5.0)
        XCTAssertEqual(center.y, 540, accuracy: 5.0)
    }

    func testSecondaryDisplayWithNegativeOrigin() {
        // Display positioned to the left of the primary screen: X in [-1920, 0]
        let bounds = CGRect(x: -1920, y: 0, width: 1920, height: 1080)
        let profile = CalibrationProfile(
            activeRegion: CGRect(x: 0.0, y: 0.0, width: 1.0, height: 1.0),
            displayBounds: bounds
        )
        let mapper = CoordinateMapper(profile: profile)

        let leftEdge = mapper.mapToQuartzGlobal(visionPoint: CGPoint(x: 0.0, y: 0.5))
        XCTAssertEqual(leftEdge.x, -1920, accuracy: 1.0)

        let rightEdge = mapper.mapToQuartzGlobal(visionPoint: CGPoint(x: 1.0, y: 0.5))
        XCTAssertEqual(rightEdge.x, 0, accuracy: 1.0)
    }

    func testBoundaryClamping() {
        let bounds = CGRect(x: 0, y: 0, width: 1000, height: 1000)
        let profile = CalibrationProfile(
            activeRegion: CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.6),
            displayBounds: bounds
        )
        let mapper = CoordinateMapper(profile: profile)

        // Point outside active region to the right (x=1.5)
        let clamped = mapper.mapToQuartzGlobal(visionPoint: CGPoint(x: 1.5, y: 0.5))
        XCTAssertLessThanOrEqual(clamped.x, 1000.0)
        XCTAssertGreaterThanOrEqual(clamped.x, 0.0)
    }
}
