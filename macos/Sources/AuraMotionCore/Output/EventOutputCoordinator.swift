import Foundation
import CoreGraphics
import os

/// Serialized output coordinator with coalescing buffers, epoch validation on every event,
/// and verified preemptive emergency release.
public final class EventOutputCoordinator: @unchecked Sendable {
    private let outputQueue = DispatchQueue(label: "com.auramotion.output", qos: .userInteractive)
    private let synthesizer: any EventPosting
    public let guardian = MouseButtonGuardian()

    public var epochProvider: (@Sendable () -> UInt64)?
    public var injectionAllowedProvider: (@Sendable () -> Bool)?

    private var lock = os_unfair_lock_s()
    private var pendingMove: (location: CGPoint, epoch: UInt64)?
    private var pendingDrag: (location: CGPoint, epoch: UInt64)?
    private var pendingScroll: (delta: ScrollDelta, epoch: UInt64)?
    private var lastPostedMove: CGPoint?
    private var isDispatchScheduled = false
    private var isEmergencyActive = false

    public init(synthesizer: any EventPosting = EventSynthesizer()) {
        self.synthesizer = synthesizer
    }

    public func enqueueCommand(_ command: GestureCommand, at target: CGPoint, epoch: UInt64) {
        enqueueValidatedAction(epoch: epoch) { [weak self] in
            self?.synthesizer.postCommand(command, at: target)
        }
    }

