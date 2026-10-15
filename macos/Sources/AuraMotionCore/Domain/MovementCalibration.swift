import Foundation
import CoreGraphics

/// Explicit, in-memory calibration using landmarks only. Each stage is started
/// by the user; transitions between poses are excluded from the recordings.
public struct MovementCalibration {
    public enum Step: Int {
        case still, slow, fast
        public var instruction: String {
            switch self {
            case .still: return "Point with your index finger and hold comfortably still."
            case .slow: return "Keep pointing and sweep your hand slowly from side to side."
            case .fast: return "Keep pointing and make quicker, comfortable side-to-side sweeps."
            }
        }
    }
    public private(set) var step: Step = .still
    public private(set) var count = 0
    public private(set) var isComplete = false
    public private(set) var message: String?
    private var points: [CGPoint] = []
    private var times: [Double] = []
    private var recordings: [Int: [CGPoint]] = [:]
    private var speeds: [Int: Double] = [:]
    private var trackingID: Int?
    public init() {}

    @discardableResult
    public mutating func add(_ sample: HandSample) -> Bool {
        guard !isComplete else { return false }
        guard sample.overallConfidence >= 0.6,
              let tip = sample.joint(.indexTip, minConfidence: 0.6),
              tip.x.isFinite, tip.y.isFinite, sample.hostTimestamp.isFinite else { return false }
        let pose = PoseClassifier.classify(sample: sample)
        guard pose.isIndexExtended, !pose.isMiddleExtended, !pose.isPinchApproach else {
            points = []; times = []; count = 0
            message = "Keep only the index finger extended, with thumb comfortably apart."
            return false
        }
        if let last = times.last {
            guard sample.hostTimestamp - last >= 0.025 else { return false }
            if sample.hostTimestamp - last > 0.2 || trackingID != sample.trackingID {
                points = []; times = []; count = 0
            }
        }
        trackingID = sample.trackingID
        message = nil
        points.append(tip); times.append(sample.hostTimestamp); count = points.count
        guard count >= 60 else { return false }
        let xs = points.map(\.x).sorted(), ys = points.map(\.y).sorted()
        let span = hypot(xs[53] - xs[6], ys[53] - ys[6])
        var velocities: [Double] = []
        // 200 ms baselines reduce the influence of single-frame landmark noise.
        for i in 6..<points.count {
            velocities.append(hypot(points[i].x - points[i - 6].x, points[i].y - points[i - 6].y) / (times[i] - times[i - 6]))
        }
        velocities.sort()
        let speed = velocities[velocities.count / 2]
        let valid: Bool
        switch step {
        case .still: valid = span <= 0.04
        case .slow: valid = span >= 0.08 && speed >= 0.025
        case .fast: valid = span >= 0.12 && speed > (speeds[Step.slow.rawValue] ?? 0) * 1.25
        }
        guard valid else {
            message = step == .still ? "Too much movement. Try holding still again." : "Use a wider sweep; the quick sweep must be faster than the slow one."
            points = []; times = []; count = 0
            return true
        }
        recordings[step.rawValue] = points; speeds[step.rawValue] = speed
        points = []; times = []; count = 0
        if let next = Step(rawValue: step.rawValue + 1) { step = next }
        else { isComplete = true }
        return true
    }

    public func applying(to original: CalibrationProfile) -> CalibrationProfile? {
        guard isComplete, let still = recordings[0], let slow = speeds[1], let fast = speeds[2] else { return nil }
        let mapper = CoordinateMapper(profile: original)
        let mapped = still.map { mapper.mapToQuartzGlobal(visionPoint: $0) }
        let xs = mapped.map(\.x).sorted(), ys = mapped.map(\.y).sorted()
        let center = CGPoint(x: xs[xs.count / 2], y: ys[ys.count / 2])
        let residuals = mapped.map { hypot($0.x - center.x, $0.y - center.y) }.sorted()
        let noise = residuals[Int(Double(residuals.count - 1) * 0.8)]
        var result = original
        result.cursorRestRadius = min(3, max(0.6, noise * 0.18))
        result.cursorMinCutoff = min(1.2, max(0.6, 1.2 - Double(noise) * 0.025))
        result.cursorMotionBeta = min(0.018, max(0.006, 0.006 + 0.002 * fast / max(slow, 0.025)))
        return result
    }
}
