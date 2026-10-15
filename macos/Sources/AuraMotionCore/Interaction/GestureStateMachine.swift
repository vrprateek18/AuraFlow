import QuartzCore
import Foundation
import CoreGraphics

public protocol GestureStateMachineDelegate: AnyObject, Sendable {
    func stateMachine(_ fsm: GestureStateMachine, didTransitionTo state: GestureState)
    func stateMachine(_ fsm: GestureStateMachine, emitMoveTo location: CGPoint, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitClickAt anchor: CGPoint, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitDragStartAt anchor: CGPoint, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitDragMoveTo location: CGPoint, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitDragEndAt location: CGPoint, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitScroll delta: ScrollDelta, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitSwipe direction: PalmSwipeDirection, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitShortcut shortcut: FingerShortcut, epoch: UInt64)
    func stateMachine(_ fsm: GestureStateMachine, emitCommand command: GestureCommand, at target: CGPoint, epoch: UInt64)
    func stateMachineTriggerEmergencyRelease(_ fsm: GestureStateMachine)
}

public extension GestureStateMachineDelegate {
    func stateMachine(_ fsm: GestureStateMachine, emitSwipe direction: PalmSwipeDirection, epoch: UInt64) {}
    func stateMachine(_ fsm: GestureStateMachine, emitShortcut shortcut: FingerShortcut, epoch: UInt64) {}
    func stateMachine(_ fsm: GestureStateMachine, emitCommand command: GestureCommand, at target: CGPoint, epoch: UInt64) {}
}

/// Hierarchical finite-state machine governing pointer, click, drag, scroll, pause, and safety.
///
/// Priority order (highest first):
///   1. Manual Pause
///   2. Confidence Gate
///   3. Open Palm → Palm Swipe / Palm Rest
///   4. Pinch → Click / Drag  (evaluated BEFORE clutch to avoid blocking)
///   5. Two-Finger → Scroll
///   6. Pointer (default)
public final class GestureStateMachine: @unchecked Sendable {
    public weak var delegate: GestureStateMachineDelegate?

    public private(set) var currentState: GestureState = .idle
    public let confidenceGate = ConfidenceGate()
    private let clutch = EngagementClutch(dwellDuration: 0.02, disengageGraceDuration: 0.20)
    public let pinchDetector = PinchDetector()
    public let shortcutDetector = FingerShortcutDetector()
    public let scrollDetector = ScrollDetector()
    public let palmSwipeDetector = PalmSwipeDetector()
    public let commandMenu = GestureCommandMenu()
    private var lastPointerTarget: CGPoint?
    private var scrollPoseConfirmation = ContactConfirmation(duration: 0.04)
    private var scrollPoseConfirmed = false
    private var lastScrollPoseTime: TimeInterval?

    public var isClutchEnabled: Bool = true
    public var clutchDwellDuration: TimeInterval {
        get { clutch.dwellDuration }
        set { clutch.dwellDuration = max(0, newValue) }
    }
    public var isManualPaused: Bool = false
    public var isPalmSwipeEnabled: Bool = true
    public var openPalmGraceDuration: TimeInterval = 0.12

    private var lastOpenPalmTimestamp: TimeInterval = 0

    public init() {}

    public func updateCalibration(_ profile: CalibrationProfile) {
        pinchDetector.updateThresholds(
            startThreshold: profile.pinchStartThreshold,
            releaseThreshold: profile.pinchReleaseThreshold,
            dragDeadbandPoints: profile.dragDeadbandPoints
        )
        scrollDetector.updateDeadband(points: profile.scrollDeadbandPoints)
        shortcutDetector.updateCalibration(profile)
    }

    public func reset() {
        scrollPoseConfirmation.reset()
        scrollPoseConfirmed = false
        lastScrollPoseTime = nil
        currentState = .idle
        commandMenu.cancel()
        confidenceGate.reset()
        clutch.reset()
        pinchDetector.reset()
        shortcutDetector.reset()
        scrollDetector.reset()
        palmSwipeDetector.reset()
        lastOpenPalmTimestamp = 0
    }

