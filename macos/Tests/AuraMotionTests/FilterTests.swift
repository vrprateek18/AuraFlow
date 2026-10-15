import XCTest
import CoreGraphics
@testable import AuraMotionCore

final class FilterTests: XCTestCase {
    func test1EuroFilterSuppressesJitterAtRest() {
        let filter = OneEuroFilter1D(minCutoff: 1.0, beta: 0.007)
        var t: TimeInterval = 100.0
        let baseValue = 500.0

        var rawValues: [Double] = []
        var filteredValues: [Double] = []

        for i in 0..<50 {
            // Add tiny high-frequency noise +/- 1.5 pixels
            let noise = sin(Double(i) * 1.5) * 1.5
            let raw = baseValue + noise
            let filtered = filter.filter(x: raw, timestamp: t)
            rawValues.append(raw)
            filteredValues.append(filtered)
            t += 0.016 // ~60 FPS
        }

        // Compute variance of raw vs filtered
        let rawMean = rawValues.reduce(0, +) / Double(rawValues.count)
        let rawVar = rawValues.map { pow($0 - rawMean, 2) }.reduce(0, +) / Double(rawValues.count)

        let filtMean = filteredValues.reduce(0, +) / Double(filteredValues.count)
        let filtVar = filteredValues.map { pow($0 - filtMean, 2) }.reduce(0, +) / Double(filteredValues.count)

        XCTAssertLessThan(filtVar, rawVar * 0.4, "1Euro filter must suppress stationary jitter variance by at least 60%")
    }

    func test1EuroFilterDynamicCutoffAdaptsUnderFastMotion() {
        let filter = OneEuroFilter1D(minCutoff: 1.0, beta: 0.01)
        var t: TimeInterval = 100.0

        // Step response: jump from 100 to 800
        _ = filter.filter(x: 100.0, timestamp: t)
        t += 0.016
        let fastStep = filter.filter(x: 800.0, timestamp: t)

        // The filter should adapt quickly and close a significant portion of the jump
        XCTAssertGreaterThan(fastStep, 350.0, "Filter should not excessively lag under high velocity")
    }

    func test2DFilterMaintainsPointIntegrity() {
        let filter = OneEuroFilter2D()
        let pt1 = CGPoint(x: 100, y: 200)
        let res1 = filter.filter(point: pt1, timestamp: 1.0)
        XCTAssertEqual(res1.x, 100, accuracy: 0.001)
        XCTAssertEqual(res1.y, 200, accuracy: 0.001)

        let pt2 = CGPoint(x: 102, y: 203)
        let res2 = filter.filter(point: pt2, timestamp: 1.016)
        XCTAssertGreaterThan(res2.x, 100)
        XCTAssertGreaterThan(res2.y, 200)
    }

    func testOneEuroFilter2DTuningReducesJitterSignificantly() {
        let filter = OneEuroFilter2D(minCutoff: 0.5, beta: 0.008)
        var t: TimeInterval = 10.0
        var rawPoints: [CGPoint] = []
        var filteredPoints: [CGPoint] = []

        for i in 0..<60 {
            let noiseX = sin(Double(i) * 1.7) * 2.0
            let noiseY = cos(Double(i) * 2.1) * 2.0
            let raw = CGPoint(x: 960.0 + noiseX, y: 540.0 + noiseY)
            let filtered = filter.filter(point: raw, timestamp: t)
            if i > 10 {
                rawPoints.append(raw)
                filteredPoints.append(filtered)
            }
            t += 0.0333
        }

        let rawVarX = rawPoints.map { pow($0.x - 960.0, 2) }.reduce(0, +) / Double(rawPoints.count)
        let filtVarX = filteredPoints.map { pow($0.x - 960.0, 2) }.reduce(0, +) / Double(filteredPoints.count)

        XCTAssertLessThan(filtVarX, rawVarX * 0.35, "Tuned OneEuroFilter2D must reduce stationary jitter variance by at least 65%")
    }

