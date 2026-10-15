import Foundation
import CoreGraphics
import os

/// Thread-safe guardian ensuring zero stuck mouse buttons on all app-controlled lifecycle paths.
/// Tracks both the button state and the latest drag coordinates.
public final class MouseButtonGuardian: @unchecked Sendable {
    private var lock = os_unfair_lock_s()
    private var isLeftMouseDownState = false
    private var lastKnownLocation = CGPoint(x: 500, y: 500)

    public init() {}

    public var isLeftMouseDown: Bool {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return isLeftMouseDownState
    }

    public var currentLocation: CGPoint {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return lastKnownLocation
    }

    public func markLeftMouseDown(at location: CGPoint) {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        isLeftMouseDownState = true
        lastKnownLocation = location
    }

    public func updateDragLocation(to location: CGPoint) {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        lastKnownLocation = location
    }

    public func markLeftMouseUp(at location: CGPoint? = nil) {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        isLeftMouseDownState = false
        if let loc = location {
            lastKnownLocation = loc
        }
    }

    /// Idempotent release of all virtual mouse buttons.
    /// Safe to call repeatedly from any thread.
    /// Releases at the latest updated drag location rather than the initial click anchor.
    @discardableResult
    public func releaseAllButtons(synthesizer: any EventPosting) -> CGPoint? {
        os_unfair_lock_lock(&lock)
        guard isLeftMouseDownState else {
            os_unfair_lock_unlock(&lock)
            return nil
        }
        isLeftMouseDownState = false
        let releaseLocation = lastKnownLocation
        os_unfair_lock_unlock(&lock)

        // Synthesize mouse-up event immediately at the latest drag location
        synthesizer.postDirectMouseUp(at: releaseLocation)
        return releaseLocation
    }
}
