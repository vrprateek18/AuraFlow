import Foundation
import CoreGraphics

public enum GestureCommand: String, CaseIterable, Sendable {
    case rightClick, doubleClick, missionControl, previousApp, nextApp, minimize, fullScreen, snapLeft, snapRight
    public var title: String {
        switch self {
        case .rightClick: return "Right click"
        case .doubleClick: return "Double click"
        case .missionControl: return "All windows"
        case .previousApp: return "Previous app"
        case .nextApp: return "Next app"
        case .minimize: return "Minimize"
        case .fullScreen: return "Full screen"
        case .snapLeft: return "Left half"
        case .snapRight: return "Right half"
        }
    }
    public var symbol: String {
        switch self {
        case .rightClick: return "cursorarrow.click"
        case .doubleClick: return "cursorarrow.click.2"
        case .missionControl: return "rectangle.3.group"
        case .previousApp: return "arrow.left"
        case .nextApp: return "arrow.right"
        case .minimize: return "minus.rectangle"
        case .fullScreen: return "arrow.up.left.and.arrow.down.right"
        case .snapLeft: return "rectangle.lefthalf.filled"
        case .snapRight: return "rectangle.righthalf.filled"
        }
    }
}

public struct CommandMenuSnapshot: Sendable {
    public let selected: GestureCommand?
    /// Local normalized position, with top-left origin.
    public let pointer: CGPoint
    public let target: CGPoint
    public let awaitingPointer: Bool
}

/// Pure interaction model: no OS events are sent while navigating the menu.
public final class GestureCommandMenu: @unchecked Sendable {
    public var holdDuration: TimeInterval = 0.9
    public private(set) var isOpen = false
    private var holdStart: Double?
    private var palmAnchor: CGPoint?
    private var pointerOrigin: CGPoint?
    private var pointer = CGPoint(x: 0.5, y: 0.5)
    private var target: CGPoint = .zero
    private var selected: GestureCommand?
    private var lockedSelection: GestureCommand?
    private var confirmation = ContactConfirmation(duration: 0.08)
    private var lastTime: Double?
    private var suppressUntilRelease = false
    private var openedAt: Double = 0
    private let pointerFilter = OneEuroFilter2D(minCutoff: 3, beta: 4)

    public init() {}
    public var snapshot: CommandMenuSnapshot? {
        isOpen ? CommandMenuSnapshot(selected: lockedSelection ?? selected, pointer: pointer, target: target, awaitingPointer: pointerOrigin == nil) : nil
    }
    public func cancel() {
        isOpen = false; holdStart = nil; palmAnchor = nil; pointerOrigin = nil
        selected = nil; lockedSelection = nil; confirmation.reset()
        pointerFilter.reset()
    }
    public func resetHold() { holdStart = nil; palmAnchor = nil }

    @discardableResult
    public func observePalm(position: CGPoint?, timestamp: Double, target: CGPoint) -> Bool {
        guard let position else { resetHold(); return false }
        if let previous = lastTime, timestamp - previous > 0.15 { resetHold() }
        lastTime = timestamp
        if let anchor = palmAnchor, hypot(position.x - anchor.x, position.y - anchor.y) > 0.035 { resetHold() }
        if holdStart == nil { holdStart = timestamp; palmAnchor = position }
        guard timestamp - (holdStart ?? timestamp) >= holdDuration else { return false }
        isOpen = true; self.target = target; pointerOrigin = nil
        pointer = CGPoint(x: 0.5, y: 0.5); selected = nil
        openedAt = timestamp; resetHold()
        return true
    }

    /// Returns true while closing pinch is still held, so it cannot become a click.
    public func consumeClosingContact(distance: CGFloat?, releaseThreshold: CGFloat) -> Bool {
        guard suppressUntilRelease else { return false }
        if let distance, distance >= releaseThreshold { suppressUntilRelease = false }
        return true
    }

    public func navigate(index: CGPoint?, isPointing: Bool, pinchDistance: CGFloat?, contactThreshold: CGFloat, releaseThreshold: CGFloat, timestamp: Double) -> GestureCommand? {
        guard isOpen else { return nil }
        if timestamp - openedAt > 12 { cancel(); return nil }
        guard let index, let distance = pinchDistance else { confirmation.reset(); lockedSelection = nil; return nil }
        if pointerOrigin == nil {
            guard isPointing, distance >= releaseThreshold else { return nil }
            pointerOrigin = index
        }
        if distance >= releaseThreshold {
            confirmation.reset(); lockedSelection = nil
            let origin = pointerOrigin ?? index
            // A 24%-of-frame hand sweep covers the entire palette.
            guard isPointing else { return nil }
            let rawPointer = CGPoint(x: min(1, max(0, 0.5 + (index.x - origin.x) / 0.24)),
                              y: min(1, max(0, 0.5 - (index.y - origin.y) / 0.24)))
            pointer = pointerFilter.filter(point: rawPointer, timestamp: timestamp)
            // Keep the selected tile until the pointer clears its edge by 3%.
            if let selected, let cell = GestureCommand.allCases.firstIndex(of: selected) {
                let bounds = CGRect(x: CGFloat(cell % 3) / 3, y: CGFloat(cell / 3) / 3, width: 1.0 / 3, height: 1.0 / 3).insetBy(dx: -0.03, dy: -0.03)
                if bounds.contains(pointer) { return nil }
            }
            selected = Self.command(at: pointer)
        } else if distance <= contactThreshold {
            if lockedSelection == nil { lockedSelection = selected }
            if confirmation.update(matches: lockedSelection != nil, timestamp: timestamp), let command = lockedSelection {
                suppressUntilRelease = true
                cancel()
                return command
            }
        } else {
            confirmation.reset()
        }
        return nil
    }

    public static func command(at point: CGPoint) -> GestureCommand? {
        guard point.x >= 0, point.x <= 1, point.y >= 0, point.y <= 1 else { return nil }
        return GestureCommand.allCases[min(2, Int(point.y * 3)) * 3 + min(2, Int(point.x * 3))]
    }
}
