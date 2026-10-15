import ApplicationServices
import Foundation

public enum WindowSnapper {
    public static func frame(in visibleBounds: CGRect, right: Bool) -> CGRect {
        let half = visibleBounds.width / 2
        return CGRect(x: visibleBounds.minX + (right ? half : 0), y: visibleBounds.minY, width: half, height: visibleBounds.height)
    }

    /// Called on the output queue. Uses the focused window of the captured app.
    /// Returns a human-readable result rather than silently ignoring unsupported apps.
    public static func apply(pid: pid_t, bounds: CGRect, right: Bool) -> String {
        let app = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(app, 0.25)
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(app, kAXFocusedWindowAttribute as CFString, &value) == .success,
              let value, CFGetTypeID(value) == AXUIElementGetTypeID() else { return "No accessible window to resize" }
        let window = unsafeDowncast(value, to: AXUIElement.self)
        var movable: DarwinBoolean = false
        var resizable: DarwinBoolean = false
        guard AXUIElementIsAttributeSettable(window, kAXPositionAttribute as CFString, &movable) == .success,
              AXUIElementIsAttributeSettable(window, kAXSizeAttribute as CFString, &resizable) == .success,
              movable.boolValue, resizable.boolValue else { return "This window does not support resizing" }
        let target = frame(in: bounds, right: right)
        var size = target.size
        var position = target.origin
        guard let sizeValue = AXValueCreate(.cgSize, &size), let positionValue = AXValueCreate(.cgPoint, &position) else {
            return "Could not create window placement"
        }
        // Resize first, then move; some apps constrain movement of a large window.
        let resized = AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, sizeValue)
        let moved = AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, positionValue)
        guard resized == .success, moved == .success else { return "Window placement was not fully applied" }
        return right ? "Right-half placement requested" : "Left-half placement requested"
    }
}