    public func transition(to newState: GestureState) {
        if newState != .scrolling && newState != .scrollCandidate {
            scrollPoseConfirmation.reset()
            scrollPoseConfirmed = false
            lastScrollPoseTime = nil
        }
        if newState == .paused || newState == .trackingLost { commandMenu.cancel() }
        guard currentState != newState else { return }
        currentState = newState
        delegate?.stateMachine(self, didTransitionTo: newState)
    }

    /// Evaluates incoming filtered hand sample and updates state & actions.
    public func processFrame(
        sample: HandSample?,
        mappedCursorLocation: CGPoint?,
        currentEpoch: UInt64,
        isInjectionAllowed: Bool
    ) {
        let timestamp = sample?.hostTimestamp ?? CACurrentMediaTime()

        // ── 1. Manual Pause ──
        if isManualPaused {
            commandMenu.cancel()
            if currentState != .paused {
                transition(to: .paused)
                palmSwipeDetector.reset()
                delegate?.stateMachineTriggerEmergencyRelease(self)
            }
            return
        }

        // ── 2. Confidence Gate ──
        let hasValidConfidence = confidenceGate.evaluate(sample: sample, timestamp: timestamp)
        guard hasValidConfidence, let sample = sample, let cursorLoc = mappedCursorLocation else {
            commandMenu.cancel()
            if currentState != .trackingLost {
                transition(to: .trackingLost)
                pinchDetector.reset()
                shortcutDetector.cancelCandidate()
                scrollDetector.reset()
                palmSwipeDetector.reset()
                clutch.reset()
                lastOpenPalmTimestamp = 0
                delegate?.stateMachineTriggerEmergencyRelease(self)
            }
            return
        }

        // ── 3. Classify Pose ──
        guard isInjectionAllowed else {
            commandMenu.cancel()
            if currentState != .paused {
                pinchDetector.reset()
                scrollDetector.reset()
                palmSwipeDetector.reset()
                clutch.reset()
                transition(to: .paused)
                delegate?.stateMachineTriggerEmergencyRelease(self)
            }
            return
        }
        let features = PoseClassifier.classify(sample: sample, pinchReleaseThreshold: pinchDetector.releaseThreshold)

        if commandMenu.consumeClosingContact(distance: features.normalizedPinchDistance, releaseThreshold: pinchDetector.releaseThreshold) { return }
        if let menu = commandMenu.snapshot {
            // A deliberate transition from the open palm into an index-pointing
            // pose keeps the menu open for navigation. If tracking still sees a
            // hand but no actionable finger pose (fist, lowered hand, or a folded
            // wrist), dismiss immediately instead of leaving a stale overlay up
            // for the full timeout.
            if !features.isOpenPalm && !features.isIndexExtended &&
                !features.isTwoFingerPointing && !features.isPinchApproach {
                commandMenu.cancel()
                return
            }
            if let command = commandMenu.navigate(index: sample.joint(.indexTip, minConfidence: 0.5),
                isPointing: features.isIndexExtended && !features.isMiddleExtended,
                pinchDistance: features.normalizedPinchDistance,
                contactThreshold: pinchDetector.startThreshold, releaseThreshold: pinchDetector.releaseThreshold,
                timestamp: timestamp) {
                delegate?.stateMachine(self, emitCommand: command, at: menu.target, epoch: currentEpoch)
            }
            return
        }
        if !features.isOpenPalm { commandMenu.resetHold() }

        // Shortcut contacts are edge-triggered and evaluated before the open-palm
        // path, which could otherwise consume a thumb-to-ring paste gesture.
        if currentState != .pinchArmed && currentState != .dragging {
            let wasHolding = shortcutDetector.isHoldingContact
            let shortcut = shortcutDetector.evaluate(sample: sample)
            if wasHolding || shortcutDetector.isHoldingContact {
                pinchDetector.reset()
                scrollDetector.reset()
                palmSwipeDetector.reset()
                transition(to: .idle)
                if let shortcut {
                    delegate?.stateMachine(self, emitShortcut: shortcut, epoch: currentEpoch)
                }
                return
            }
        }

        // Determine if this is an explicit non-palm pose (pointer, scroll, or pinch approach)
        let isExplicitPointerPose = features.isIndexExtended && !features.isMiddleExtended && !features.isOpenPalm
        let isExplicitNonPalmPose = isExplicitPointerPose || features.isTwoFingerPointing || features.isPinchApproach

        // ── 4. Open Palm with grace period ──
        let isEffectiveOpenPalm: Bool
        if isExplicitNonPalmPose {
            isEffectiveOpenPalm = false
            lastOpenPalmTimestamp = 0
        } else if features.isOpenPalm {
            lastOpenPalmTimestamp = timestamp
            isEffectiveOpenPalm = true
        } else if (currentState == .palmCandidate || currentState == .palmRest || currentState == .palmSwipeLeft || currentState == .palmSwipeRight) &&
                  (timestamp - lastOpenPalmTimestamp) < openPalmGraceDuration &&
                  lastOpenPalmTimestamp > 0 {
            isEffectiveOpenPalm = true
        } else {
            isEffectiveOpenPalm = false
        }

        // ── 5. Palm Swipe / Palm Rest ──
        if isEffectiveOpenPalm {
            let inPinchOrDragOrScroll = (currentState == .pinchArmed || currentState == .dragging || currentState == .scrolling || currentState == .scrollCandidate)
            if !inPinchOrDragOrScroll {
                pinchDetector.reset()
                scrollDetector.reset()

                if isPalmSwipeEnabled, let swipeDirection = palmSwipeDetector.evaluate(
                    sample: sample,
                    isOpenPalm: true,
                    timestamp: timestamp
                ) {
                    let swipeState: GestureState = (swipeDirection == .left) ? .palmSwipeLeft : .palmSwipeRight
                    transition(to: swipeState)
                    clutch.reset()
                    commandMenu.resetHold()
                    delegate?.stateMachine(self, emitSwipe: swipeDirection, epoch: currentEpoch)
                    return
                }

                if isPalmSwipeEnabled && palmSwipeDetector.isCandidateActive {
                    transition(to: .palmCandidate)
                    return
                } else {
                    if commandMenu.observePalm(position: PalmSwipeDetector.extractPalmCenter(from: sample), timestamp: timestamp,
                                               target: lastPointerTarget ?? cursorLoc) {
                        pinchDetector.reset(); scrollDetector.reset(); shortcutDetector.reset()
                        transition(to: .idle)
                        return
                    }
                    if currentState != .palmRest {
                        transition(to: .palmRest)
                        clutch.reset()
                        delegate?.stateMachineTriggerEmergencyRelease(self)
                    }
                    return
                }
            }
        } else {
            palmSwipeDetector.notifyHandLeftOpenPalm(timestamp: timestamp)
            if currentState == .palmCandidate || currentState == .palmRest || currentState == .palmSwipeLeft || currentState == .palmSwipeRight {
                transition(to: .idle)
            }
        }

        // ── 6. Pinch Detection (BEFORE clutch — pinch must never be blocked) ──
        //    When actively pinching or in drag, always evaluate pinch regardless of clutch.
        let isPinchActive = (currentState == .pinchArmed || currentState == .dragging)
        if isPinchActive || features.isPinchApproach {
            let pinchDecision = pinchDetector.evaluate(
                normalizedDistance: features.normalizedPinchDistance,
                currentLocation: cursorLoc,
                timestamp: timestamp
            )

            switch pinchDecision {
            case .armed(let anchor):
                scrollDetector.reset()
                transition(to: .pinchArmed)
                delegate?.stateMachine(self, emitMoveTo: anchor, epoch: currentEpoch)
                return

            case .click(let anchor):
                transition(to: pinchDetector.isContactActive ? .pinchArmed : .pointer)
                delegate?.stateMachine(self, emitClickAt: anchor, epoch: currentEpoch)
                return

            case .startDrag(let anchor):
                scrollDetector.reset()
                transition(to: .dragging)
                delegate?.stateMachine(self, emitDragStartAt: anchor, epoch: currentEpoch)
                return

            case .dragging(let current):
                scrollDetector.reset()
                transition(to: .dragging)
                delegate?.stateMachine(self, emitDragMoveTo: current, epoch: currentEpoch)
                return

            case .dragRelease:
                transition(to: .pointer)
                delegate?.stateMachine(self, emitDragEndAt: cursorLoc, epoch: currentEpoch)
                return

            case .cancelled:
                // Fall through to clutch → scroll → pointer
                break

            case .none:
                if isPinchActive {
                    // Still armed but no decision yet — stay armed
                    return
                }
                // Not actively pinching and pinch detector returned .none → continue to scroll/pointer
                break
            }
        }

        // ── 7. Engagement Clutch (fast 20ms dwell) ──
        if isClutchEnabled {
            let isActiveGesturePose = features.isIndexExtended || features.isTwoFingerPointing
            let engaged = clutch.evaluate(isReadyPose: isActiveGesturePose, timestamp: timestamp)
            if !engaged {
                transition(to: .clutch)
                return
            }
        }

        // ── 8. Two-Finger Scroll ──
        if features.isTwoFingerPointing {
            lastScrollPoseTime = timestamp
            if !scrollPoseConfirmed {
                scrollPoseConfirmed = scrollPoseConfirmation.update(matches: true, timestamp: timestamp)
                guard scrollPoseConfirmed else {
                    scrollDetector.reset()
                    transition(to: .scrollCandidate)
                    return
                }
            }
            if let delta = scrollDetector.evaluate(isTwoFingerPose: true, currentLocation: cursorLoc) {
                transition(to: .scrolling)
                delegate?.stateMachine(self, emitScroll: delta, epoch: currentEpoch)
            } else {
                transition(to: .scrollCandidate)
            }
            return
        }

        // ── 9. Scroll Inertia Decay ──
        if !isExplicitPointerPose && !features.isOpenPalm && !features.isPinchApproach,
           let last = lastScrollPoseTime, timestamp - last < 0.08 {
            // Freeze during brief ambiguity, rather than interpreting it as a
            // new gesture or sending momentum while finger pose is uncertain.
            return
        }
        if !isExplicitPointerPose && !features.isOpenPalm, let inertiaDelta = scrollDetector.computeInertiaStep() {
            transition(to: .scrolling)
            delegate?.stateMachine(self, emitScroll: inertiaDelta, epoch: currentEpoch)
            return
        }
        scrollDetector.reset()

        guard isExplicitPointerPose else {
            transition(to: .idle)
            return
        }

        // ── 10. Default: Pointer ──
        // If pinch detector has no active state, evaluate it passively to track pre-pinch approach
        if !isPinchActive {
            let pinchDecision = pinchDetector.evaluate(
                normalizedDistance: features.normalizedPinchDistance,
                currentLocation: cursorLoc,
                timestamp: timestamp
            )
            switch pinchDecision {
            case .armed(let anchor):
                scrollDetector.reset()
                transition(to: .pinchArmed)
                delegate?.stateMachine(self, emitMoveTo: anchor, epoch: currentEpoch)
                return
            default:
                break
            }
        }

        transition(to: .pointer)
        lastPointerTarget = cursorLoc
        delegate?.stateMachine(self, emitMoveTo: cursorLoc, epoch: currentEpoch)
    }
}
