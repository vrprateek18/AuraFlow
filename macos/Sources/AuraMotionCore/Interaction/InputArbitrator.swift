import QuartzCore
import Foundation
import CoreGraphics
import AuraAtomics

public protocol InputArbitratorDelegate: AnyObject, Sendable {
    func arbitratorDidDetectExternalInput(epoch: UInt64)
    func arbitratorDidTimeoutExcessively()
}

public let kAuraMotionEventMagicTag: Int64 = 0x415552414D4F544E // "AURAMOTN"

/// Lock-free C11 CGEventTap listener for physical input arbitration.
/// All tap lifecycle and management operations execute on a dedicated arbitratorQueue.
/// All CFRunLoop operations dispatch to the main queue.
public final class InputArbitrator: @unchecked Sendable {
    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?
    private var arbitrationState = AuraArbitrationState()
    private var isHardwareLockFree = false

    public weak var delegate: InputArbitratorDelegate?

    /// Guards eventTap, runLoopSource, and _isTapActive for cross-queue reads.
    /// Never acquired inside the event-tap callback.
    private var tapLock = os_unfair_lock_s()
    private var _isTapActive = false

    public var isTapActive: Bool {
        os_unfair_lock_lock(&tapLock)
        defer { os_unfair_lock_unlock(&tapLock) }
        return _isTapActive
    }

    private var timeoutCount: Int = 0
    private var lastTimeoutResetTime: TimeInterval = 0
    private let safetyQueue = DispatchQueue(label: "com.auramotion.safety", qos: .userInteractive)
    private let arbitratorQueue = DispatchQueue(label: "com.auramotion.arbitrator.lifecycle", qos: .userInitiated)

    public init() {
        aura_atomic_init(&arbitrationState, true, 1)
        isHardwareLockFree = aura_atomic_is_hardware_lock_free(&arbitrationState)
    }

    deinit {
        // Synchronous teardown in deinit: directly clean up if possible
        os_unfair_lock_lock(&tapLock)
        let tap = eventTap
        let source = runLoopSource
        eventTap = nil
        runLoopSource = nil
        _isTapActive = false
        os_unfair_lock_unlock(&tapLock)

        if let tap = tap {
            CGEvent.tapEnable(tap: tap, enable: false)
        }
        if let source = source {
            // Best-effort removal; may not be on main thread in deinit
            CFRunLoopRemoveSource(CFRunLoopGetMain(), source, .commonModes)
        }
    }

    public func isLockFree() -> Bool {
        return isHardwareLockFree
    }

    public func currentEpoch() -> UInt64 {
        return aura_atomic_get_epoch(&arbitrationState)
    }

    public func isInjectionEnabled() -> Bool {
        return aura_atomic_is_enabled(&arbitrationState)
    }

    /// Strict 4-step re-enable method.
    public func reenableInjection() -> UInt64 {
        return aura_atomic_enable(&arbitrationState)
    }

