import Foundation
import CoreGraphics

public enum PinchDecision: Sendable, Equatable {
    case none
    case armed(anchor: CGPoint)
    case click(anchor: CGPoint)
    case startDrag(anchor: CGPoint)
    case dragging(current: CGPoint)
    case dragRelease
    case cancelled
}

/// Anchor-locked pinch and dwell detector.
/// Guarantees clean click emission at anchor location and zero micro-drags.
public final class PinchDetector: @unchecked Sendable {
    public var startThreshold: CGFloat
    public var releaseThreshold: CGFloat
    public var dwellThresholdSeconds: TimeInterval
    public var dragDeadbandPoints: CGFloat
    public var clickDeadbandPoints: CGFloat
    public var maxClickDwellSeconds: TimeInterval

    private var isPinching = false
    public var isContactActive: Bool { isPinching }
    private var clickEmitted = false
    private var isDragging = false
    private var pinchStartTime: TimeInterval?
    private var anchorLocation: CGPoint?
    private var candidateAnchor: CGPoint?
    private let prePinchThreshold: CGFloat = 0.42
    private let anchorLockRadius: CGFloat = 35.0

    public init(
        startThreshold: CGFloat = 0.28,
        releaseThreshold: CGFloat = 0.38,
        dwellThresholdSeconds: TimeInterval = 0.20,
        dragDeadbandPoints: CGFloat = 20.0,
        clickDeadbandPoints: CGFloat = 32.0,
        maxClickDwellSeconds: TimeInterval = 0.80
    ) {
        self.startThreshold = startThreshold
        self.releaseThreshold = releaseThreshold
        self.dwellThresholdSeconds = dwellThresholdSeconds
        self.dragDeadbandPoints = dragDeadbandPoints
        self.clickDeadbandPoints = clickDeadbandPoints
        self.maxClickDwellSeconds = maxClickDwellSeconds
    }

    public func reset() {
        isPinching = false
        clickEmitted = false
        isDragging = false
        pinchStartTime = nil
        anchorLocation = nil
        candidateAnchor = nil
    }

    public func updateThresholds(
        startThreshold: CGFloat? = nil,
        releaseThreshold: CGFloat? = nil,
        dragDeadbandPoints: CGFloat? = nil
    ) {
        if let start = startThreshold { self.startThreshold = start }
        if let release = releaseThreshold { self.releaseThreshold = release }
        if let deadband = dragDeadbandPoints { self.dragDeadbandPoints = deadband }
    }

    /// Evaluates pinch state and returns decision.
    public func evaluate(
        normalizedDistance: CGFloat?,
        currentLocation: CGPoint,
        timestamp: TimeInterval
    ) -> PinchDecision {
        guard let dist = normalizedDistance else {
            if isDragging {
                reset()
                return .dragRelease
            }
            reset()
            return .cancelled
        }

        if !isPinching {
            // Track candidate anchor when fingers begin closing towards each other
            if dist <= max(prePinchThreshold, releaseThreshold) {
                if let candidate = candidateAnchor {
                    let dx = currentLocation.x - candidate.x
                    let dy = currentLocation.y - candidate.y
                    let distFromCandidate = sqrt(dx * dx + dy * dy)
                    // If hand moves beyond anchorLockRadius, the user is navigating, not aiming to click
                    if distFromCandidate > anchorLockRadius {
                        candidateAnchor = currentLocation
                    }
                } else {
                    candidateAnchor = currentLocation
                }
            } else {
                candidateAnchor = nil
            }

            // Check for pinch entry
            if dist <= startThreshold {
                clickEmitted = false
                isPinching = true
                isDragging = false
                pinchStartTime = timestamp
                let anchor = candidateAnchor ?? currentLocation
                anchorLocation = anchor
                candidateAnchor = nil
                return .armed(anchor: anchor)
            }
            return .none
        } else {
            // Already pinching
            guard let startTime = pinchStartTime, let anchor = anchorLocation else {
                reset()
                return .cancelled
            }

            let dwell = timestamp - startTime
            let dx = currentLocation.x - anchor.x
            let dy = currentLocation.y - anchor.y
            let displacement = sqrt(dx * dx + dy * dy)

            // Check for pinch release
            if dist >= releaseThreshold {
                isPinching = false
                pinchStartTime = nil
                anchorLocation = nil
                candidateAnchor = nil

                if isDragging {
                    isDragging = false
                    return .dragRelease
                } else if !clickEmitted && displacement <= clickDeadbandPoints && dwell >= 0.045 && dwell <= maxClickDwellSeconds {
                    // Clean Click at anchor location!
                    return .click(anchor: anchor)
                } else {
                    return .cancelled
                }
            }

            // Still pinched: check if drag should start or continue
            if !isDragging && !clickEmitted && dwell >= 0.045 && dwell <= maxClickDwellSeconds && displacement <= dragDeadbandPoints {
                clickEmitted = true
                return .click(anchor: anchor)
            }
            if !isDragging {
                if dwell >= dwellThresholdSeconds {
                    if displacement > dragDeadbandPoints {
                        isDragging = true
                        return .startDrag(anchor: anchor)
                    }
                    return .armed(anchor: anchor)
                } else {
                    // Within early dwell window (< dwellThresholdSeconds):
                    // If moved significantly across screen (> 36 pt), this is fast cursor navigation,
                    // NOT an intentional pinch-to-click. Cancel immediately to prevent accidental drag or selection.
                    if displacement > 36.0 {
                        reset()
                        return .cancelled
                    }
                    return .armed(anchor: anchor)
                }
            } else {
                return .dragging(current: currentLocation)
            }
        }
    }
}
