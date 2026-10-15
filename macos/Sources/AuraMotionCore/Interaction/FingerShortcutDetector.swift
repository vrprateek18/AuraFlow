import Foundation
import CoreGraphics

/// One-shot thumb-to-finger shortcuts. A contact is emitted once and must be
/// released before it can be recognised again, preventing repeated copy/paste.
public enum FingerShortcut: Sendable, Equatable {
    case copy
    case paste
}

public final class FingerShortcutDetector: @unchecked Sendable {
    public var contactThreshold: CGFloat = 0.28
    public var releaseThreshold: CGFloat = 0.40
    private var activeShortcut: FingerShortcut?
    private var candidate: FingerShortcut?
    private var contactConfirmation = ContactConfirmation()
    private var releaseConfirmation = ContactConfirmation()
    private var profile: CalibrationProfile?
    public var isHoldingContact: Bool { activeShortcut != nil || candidate != nil }
    public var confirmationDuration: TimeInterval {
        get { contactConfirmation.duration }
        set { contactConfirmation.duration = newValue; releaseConfirmation.duration = newValue }
    }
    public func updateCalibration(_ profile: CalibrationProfile) { self.profile = profile }

    public init() {}

    public func reset() {
        activeShortcut = nil
        cancelCandidate()
        releaseConfirmation.reset()
    }

    public func cancelCandidate() {
        candidate = nil
        contactConfirmation.reset()
        releaseConfirmation.reset()
    }

    public func evaluate(sample: HandSample) -> FingerShortcut? {
        guard let thumb = sample.joint(.thumbTip, minConfidence: 0.35),
              let scale = sample.scaleReference else {
            cancelCandidate()
            return nil
        }

        let middleDistance = normalizedDistance(from: thumb, to: sample.joint(.middleTip, minConfidence: 0.35), scale: scale)
        let ringDistance = normalizedDistance(from: thumb, to: sample.joint(.ringTip, minConfidence: 0.35), scale: scale)

        if let activeShortcut {
            let distance = activeShortcut == .copy ? middleDistance : ringDistance
            let threshold = activeShortcut == .copy ? profile?.copyReleaseThreshold : profile?.pasteReleaseThreshold
            if releaseConfirmation.update(matches: (distance ?? -.infinity) >= (threshold ?? releaseThreshold), timestamp: sample.hostTimestamp) {
                self.activeShortcut = nil
                releaseConfirmation.reset()
            }
            return nil
        }

        // Index pinch is reserved for click/drag.
        if let index = sample.joint(.indexTip, minConfidence: 0.35),
           let indexDistance = normalizedDistance(from: thumb, to: index, scale: scale),
           indexDistance <= (profile?.pinchStartThreshold ?? contactThreshold),
           indexDistance <= min(middleDistance ?? .infinity, ringDistance ?? .infinity) {
            cancelCandidate()
            return nil
        }

        let detected: FingerShortcut?
        if let ringDistance, ringDistance <= (profile?.pasteContactThreshold ?? contactThreshold),
           ringDistance < (middleDistance ?? .infinity) {
            detected = .paste
        } else if let middleDistance, middleDistance <= (profile?.copyContactThreshold ?? contactThreshold) {
            detected = .copy
        } else {
            detected = nil
        }
        if detected != candidate { contactConfirmation.reset(); candidate = detected }
        if contactConfirmation.update(matches: detected != nil, timestamp: sample.hostTimestamp), let detected {
            activeShortcut = detected
            candidate = nil
            contactConfirmation.reset()
            return detected
        }
        return nil
    }

    private func normalizedDistance(from first: CGPoint, to second: CGPoint?, scale: CGFloat) -> CGFloat? {
        guard let second else { return nil }
        let dx = first.x - second.x
        let dy = first.y - second.y
        return sqrt(dx * dx + dy * dy) / max(scale, 0.01)
    }
}