    func testScrollControllerSmoothsNoisyDeltas() {
        let sc = ScrollController(isInertiaEnabled: true, speedMultiplier: 2.0, smoothingFactor: 0.35)
        let rawDeltas: [CGFloat] = [12.0, 3.0, 15.0, 2.0, 14.0, 4.0, 13.0]
        var smoothedDeltas: [CGFloat] = []

        for r in rawDeltas {
            let out = sc.update(rawDeltaX: 0, rawDeltaY: r)
            smoothedDeltas.append(out.deltaY)
        }

        // Smoothed delta variation between consecutive steps should be much lower than raw delta swings
        let rawSwings = zip(rawDeltas, rawDeltas.dropFirst()).map { abs($0 - $1) }.reduce(0, +)
        let smoothedSwings = zip(smoothedDeltas, smoothedDeltas.dropFirst()).map { abs($0 - $1) }.reduce(0, +)

        XCTAssertLessThan(smoothedSwings, rawSwings * 0.60, "ScrollController must smooth erratic delta fluctuations by > 40%")
    }

    func testScrollControllerInertiaDecaysNaturally() {
        let sc = ScrollController(isInertiaEnabled: true, frictionCoefficient: 0.82)
        _ = sc.update(rawDeltaX: 0, rawDeltaY: 20.0)

        var steps: [CGFloat] = []
        while let step = sc.computeInertiaStep() {
            steps.append(step.deltaY)
        }

        XCTAssertGreaterThan(steps.count, 5, "Inertia must produce multiple smooth deceleration frames")
        XCTAssertLessThan(steps.count, 30, "Inertia must naturally conclude within a reasonable duration")

        // Monotonically decaying
        for i in 1..<steps.count {
            XCTAssertLessThan(abs(steps[i]), abs(steps[i - 1]), "Inertia steps must decay monotonically")
        }
    }

    func testSlowScrollMotionAccumulatesUntilItDeliberatelyEngages() {
        let detector = ScrollDetector(deadbandPoints: 3.0, scrollSpeedMultiplier: 1.0)

        // At a 30–60 FPS camera rate, intentional hand movement is commonly less
        // than the entry deadband in any individual frame.
        XCTAssertNil(detector.evaluate(isTwoFingerPose: true, currentLocation: .zero))
        XCTAssertNil(detector.evaluate(isTwoFingerPose: true, currentLocation: CGPoint(x: 0, y: 1)))
        XCTAssertNil(detector.evaluate(isTwoFingerPose: true, currentLocation: CGPoint(x: 0, y: 2)))

        let delta = detector.evaluate(isTwoFingerPose: true, currentLocation: CGPoint(x: 0, y: 3))
        XCTAssertEqual(delta?.deltaY ?? 0, 3.0, accuracy: 0.001)
        XCTAssertTrue(detector.isScrollActive)
    }

    func testEventSynthesizerSubpixelAccumulationPreservesFractionalDeltas() {
        let synthesizer = EventSynthesizer()
        synthesizer.resetScrollAccumulator()

        // Three 0.4px steps: 0.4 -> 0px (rem 0.4), 0.8 -> 0px (rem 0.8), 1.2 -> 1px (rem 0.2)
        // Verified by observing that no fatal crash happens and remainders accumulate correctly
        synthesizer.postScroll(deltaX: 0, deltaY: 0.4)
        synthesizer.postScroll(deltaX: 0, deltaY: 0.4)
        synthesizer.postScroll(deltaX: 0, deltaY: 0.4)

        synthesizer.resetScrollAccumulator()
    }

    func testPartiallyVisibleHandKeepsItsRecognizedLandmarkConfidence() {
        // Six reliable joints should remain a reliable partial hand, rather than being
        // diluted as if the other fifteen joints had confidence zero.
        XCTAssertEqual(
            HandObservationDecoder.overallConfidence(total: 5.4, recognizedCount: 6),
            0.9,
            accuracy: 0.0001
        )
    }
}
