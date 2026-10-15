import Foundation
import os

/// Thread-safe in-memory permission gate avoiding CoreGraphics and TCC Mach IPC calls on the hot event output path.
/// Caches both fast boolean flags (canInject, canArbitrate) and a complete PermissionsState snapshot
/// for consumers like the HUD that need the full breakdown without triggering live TCC queries.
public final class PermissionGate: @unchecked Sendable {
    private var lock = os_unfair_lock_s()
    private var _canInject: Bool = false
    private var _canArbitrate: Bool = false
    private var _cachedSnapshot: PermissionsState = PermissionsState(
        isCameraAuthorized: false,
        isAccessibilityTrusted: false,
        isPostEventAuthorized: false,
        isListenEventAuthorized: false
    )

    public init() {}

    /// Instantaneous in-memory check for whether input injection is permitted. Zero IPC.
    public var canInject: Bool {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return _canInject
    }

    /// Instantaneous in-memory check for whether event-tap arbitration is permitted. Zero IPC.
    public var canArbitrate: Bool {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return _canArbitrate
    }

    /// Returns the full cached permission snapshot without any live IPC. Zero Mach calls.
    public var cachedSnapshot: PermissionsState {
        os_unfair_lock_lock(&lock)
        defer { os_unfair_lock_unlock(&lock) }
        return _cachedSnapshot
    }

    /// Updates gate state and cached snapshot from OS preflight checks.
    public func update(from state: PermissionsState) {
        os_unfair_lock_lock(&lock)
        _canInject = state.canInjectInput
        _canArbitrate = state.canArbitrate
        _cachedSnapshot = state
        os_unfair_lock_unlock(&lock)
    }

    /// Immediately revokes permissions upon detected permission loss or interruption.
    public func invalidate() {
        os_unfair_lock_lock(&lock)
        _canInject = false
        _canArbitrate = false
        _cachedSnapshot = PermissionsState(
            isCameraAuthorized: _cachedSnapshot.isCameraAuthorized,
            isAccessibilityTrusted: false,
            isPostEventAuthorized: false,
            isListenEventAuthorized: false
        )
        os_unfair_lock_unlock(&lock)
    }
}
