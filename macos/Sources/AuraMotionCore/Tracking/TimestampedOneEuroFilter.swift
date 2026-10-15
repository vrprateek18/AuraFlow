import Foundation
import CoreGraphics

/// Low-pass filter with dynamic cutoff frequency based on velocity.
/// Based on Casiez, Roussel, Vogel (CHI 2012): "1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in HCI"
public final class OneEuroFilter1D: @unchecked Sendable {
    public var minCutoff: Double
    public var beta: Double
    public var dCutoff: Double

    private var xPrev: Double?
    private var rawPrev: Double?
    private var dxPrev: Double = 0.0
    private var tPrev: TimeInterval?

    public init(minCutoff: Double = 1.0, beta: Double = 0.007, dCutoff: Double = 1.0) {
        self.minCutoff = minCutoff
        self.beta = beta
        self.dCutoff = dCutoff
    }

    public func reset() {
        xPrev = nil
        rawPrev = nil
        dxPrev = 0.0
        tPrev = nil
    }

    private func alpha(rate: Double, cutoff: Double) -> Double {
        let tau = 1.0 / (2.0 * Double.pi * cutoff)
        let te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)
    }

    public func filter(x: Double, timestamp: TimeInterval) -> Double {
        guard x.isFinite, timestamp.isFinite else { return xPrev ?? 0 }
        guard let prevX = xPrev, let prevT = tPrev else {
            xPrev = x
            rawPrev = x
            tPrev = timestamp
            return x
        }

        guard timestamp > prevT else { return prevX }
        if timestamp - prevT > 0.25 {
            reset()
            return filter(x: x, timestamp: timestamp)
        }
        let dt = max(timestamp - prevT, 1e-4)
        tPrev = timestamp
        let rate = 1.0 / dt

        // Estimate derivative (velocity) with low-pass filtering
        let dx = (x - (rawPrev ?? x)) * rate
        rawPrev = x
        let aD = alpha(rate: rate, cutoff: dCutoff)
        let dxHat = aD * dx + (1.0 - aD) * dxPrev
        dxPrev = dxHat

        // Dynamic cutoff based on speed
        let cutoff = minCutoff + beta * abs(dxHat)
        let a = alpha(rate: rate, cutoff: cutoff)
        let xHat = a * x + (1.0 - a) * prevX
        xPrev = xHat

        return xHat
    }
}

public final class OneEuroFilter2D: @unchecked Sendable {
    private let filterX: OneEuroFilter1D
    private let filterY: OneEuroFilter1D

    public init(minCutoff: Double = 0.5, beta: Double = 0.008, dCutoff: Double = 1.0) {
        self.filterX = OneEuroFilter1D(minCutoff: minCutoff, beta: beta, dCutoff: dCutoff)
        self.filterY = OneEuroFilter1D(minCutoff: minCutoff, beta: beta, dCutoff: dCutoff)
    }

    public var minCutoff: Double {
        get { filterX.minCutoff }
        set {
            filterX.minCutoff = newValue
            filterY.minCutoff = newValue
        }
    }

    public var beta: Double {
        get { filterX.beta }
        set {
            filterX.beta = newValue
            filterY.beta = newValue
        }
    }

    public func reset() {
        filterX.reset()
        filterY.reset()
    }

    public func filter(point: CGPoint, timestamp: TimeInterval) -> CGPoint {
        let fx = filterX.filter(x: Double(point.x), timestamp: timestamp)
        let fy = filterY.filter(x: Double(point.y), timestamp: timestamp)
        return CGPoint(x: fx, y: fy)
    }
}
