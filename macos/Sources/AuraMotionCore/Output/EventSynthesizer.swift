import Foundation
import CoreGraphics
import QuartzCore

/// Protocol abstracting Quartz event injection, allowing comprehensive test verification.
public protocol EventPosting: Sendable {
    func postMove(to location: CGPoint)
    func postClick(at location: CGPoint)
    func postRightClick(at location: CGPoint)
    func postDoubleClick(at location: CGPoint)
    func postMouseDown(at location: CGPoint)
    func postMouseDragged(to location: CGPoint)
    func postMouseUp(at location: CGPoint)
    func postDirectMouseUp(at location: CGPoint)
    func postScroll(deltaX: CGFloat, deltaY: CGFloat)
    func postKeyEvent(virtualKey: CGKeyCode, keyDown: Bool, flags: CGEventFlags)
    func postSwitchSpace(direction: PalmSwipeDirection)
    func postSwipe(direction: PalmSwipeDirection, action: SwipeActionType)
    func postShortcut(_ shortcut: FingerShortcut)
    func resetScrollAccumulator()
}

public extension EventPosting {
    func resetScrollAccumulator() {}

    func postCommand(_ command: GestureCommand, at location: CGPoint) {
        switch command {
        case .rightClick: postRightClick(at: location)
        case .doubleClick: postDoubleClick(at: location)
        case .previousApp: postSwipe(direction: .left, action: .switchApp)
        case .nextApp: postSwipe(direction: .right, action: .switchApp)
        case .missionControl:
            postKeyEvent(virtualKey: 126, keyDown: true, flags: .maskControl)
            postKeyEvent(virtualKey: 126, keyDown: false, flags: [])
        case .minimize:
            postKeyEvent(virtualKey: 46, keyDown: true, flags: .maskCommand)
            postKeyEvent(virtualKey: 46, keyDown: false, flags: [])
        case .fullScreen:
            postKeyEvent(virtualKey: 3, keyDown: true, flags: [.maskCommand, .maskControl])
            postKeyEvent(virtualKey: 3, keyDown: false, flags: [])
        case .snapLeft, .snapRight: break // Window geometry is handled via Accessibility.
        }
    }

    func postShortcut(_ shortcut: FingerShortcut) {
        let key: CGKeyCode = shortcut == .copy ? 8 : 9 // C / V
        let command: CGKeyCode = 55
        postKeyEvent(virtualKey: command, keyDown: true, flags: .maskCommand)
        postKeyEvent(virtualKey: key, keyDown: true, flags: .maskCommand)
        postKeyEvent(virtualKey: key, keyDown: false, flags: .maskCommand)
        postKeyEvent(virtualKey: command, keyDown: false, flags: [])
    }

    func postSwipe(direction: PalmSwipeDirection, action: SwipeActionType) {
        switch action {
        case .switchSpace:
            postSwitchSpace(direction: direction)
        case .switchWindow:
            postSwitchWindow(direction: direction)
        case .switchApp:
            postSwitchApp(direction: direction)
        }
    }

    func postSwitchSpace(direction: PalmSwipeDirection) {
        let arrowKey: CGKeyCode = (direction == .left) ? 123 : 124 // 123 = Left Arrow, 124 = Right Arrow
        let controlKey: CGKeyCode = 59 // Left Control

        postKeyEvent(virtualKey: controlKey, keyDown: true, flags: .maskControl)
        usleep(25_000)
        postKeyEvent(virtualKey: arrowKey, keyDown: true, flags: .maskControl)
        usleep(30_000)
        postKeyEvent(virtualKey: arrowKey, keyDown: false, flags: .maskControl)
        usleep(25_000)
        postKeyEvent(virtualKey: controlKey, keyDown: false, flags: [])
    }