    public func enqueueValidatedAction(epoch: UInt64, action: @escaping @Sendable () -> Void) {
        outputQueue.async { [weak self] in
            guard let self else { return }
            os_unfair_lock_lock(&self.lock)
            let emergency = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)
            guard !emergency, self.canPost(epoch: epoch), !self.guardian.isLeftMouseDown else { return }
            action()
        }
    }

    /// Validates whether an event with a given epoch is permitted to post.
    public func canPost(epoch: UInt64) -> Bool {
        guard let currentEpoch = epochProvider?() else { return false }
        guard let allowed = injectionAllowedProvider?() else { return false }
        return allowed && (currentEpoch == epoch)
    }

    /// Enqueues or coalesces a pointer move.
    public func enqueueMove(to location: CGPoint, epoch: UInt64) {
        os_unfair_lock_lock(&lock)
        guard !isEmergencyActive else {
            os_unfair_lock_unlock(&lock)
            return
        }
        pendingMove = (location, epoch)
        scheduleDrainIfNeeded()
        os_unfair_lock_unlock(&lock)
    }

    /// Enqueues an anchor-locked click.
    public func enqueueClick(at anchor: CGPoint, epoch: UInt64) {
        outputQueue.async { [weak self] in
            guard let self = self else { return }
            os_unfair_lock_lock(&self.lock)
            let emergency = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)

            guard !emergency, self.canPost(epoch: epoch) else { return }
            self.synthesizer.postClick(at: anchor)
        }
    }

    /// Enqueues drag start (mouse down).
    public func enqueueDragStart(at anchor: CGPoint, epoch: UInt64) {
        outputQueue.async { [weak self] in
            guard let self = self else { return }
            os_unfair_lock_lock(&self.lock)
            let emergency = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)

            guard !emergency, self.canPost(epoch: epoch) else { return }
            self.guardian.markLeftMouseDown(at: anchor)
            self.synthesizer.postMouseDown(at: anchor)
        }
    }

    /// Enqueues or coalesces a drag movement update.
    /// Invariant: Guardian location is NOT updated here; it is updated only upon actual validated emission.
    public func enqueueDragMove(to location: CGPoint, epoch: UInt64) {
        os_unfair_lock_lock(&lock)
        guard !isEmergencyActive else {
            os_unfair_lock_unlock(&lock)
            return
        }
        pendingDrag = (location, epoch)
        scheduleDrainIfNeeded()
        os_unfair_lock_unlock(&lock)
    }

    /// Enqueues drag end (mouse up). Clears pending drag updates immediately.
    public func enqueueDragEnd(at location: CGPoint, epoch: UInt64) {
        os_unfair_lock_lock(&lock)
        pendingDrag = nil
        let emergency = isEmergencyActive
        os_unfair_lock_unlock(&lock)

        guard !emergency else { return }

        outputQueue.async { [weak self] in
            guard let self = self else { return }
            os_unfair_lock_lock(&self.lock)
            let isEmerg = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)

            guard !isEmerg, self.canPost(epoch: epoch) else { return }
            self.guardian.markLeftMouseUp(at: location)
            self.synthesizer.postMouseUp(at: location)
        }
    }

    /// Enqueues or coalesces a scroll update.
    public func enqueueScroll(delta: ScrollDelta, epoch: UInt64) {
        os_unfair_lock_lock(&lock)
        guard !isEmergencyActive else {
            os_unfair_lock_unlock(&lock)
            return
        }
        if let existing = pendingScroll, existing.epoch == epoch {
            pendingScroll = (ScrollDelta(deltaX: existing.delta.deltaX + delta.deltaX,
                                         deltaY: existing.delta.deltaY + delta.deltaY), epoch)
        } else {
            pendingScroll = (delta, epoch)
        }
        scheduleDrainIfNeeded()
        os_unfair_lock_unlock(&lock)
    }

    /// Enqueues a Space or Window switch action following strict epoch and injection permission checks.
    public func enqueueSwipe(direction: PalmSwipeDirection, action: SwipeActionType = .switchSpace, epoch: UInt64) {
        outputQueue.async { [weak self] in
            guard let self = self else { return }
            os_unfair_lock_lock(&self.lock)
            let emergency = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)

            guard !emergency, self.canPost(epoch: epoch) else { return }
            self.synthesizer.postSwipe(direction: direction, action: action)
        }
    }

    /// Enqueues a one-shot keyboard shortcut after the same epoch and permission checks
    /// used for every other synthetic event.
    public func enqueueShortcut(_ shortcut: FingerShortcut, epoch: UInt64) {
        outputQueue.async { [weak self] in
            guard let self = self else { return }
            os_unfair_lock_lock(&self.lock)
            let emergency = self.isEmergencyActive
            os_unfair_lock_unlock(&self.lock)

            guard !emergency, self.canPost(epoch: epoch) else { return }
            self.synthesizer.postShortcut(shortcut)
        }
    }

    /// Truly preemptive emergency release with confirmation callback.
    /// Immediately purges all pending coalesced buffers, flags emergency state to drop any
    /// enqueued FIFO ordinary work, posts mouseUp at the latest drag position, and invokes completion.
    public func emergencyRelease(completion: (@Sendable () -> Void)? = nil) {
        os_unfair_lock_lock(&lock)
        isEmergencyActive = true
        pendingMove = nil
        pendingDrag = nil
        pendingScroll = nil
        os_unfair_lock_unlock(&lock)

        outputQueue.async { [weak self] in
            guard let self = self else {
                completion?()
                return
            }
            // Release mouse buttons at the latest actually-emitted drag location
            self.guardian.releaseAllButtons(synthesizer: self.synthesizer)
            self.synthesizer.resetScrollAccumulator()
            self.lastPostedMove = nil

            os_unfair_lock_lock(&self.lock)
            self.isEmergencyActive = false
            os_unfair_lock_unlock(&self.lock)

            completion?()
        }
    }

    private func scheduleDrainIfNeeded() {
        guard !isDispatchScheduled else { return }
        isDispatchScheduled = true

        outputQueue.async { [weak self] in
            guard let self = self else { return }
            self.drainCoalescedBuffers()
        }
    }

    private func drainCoalescedBuffers() {
        os_unfair_lock_lock(&lock)
        let emergency = isEmergencyActive
        let move = pendingMove
        let drag = pendingDrag
        let scroll = pendingScroll
        pendingMove = nil
        pendingDrag = nil
        pendingScroll = nil
        isDispatchScheduled = false
        os_unfair_lock_unlock(&lock)

        guard !emergency else { return }

        // 1. Coalesced drag moves: MUST validate epoch & permission before posting
        if let d = drag {
            if canPost(epoch: d.epoch) {
                // Invariant: Guardian location updates ONLY after epoch/permission check and right before posting!
                guardian.updateDragLocation(to: d.location)
                synthesizer.postMouseDragged(to: d.location)
            }
        } else if let m = move {
            // 2. Coalesced pointer moves: MUST validate epoch & permission before posting
            if canPost(epoch: m.epoch) {
                // CursorController handles tremor. Preserve fractional movement
                // here so slow aiming does not become whole-point stair steps.
                if shouldPostMove(to: m.location) {
                    synthesizer.postMove(to: m.location)
                    lastPostedMove = m.location
                }
            }
        }

        // 3. Coalesced scroll: MUST validate epoch & permission before posting
        if let s = scroll {
            if canPost(epoch: s.epoch) {
                synthesizer.postScroll(deltaX: s.delta.deltaX, deltaY: s.delta.deltaY)
            }
        }
    }

    private func shouldPostMove(to location: CGPoint) -> Bool {
        guard let previous = lastPostedMove else { return true }
        let dx = location.x - previous.x
        let dy = location.y - previous.y
        return (dx * dx + dy * dy) >= 0.0625
    }
}
