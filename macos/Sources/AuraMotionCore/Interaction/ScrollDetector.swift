import Foundation
import CoreGraphics

public struct ScrollDelta: Sendable, Equatable {
    public let deltaX: CGFloat
    public let deltaY: CGFloat
}

/// Two-finger scroll detector with mutual exclusion, smoothing, and inertia.
public final class ScrollDetector: @unchecked Sendable {
    /// Distance required to deliberately enter scrolling. This is accumulated across
    /// frames so slow, intentional scrolling is not mistaken for a stationary hand.
    public var deadbandPoints: CGFloat
    public let scrollController: ScrollController

    private var previousLocation: CGPoint?
    private var pendingDeltaX: CGFloat = 0
    private var pendingDeltaY: CGFloat = 0
    public private(set) var isScrollActive = false

    public init(
        deadbandPoints: CGFloat = 3.0,
        scrollSpeedMultiplier: CGFloat = 1.8,
        scrollController: ScrollController = ScrollController()
    ) {
        self.deadbandPoints = deadbandPoints
        self.scrollController = scrollController
        self.scrollController.speedMultiplier = scrollSpeedMultiplier
    }

    public var scrollSpeedMultiplier: CGFloat {
        get { scrollController.speedMultiplier }
        set { scrollController.speedMultiplier = newValue }
    }

    public func reset() {
        previousLocation = nil
        pendingDeltaX = 0
        pendingDeltaY = 0
        isScrollActive = false
        scrollController.reset()
    }

    public func updateDeadband(points: CGFloat) {
        deadbandPoints = max(0.5, points)
    }

    /// Evaluates two-finger motion and produces smoothed scroll deltas.
    /// Invariant: Must NOT be called when pinchArmed or dragging is active.
    public func evaluate(
        isTwoFingerPose: Bool,
        currentLocation: CGPoint
    ) -> ScrollDelta? {
        guard isTwoFingerPose else {
            return nil
        }

        guard let prev = previousLocation else {
            previousLocation = currentLocation
            return nil
        }

        let rawDx = currentLocation.x - prev.x
        let rawDy = currentLocation.y - prev.y
        previousLocation = currentLocation

        if !isScrollActive {
            // A normal hand motion is often only a point or two per camera frame.
            // Accumulating it preserves the intentional-entry deadband without making
            // scrolling feel unresponsive at ordinary speeds.
            pendingDeltaX += rawDx
            pendingDeltaY += rawDy
            let totalDist = sqrt(pendingDeltaX * pendingDeltaX + pendingDeltaY * pendingDeltaY)
            if totalDist >= deadbandPoints {
                isScrollActive = true
                let initialX = pendingDeltaX
                let initialY = pendingDeltaY
                pendingDeltaX = 0
                pendingDeltaY = 0
                return scrollController.update(rawDeltaX: initialX, rawDeltaY: initialY)
            }
            return nil
        } else {
            // Ignore sub-pixel tracking tremor after scrolling has started. The motion
            // filter receives only meaningful deltas, avoiding scroll-wheel chatter.
            return scrollController.update(rawDeltaX: rawDx, rawDeltaY: rawDy)
        }
    }

    /// Returns next inertia decay step if scrolling was active and momentum is enabled.
    public func computeInertiaStep() -> ScrollDelta? {
        guard isScrollActive else { return nil }
        guard let step = scrollController.computeInertiaStep() else {
            isScrollActive = false
            return nil
        }
        return step
    }
}