    /// Starts the event tap. Serialized on arbitratorQueue; RunLoop source added on main queue.
    /// Completion receives true if the tap was successfully installed.
    /// The synchronous return value is always `false`; use the completion for the real result.
    @discardableResult
    public func start(completion: (@Sendable (Bool) -> Void)? = nil) -> Bool {
        guard isHardwareLockFree else {
            completion?(false)
            return false
        }

        arbitratorQueue.async { [weak self] in
            guard let self = self else {
                completion?(false)
                return
            }

            os_unfair_lock_lock(&self.tapLock)
            if self._isTapActive {
                os_unfair_lock_unlock(&self.tapLock)
                completion?(true)
                return
            }
            os_unfair_lock_unlock(&self.tapLock)

            // Pointer movement and scrolling are frequently incidental (for example, a
            // trackpad being nudged while using gestures).  Treating either as a takeover
            // permanently disabled injection for the cooldown, even though no deliberate
            // direct interaction occurred.  A physical button press is an unambiguous
            // handoff and still immediately yields control.
            let eventMask: CGEventMask = (1 << CGEventType.leftMouseDown.rawValue) |
                                         (1 << CGEventType.rightMouseDown.rawValue)

            let selfPtr = Unmanaged.passUnretained(self).toOpaque()

            guard let tap = CGEvent.tapCreate(
                tap: .cghidEventTap,
                place: .headInsertEventTap,
                options: .listenOnly,
                eventsOfInterest: eventMask,
                callback: { (proxy, type, event, refcon) -> Unmanaged<CGEvent>? in
                    guard let refcon = refcon else {
                        return Unmanaged.passUnretained(event)
                    }
                    let arbitrator = Unmanaged<InputArbitrator>.fromOpaque(refcon).takeUnretainedValue()
                    return arbitrator.handleTapEvent(proxy: proxy, type: type, event: event)
                },
                userInfo: selfPtr
            ) else {
                completion?(false)
                return
            }

            guard let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0) else {
                completion?(false)
                return
            }

            // Store tap and source under lock BEFORE dispatching to main.
            // This ensures handleTapDisabledOffload can see them even if the tap fires
            // before the main queue block runs.
            os_unfair_lock_lock(&self.tapLock)
            self.eventTap = tap
            self.runLoopSource = source
            os_unfair_lock_unlock(&self.tapLock)

            // CFRunLoopSource and CFMachPort are thread-safe CoreFoundation objects.
            // Use nonisolated(unsafe) to satisfy Swift 6 strict sendability.
            nonisolated(unsafe) let safeSource = source
            nonisolated(unsafe) let safeTap = tap

            // Install RunLoop source and enable tap on main queue
            DispatchQueue.main.async { [weak self] in
                guard let self = self else {
                    completion?(false)
                    return
                }

                os_unfair_lock_lock(&self.tapLock)
                guard self.eventTap != nil else {
                    // Tap was already stopped before this block executed
                    os_unfair_lock_unlock(&self.tapLock)
                    completion?(false)
                    return
                }
                self._isTapActive = true
                os_unfair_lock_unlock(&self.tapLock)

                CFRunLoopAddSource(CFRunLoopGetMain(), safeSource, .commonModes)
                CGEvent.tapEnable(tap: safeTap, enable: true)
                completion?(true)
            }
        }

        return false
    }

    /// Stops the event tap. Serialized on arbitratorQueue; RunLoop source removed on main queue.
    public func stop(completion: (@Sendable () -> Void)? = nil) {
        arbitratorQueue.async { [weak self] in
            guard let self = self else {
                completion?()
                return
            }

            os_unfair_lock_lock(&self.tapLock)
            let tap = self.eventTap
            let source = self.runLoopSource
            self.eventTap = nil
            self.runLoopSource = nil
            self._isTapActive = false
            os_unfair_lock_unlock(&self.tapLock)

            guard let activeTap = tap else {
                completion?()
                return
            }

            CGEvent.tapEnable(tap: activeTap, enable: false)

            if let activeSource = source {
                DispatchQueue.main.async {
                    CFRunLoopRemoveSource(CFRunLoopGetMain(), activeSource, .commonModes)
                    completion?()
                }
            } else {
                completion?()
            }
        }
    }

    // MARK: - Event Tap Callback (Bounded O(1), Strictly Non-Blocking, Lock-Free)

    private func handleTapEvent(
        proxy: CGEventTapProxy,
        type: CGEventType,
        event: CGEvent
    ) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            // Offload all timeout and re-enable handling to the arbitrator queue
            arbitratorQueue.async { [weak self] in
                self?.handleTapDisabledOffload()
            }
            return Unmanaged.passUnretained(event)
        }

        // 1. Check user data field for AuraMotion magic tag
        let userData = event.getIntegerValueField(.eventSourceUserData)
        if userData == kAuraMotionEventMagicTag {
            // Our own injected event: return immediately
            return Unmanaged.passUnretained(event)
        }

        // 2. External input detected! Lock-free compare-exchange true -> false
        var newEpoch: UInt64 = 0
        if aura_atomic_try_disable(&arbitrationState, &newEpoch) {
            let capturedEpoch = newEpoch
            // First external event: dispatch asynchronously to safety queue
            safetyQueue.async { [weak self] in
                self?.delegate?.arbitratorDidDetectExternalInput(epoch: capturedEpoch)
            }
        }

        return Unmanaged.passUnretained(event)
    }

    private func handleTapDisabledOffload() {
        let now = CACurrentMediaTime()
        if (now - lastTimeoutResetTime) > 10.0 {
            timeoutCount = 0
            lastTimeoutResetTime = now
        }
        timeoutCount += 1

        if timeoutCount > 3 {
            // Repeated timeouts: safely disable arbitration
            stop()
            safetyQueue.async { [weak self] in
                self?.delegate?.arbitratorDidTimeoutExcessively()
            }
        } else {
            os_unfair_lock_lock(&tapLock)
            let tap = eventTap
            os_unfair_lock_unlock(&tapLock)

            if let tap = tap {
                CGEvent.tapEnable(tap: tap, enable: true)
            }
        }
    }
}
