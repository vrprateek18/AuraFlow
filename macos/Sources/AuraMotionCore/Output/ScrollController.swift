import Foundation
import CoreGraphics

/// Generates smooth, low-pass filtered scroll events with inertia decay.
public final class ScrollController: @unchecked Sendable {
    public var isInertiaEnabled: Bool = true
    public var frictionCoefficient: CGFloat = 0.82
    public var speedMultiplier: CGFloat = 1.8
    public var smoothingFactor: CGFloat = 0.32

    private var currentVelocityX: CGFloat = 0
    private var currentVelocityY: CGFloat = 0
    private var isFirstStep: Bool = true

    public init(
        isInertiaEnabled: Bool = true,
        frictionCoefficient: CGFloat = 0.82,
        speedMultiplier: CGFloat = 1.8,
        smoothingFactor: CGFloat = 0.32
    ) {
        self.isInertiaEnabled = isInertiaEnabled
        self.frictionCoefficient = frictionCoefficient
        self.speedMultiplier = speedMultiplier
        self.smoothingFactor = smoothingFactor
    }

    public func reset() {
        currentVelocityX = 0
        currentVelocityY = 0
        isFirstStep = true
    }

    /// Ingests raw movement deltas, applies speed multiplier and low-pass smoothing.
    public func update(rawDeltaX: CGFloat, rawDeltaY: CGFloat) -> ScrollDelta {
        let scaledX = rawDeltaX * speedMultiplier
        let scaledY = rawDeltaY * speedMultiplier

        if isFirstStep {
            currentVelocityX = scaledX
            currentVelocityY = scaledY
            isFirstStep = false
        } else {
            currentVelocityX = smoothingFactor * scaledX + (1.0 - smoothingFactor) * currentVelocityX
            currentVelocityY = smoothingFactor * scaledY + (1.0 - smoothingFactor) * currentVelocityY
        }

        return ScrollDelta(deltaX: currentVelocityX, deltaY: currentVelocityY)
    }

    /// Convenience overload for ScrollDelta inputs.
    public func update(delta: ScrollDelta) -> ScrollDelta {
        return update(rawDeltaX: delta.deltaX, rawDeltaY: delta.deltaY)
    }

    /// Computes inertia step if enabled; halts immediately on pose loss or pause.
    public func computeInertiaStep() -> ScrollDelta? {
        guard isInertiaEnabled else { return nil }

        currentVelocityX *= frictionCoefficient
        currentVelocityY *= frictionCoefficient

        if abs(currentVelocityX) < 0.5 && abs(currentVelocityY) < 0.5 {
            reset()
            return nil
        }

        return ScrollDelta(deltaX: currentVelocityX, deltaY: currentVelocityY)
    }
}