    func postSwitchWindow(direction: PalmSwipeDirection) {
        let cmdKey: CGKeyCode = 55 // Left Command
        let backtickKey: CGKeyCode = 50 // `
        let shiftKey: CGKeyCode = 56 // Left Shift

        if direction == .left {
            postKeyEvent(virtualKey: cmdKey, keyDown: true, flags: [.maskCommand, .maskShift])
            postKeyEvent(virtualKey: shiftKey, keyDown: true, flags: [.maskCommand, .maskShift])
            usleep(25_000)
            postKeyEvent(virtualKey: backtickKey, keyDown: true, flags: [.maskCommand, .maskShift])
            usleep(30_000)
            postKeyEvent(virtualKey: backtickKey, keyDown: false, flags: [.maskCommand, .maskShift])
            usleep(25_000)
            postKeyEvent(virtualKey: shiftKey, keyDown: false, flags: .maskCommand)
            postKeyEvent(virtualKey: cmdKey, keyDown: false, flags: [])
        } else {
            postKeyEvent(virtualKey: cmdKey, keyDown: true, flags: .maskCommand)
            usleep(25_000)
            postKeyEvent(virtualKey: backtickKey, keyDown: true, flags: .maskCommand)
            usleep(30_000)
            postKeyEvent(virtualKey: backtickKey, keyDown: false, flags: .maskCommand)
            usleep(25_000)
            postKeyEvent(virtualKey: cmdKey, keyDown: false, flags: [])
        }
    }

    func postSwitchApp(direction: PalmSwipeDirection) {
        let cmdKey: CGKeyCode = 55 // Left Command
        let tabKey: CGKeyCode = 48 // Tab
        let shiftKey: CGKeyCode = 56 // Left Shift

        if direction == .left {
            postKeyEvent(virtualKey: cmdKey, keyDown: true, flags: [.maskCommand, .maskShift])
            postKeyEvent(virtualKey: shiftKey, keyDown: true, flags: [.maskCommand, .maskShift])
            usleep(25_000)
            postKeyEvent(virtualKey: tabKey, keyDown: true, flags: [.maskCommand, .maskShift])
            usleep(30_000)
            postKeyEvent(virtualKey: tabKey, keyDown: false, flags: [.maskCommand, .maskShift])
            usleep(25_000)
            postKeyEvent(virtualKey: shiftKey, keyDown: false, flags: .maskCommand)
            postKeyEvent(virtualKey: cmdKey, keyDown: false, flags: [])
        } else {
            postKeyEvent(virtualKey: cmdKey, keyDown: true, flags: .maskCommand)
            usleep(25_000)
            postKeyEvent(virtualKey: tabKey, keyDown: true, flags: .maskCommand)
            usleep(30_000)
            postKeyEvent(virtualKey: tabKey, keyDown: false, flags: .maskCommand)
            usleep(25_000)
            postKeyEvent(virtualKey: cmdKey, keyDown: false, flags: [])
        }
    }
}

public final class EventSynthesizer: EventPosting, @unchecked Sendable {
    private var subpixelRemainderX: CGFloat = 0.0
    private var subpixelRemainderY: CGFloat = 0.0

    private var lastClickTime: TimeInterval = 0
    private var lastClickLocation: CGPoint = .zero
    private var clickCount: Int64 = 1

    public init() {}

    public func postRightClick(at location: CGPoint) {
        postButtonClick(at: location, button: .right, count: 1)
    }

    public func postDoubleClick(at location: CGPoint) {
        postButtonClick(at: location, button: .left, count: 1)
        usleep(45_000)
        postButtonClick(at: location, button: .left, count: 2)
        // Do not let the next ordinary click inherit this explicit double click.
        lastClickTime = 0
    }

    private func postButtonClick(at location: CGPoint, button: CGMouseButton, count: Int64) {
        let downType: CGEventType = button == .right ? .rightMouseDown : .leftMouseDown
        let upType: CGEventType = button == .right ? .rightMouseUp : .leftMouseUp
        guard let down = CGEvent(mouseEventSource: nil, mouseType: downType, mouseCursorPosition: location, mouseButton: button),
              let up = CGEvent(mouseEventSource: nil, mouseType: upType, mouseCursorPosition: location, mouseButton: button) else { return }
        for event in [down, up] {
            event.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
            event.setIntegerValueField(.mouseEventClickState, value: count)
        }
        down.post(tap: .cghidEventTap)
        usleep(20_000)
        up.post(tap: .cghidEventTap)
    }

    public func resetScrollAccumulator() {
        subpixelRemainderX = 0.0
        subpixelRemainderY = 0.0
    }

    /// Injects a tagged mouse moved event.
    public func postMove(to location: CGPoint) {
        guard let event = CGEvent(
            mouseEventSource: nil,
            mouseType: .mouseMoved,
            mouseCursorPosition: location,
            mouseButton: .left
        ) else { return }

        event.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        event.post(tap: .cghidEventTap)
    }

