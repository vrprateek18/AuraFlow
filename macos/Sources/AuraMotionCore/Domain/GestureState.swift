import Foundation

/// Explicit states of the hierarchical gesture state machine.
public enum GestureState: String, Sendable, Codable, Equatable {
    case idle
    case clutch
    case pointer
    case pinchArmed
    case dragging
    case scrollCandidate
    case scrolling
    case paused
    case trackingLost
    case palmCandidate
    case palmRest
    case palmSwipeLeft
    case palmSwipeRight

    public var displayName: String {
        switch self {
        case .idle: return "IDLE"
        case .clutch: return "READY (HOLD TO ENGAGE)"
        case .pointer: return "TRACKING"
        case .pinchArmed: return "PINCH ARMED"
        case .dragging: return "DRAGGING"
        case .scrollCandidate: return "SCROLL PENDING"
        case .scrolling: return "SCROLLING"
        case .paused: return "PAUSED"
        case .trackingLost: return "TRACKING LOST - INPUT RELEASED"
        case .palmCandidate: return "PALM DETECTED"
        case .palmRest: return "PALM REST"
        case .palmSwipeLeft: return "SWIPE LEFT ◀"
        case .palmSwipeRight: return "SWIPE RIGHT ▶"
        }
    }

    public var isInputActive: Bool {
        switch self {
        case .pointer, .pinchArmed, .dragging, .scrollCandidate, .scrolling:
            return true
        default:
            return false
        }
    }
}
