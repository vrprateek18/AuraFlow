import Foundation
import AVFoundation
import CoreGraphics
import AppKit

public struct PermissionsState: Sendable, Equatable {
    public let isCameraAuthorized: Bool
    public let isAccessibilityTrusted: Bool
    public let isPostEventAuthorized: Bool
    public let isListenEventAuthorized: Bool

    public var canInjectInput: Bool {
        return isAccessibilityTrusted && isPostEventAuthorized
    }

    public var canArbitrate: Bool {
        return isListenEventAuthorized
    }

    /// A short, user-facing explanation for why gesture output is currently
    /// blocked.  Accessibility trust and event posting are separate macOS
    /// gates; reporting both as "Accessibility" made a granted AX permission
    /// look broken when only event posting was still pending.
    public var inputBlockingReason: String? {
        if !isAccessibilityTrusted {
            return "Accessibility control is required"
        }
        if !isPostEventAuthorized {
            return "Input control permission is required"
        }
        return nil
    }

    /// The most important permission status to show in compact UI surfaces.
    public var statusLabel: String? {
        if !isCameraAuthorized {
            return "Camera access is required"
        }
        return inputBlockingReason
    }

    /// Compact label suitable for a telemetry footer.
    public var compactStatusLabel: String? {
        if !isCameraAuthorized { return "NO CAMERA" }
        if !isAccessibilityTrusted { return "NO ACCESSIBILITY" }
        if !isPostEventAuthorized { return "NO INPUT CONTROL" }
        return nil
    }
}

public extension Notification.Name {
    /// Posted on the main queue whenever a TCC permission snapshot changes.
    static let auraMotionPermissionsDidChange = Notification.Name("AuraMotionPermissionsDidChange")
}

public final class PermissionsManager: @unchecked Sendable {
    public let gate = PermissionGate()

    /// Interval between periodic permission refresh cycles (seconds).
    public var refreshInterval: TimeInterval = 5.0

    private let refreshQueue = DispatchQueue(label: "com.auramotion.permissions.refresh", qos: .utility)
    private var refreshTimer: DispatchSourceTimer?
    private var isRefreshActive = false

    public init() {
        _ = checkPermissions()
    }

    deinit {
        stopPeriodicRefresh()
    }

    @discardableResult
    public func checkPermissions() -> PermissionsState {
        let previous = gate.cachedSnapshot

        // 1. Camera access
        let camStatus = AVCaptureDevice.authorizationStatus(for: .video)
        let isCamera = (camStatus == .authorized)

        // 2. Accessibility trust
        let isAX = AXIsProcessTrusted()

        // 3. Post event access
        let isPost = CGPreflightPostEventAccess()

        // 4. Listen event access
        let isListen = CGPreflightListenEventAccess()

        let state = PermissionsState(
            isCameraAuthorized: isCamera,
            isAccessibilityTrusted: isAX,
            isPostEventAuthorized: isPost,
            isListenEventAuthorized: isListen
        )
        gate.update(from: state)

        // Keep UI and lifecycle code responsive after a user grants access in
        // System Settings without forcing the hot event-output path to query
        // TCC.  The post is intentionally main-queue serialized because
        // AppKit observers consume it there.
        if previous != state {
            DispatchQueue.main.async {
                NotificationCenter.default.post(
                    name: .auraMotionPermissionsDidChange,
                    object: state
                )
            }
        }
        return state
    }

    /// Starts a periodic background refresh of the permission gate.
    /// Safe to call multiple times; only one timer will be active.
    public func startPeriodicRefresh() {
        refreshQueue.async { [weak self] in
            guard let self = self, !self.isRefreshActive else { return }
            self.isRefreshActive = true

            let timer = DispatchSource.makeTimerSource(queue: self.refreshQueue)
            timer.schedule(deadline: .now() + self.refreshInterval, repeating: self.refreshInterval)
            timer.setEventHandler { [weak self] in
                self?.checkPermissions()
            }
            self.refreshTimer = timer
            timer.resume()
        }
    }

    /// Stops the periodic background refresh.
    public func stopPeriodicRefresh() {
        refreshQueue.async { [weak self] in
            guard let self = self else { return }
            self.refreshTimer?.cancel()
            self.refreshTimer = nil
            self.isRefreshActive = false
        }
    }

    public func requestCameraAccess(completion: @escaping @Sendable (Bool) -> Void) {
        AVCaptureDevice.requestAccess(for: .video) { granted in
            completion(granted)
        }
    }

    /// Checks Accessibility trust and shows the native macOS prompt if not yet trusted.
    /// This adds the app to the Accessibility list in System Settings automatically.
    @discardableResult
    public func requestAccessibilityIfNeeded() -> Bool {
        // Use raw string to avoid Swift 6 sendability error on the global kAXTrustedCheckOptionPrompt
        let options = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
        return AXIsProcessTrustedWithOptions(options)
    }

    public func requestPostEventAccess() {
        _ = CGRequestPostEventAccess()
    }

    public func requestListenEventAccess() {
        _ = CGRequestListenEventAccess()
    }

    public func openSystemSettingsAccessibility() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
    }

    public func openSystemSettingsCamera() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera") {
            NSWorkspace.shared.open(url)
        }
    }
}