    /// Injects an anchor-locked left click (down + dwell + up) with cursor warping and click state.
    public func postClick(at location: CGPoint) {
        let now = CACurrentMediaTime()
        let dx = location.x - lastClickLocation.x
        let dy = location.y - lastClickLocation.y
        let dist = sqrt(dx * dx + dy * dy)
        if (now - lastClickTime) < 0.5 && dist <= 12.0 {
            clickCount = min(clickCount + 1, 3)
        } else {
            clickCount = 1
        }
        lastClickTime = now
        lastClickLocation = location

        CGWarpMouseCursorPosition(location)

        guard let down = CGEvent(
            mouseEventSource: nil,
            mouseType: .leftMouseDown,
            mouseCursorPosition: location,
            mouseButton: .left
        ), let up = CGEvent(
            mouseEventSource: nil,
            mouseType: .leftMouseUp,
            mouseCursorPosition: location,
            mouseButton: .left
        ) else { return }

        down.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        down.setIntegerValueField(.mouseEventClickState, value: clickCount)

        up.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        up.setIntegerValueField(.mouseEventClickState, value: clickCount)

        down.post(tap: .cghidEventTap)
        usleep(35_000)
        up.post(tap: .cghidEventTap)
    }

    /// Injects left mouse down.
    public func postMouseDown(at location: CGPoint) {
        CGWarpMouseCursorPosition(location)
        guard let down = CGEvent(
            mouseEventSource: nil,
            mouseType: .leftMouseDown,
            mouseCursorPosition: location,
            mouseButton: .left
        ) else { return }

        down.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        down.setIntegerValueField(.mouseEventClickState, value: 1)
        down.post(tap: .cghidEventTap)
    }

    /// Injects left mouse dragged.
    public func postMouseDragged(to location: CGPoint) {
        CGWarpMouseCursorPosition(location)
        guard let drag = CGEvent(
            mouseEventSource: nil,
            mouseType: .leftMouseDragged,
            mouseCursorPosition: location,
            mouseButton: .left
        ) else { return }

        drag.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        drag.post(tap: .cghidEventTap)
    }

    /// Injects left mouse up.
    public func postMouseUp(at location: CGPoint) {
        guard let up = CGEvent(
            mouseEventSource: nil,
            mouseType: .leftMouseUp,
            mouseCursorPosition: location,
            mouseButton: .left
        ) else { return }

        up.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        up.setIntegerValueField(.mouseEventClickState, value: 1)
        up.post(tap: .cghidEventTap)
    }

    /// Direct mouse-up for emergency release.
    public func postDirectMouseUp(at location: CGPoint) {
        postMouseUp(at: location)
    }

    /// Injects scroll wheel event with subpixel accumulation.
    public func postScroll(deltaX: CGFloat, deltaY: CGFloat) {
        let totalX = deltaX + subpixelRemainderX
        let totalY = deltaY + subpixelRemainderY

        let intX = Int32(totalX.rounded(.towardZero))
        let intY = Int32(totalY.rounded(.towardZero))

        subpixelRemainderX = totalX - CGFloat(intX)
        subpixelRemainderY = totalY - CGFloat(intY)

        guard intX != 0 || intY != 0 else { return }

        guard let scroll = CGEvent(
            scrollWheelEvent2Source: nil,
            units: .pixel,
            wheelCount: 2,
            wheel1: intY,
            wheel2: intX,
            wheel3: 0
        ) else { return }

        scroll.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        scroll.post(tap: .cghidEventTap)
    }

    /// Injects a tagged keyboard event with hardware-level event source.
    public func postKeyEvent(virtualKey: CGKeyCode, keyDown: Bool, flags: CGEventFlags = []) {
        let src = CGEventSource(stateID: .hidSystemState)
        guard let event = CGEvent(keyboardEventSource: src, virtualKey: virtualKey, keyDown: keyDown) else { return }
        event.flags = flags
        event.setIntegerValueField(.eventSourceUserData, value: kAuraMotionEventMagicTag)
        event.post(tap: .cghidEventTap)
    }

    public func postShortcut(_ shortcut: FingerShortcut) {
        let key: CGKeyCode = shortcut == .copy ? 8 : 9 // C / V
        let command: CGKeyCode = 55
        postKeyEvent(virtualKey: command, keyDown: true, flags: .maskCommand)
        usleep(12_000)
        postKeyEvent(virtualKey: key, keyDown: true, flags: .maskCommand)
        usleep(18_000)
        postKeyEvent(virtualKey: key, keyDown: false, flags: .maskCommand)
        postKeyEvent(virtualKey: command, keyDown: false, flags: [])
    }
}
