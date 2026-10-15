import Foundation
import CoreGraphics

/// A user-driven calibration. Only landmark distances are kept in memory.
public struct PersonalCalibration {
    public enum Step: Int, CaseIterable {
        case indexOpen, indexContact, middleOpen, middleContact, ringOpen, ringContact
        public var finger: HandJointName {
            switch self {
            case .indexOpen, .indexContact: return .indexTip
            case .middleOpen, .middleContact: return .middleTip
            case .ringOpen, .ringContact: return .ringTip
            }
        }
        public var instruction: String {
            switch self {
            case .indexOpen: return "Hold your thumb and index fingertip comfortably apart."
            case .indexContact: return "Touch your thumb tip to your index fingertip."
            case .middleOpen: return "Hold your thumb and middle fingertip comfortably apart."
            case .middleContact: return "Touch your thumb tip to your middle fingertip."
            case .ringOpen: return "Hold your thumb and ring fingertip comfortably apart."
            case .ringContact: return "Touch your thumb tip to your ring fingertip."
            }
        }
    }
    public private(set) var step: Step = .indexOpen
    public private(set) var count = 0
    public private(set) var isComplete = false
    public private(set) var message: String?
    private var samples: [CGFloat] = []
    private var observations: [Step: [CGFloat]] = [:]
    private var lastTime: Double?
    public init() {}

    /// Returns true when the current step completes. The UI must explicitly start
    /// the next collection so transitions between hand poses cannot contaminate it.
    public mutating func add(_ sample: HandSample) -> Bool {
        guard !isComplete, sample.overallConfidence >= 0.6,
              let thumb = sample.joint(.thumbTip, minConfidence: 0.6),
              let tip = sample.joint(step.finger, minConfidence: 0.6),
              let scale = sample.scaleReference else { return false }
        let time = sample.hostTimestamp
        if let lastTime, time - lastTime < 0.025 { return false }
        lastTime = time
        let distance = hypot(tip.x - thumb.x, tip.y - thumb.y) / scale
        guard distance.isFinite else { return false }
        samples.append(distance)
        count = samples.count
        guard count >= 30 else { return false }
        let sorted = samples.sorted()
        if sorted[26] - sorted[3] > 0.35 {
            message = "The hand moved too much. Hold steady and try this step again."
            samples = []; count = 0
            return true
        }
        observations[step] = samples
        samples = []; count = 0; message = nil
        if let next = Step(rawValue: step.rawValue + 1) { step = next }
        else { isComplete = true }
        return true
    }

    public func applying(to original: CalibrationProfile) -> CalibrationProfile? {
        guard isComplete else { return nil }
        var result = original
        for (open, closed) in [(Step.indexOpen, Step.indexContact), (.middleOpen, .middleContact), (.ringOpen, .ringContact)] {
            guard let apart = observations[open]?.sorted(), let contact = observations[closed]?.sorted() else { return nil }
            let low = contact[26], high = apart[3]
            // Reject overlapping poses; never save thresholds that cannot distinguish
            // deliberate release from contact.
            guard high - low >= 0.15, low < 0.6 else { return nil }
            let start = max(0.08, min(0.55, low + (high - low) * 0.20))
            let release = max(start + 0.08, min(0.8, low + (high - low) * 0.5))
            switch closed {
            case .indexContact: result.pinchStartThreshold = start; result.pinchReleaseThreshold = release
            case .middleContact: result.copyContactThreshold = start; result.copyReleaseThreshold = release
            case .ringContact: result.pasteContactThreshold = start; result.pasteReleaseThreshold = release
            default: break
            }
        }
        return result
    }
}
