import Foundation
import CoreGraphics
@testable import AuraMotionCore

public enum RecordedEventType: Equatable, Sendable {
    case move(CGPoint)
    case click(CGPoint)
    case rightClick(CGPoint)
    case doubleClick(CGPoint)
    case mouseDown(CGPoint)
    case mouseDragged(CGPoint)
    case mouseUp(CGPoint)
    case directMouseUp(CGPoint)
    case scroll(deltaX: CGFloat, deltaY: CGFloat)
    case keyEvent(virtualKey: CGKeyCode, keyDown: Bool, flags: UInt64)
}

public final class RecordingEventPoster: EventPosting, @unchecked Sendable {
    private let lock = NSLock()
    public private(set) var postedEvents: [RecordedEventType] = []

    public init() {}
    public func postRightClick(at location: CGPoint) {
        lock.lock(); defer { lock.unlock() }
        postedEvents.append(.rightClick(location))
    }
    public func postDoubleClick(at location: CGPoint) {
        lock.lock(); defer { lock.unlock() }
        postedEvents.append(.doubleClick(location))
    }

    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.removeAll()
    }

    public var allEvents: [RecordedEventType] {
        lock.lock()
        defer { lock.unlock() }
        return postedEvents
    }

    public func postMove(to location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.move(location))
    }

    public func postClick(at location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.click(location))
    }

    public func postMouseDown(at location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.mouseDown(location))
    }

    public func postMouseDragged(to location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.mouseDragged(location))
    }

    public func postMouseUp(at location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.mouseUp(location))
    }

    public func postDirectMouseUp(at location: CGPoint) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.directMouseUp(location))
    }

    public func postScroll(deltaX: CGFloat, deltaY: CGFloat) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.scroll(deltaX: deltaX, deltaY: deltaY))
    }

    public func postKeyEvent(virtualKey: CGKeyCode, keyDown: Bool, flags: CGEventFlags) {
        lock.lock()
        defer { lock.unlock() }
        postedEvents.append(.keyEvent(virtualKey: virtualKey, keyDown: keyDown, flags: flags.rawValue))
    }
}

public final class EpochBox: @unchecked Sendable {
    private let lock = NSLock()
    private var _epoch: UInt64

    public init(_ initial: UInt64 = 1) {
        self._epoch = initial
    }

    public var epoch: UInt64 {
        get {
            lock.lock()
            defer { lock.unlock() }
            return _epoch
        }
        set {
            lock.lock()
            defer { lock.unlock() }
            _epoch = newValue
        }
    }
}
