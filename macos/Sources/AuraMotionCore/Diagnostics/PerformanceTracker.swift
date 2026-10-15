import Foundation

public struct PerformanceSnapshot: Sendable {
    public let captureFPS: Double
    public let inferenceFPS: Double
    public let mailboxWaitMs: Double
    public let inferenceDurationP50Ms: Double
    public let inferenceDurationP95Ms: Double
    public let pipelineToEventMs: Double
    public let isLatencyEstimated: Bool
    public let droppedFrames: Int
}

/// Rolling performance tracker measuring true latency and percentiles over a 100-frame window.
public final class PerformanceTracker: @unchecked Sendable {
    private let lock = NSLock()
    private var inferenceDurations: [Double] = []
    private var mailboxWaitTimes: [Double] = []
    private var pipelineLatencies: [Double] = []

    private var captureFrameTimes: [TimeInterval] = []
    private var inferenceFrameTimes: [TimeInterval] = []
    private var droppedFramesCount: Int = 0
    private var isLatencyEstimatedState: Bool = false

    private let windowSize: Int = 100

    public init() {}

    public func recordCaptureFrame(timestamp: TimeInterval, droppedFrames: Int) {
        lock.lock()
        defer { lock.unlock() }

        captureFrameTimes.append(timestamp)
        if captureFrameTimes.count > windowSize {
            captureFrameTimes.removeFirst()
        }
        droppedFramesCount = droppedFrames
    }

    public func recordInference(
        duration: TimeInterval,
        mailboxWait: TimeInterval,
        pipelineLatency: TimeInterval,
        isEstimated: Bool,
        timestamp: TimeInterval
    ) {
        lock.lock()
        defer { lock.unlock() }

        isLatencyEstimatedState = isEstimated
        inferenceFrameTimes.append(timestamp)
        if inferenceFrameTimes.count > windowSize {
            inferenceFrameTimes.removeFirst()
        }

        inferenceDurations.append(duration * 1000.0) // ms
        if inferenceDurations.count > windowSize {
            inferenceDurations.removeFirst()
        }

        mailboxWaitTimes.append(mailboxWait * 1000.0) // ms
        if mailboxWaitTimes.count > windowSize {
            mailboxWaitTimes.removeFirst()
        }

        pipelineLatencies.append(pipelineLatency * 1000.0) // ms
        if pipelineLatencies.count > windowSize {
            pipelineLatencies.removeFirst()
        }
    }

    public func snapshot() -> PerformanceSnapshot {
        lock.lock()
        defer { lock.unlock() }

        let capFPS = calculateFPS(times: captureFrameTimes)
        let infFPS = calculateFPS(times: inferenceFrameTimes)

        let sortedInferences = inferenceDurations.sorted()
        let p50 = percentile(sorted: sortedInferences, p: 0.50)
        let p95 = percentile(sorted: sortedInferences, p: 0.95)

        let avgWait = mailboxWaitTimes.isEmpty ? 0.0 : (mailboxWaitTimes.reduce(0, +) / Double(mailboxWaitTimes.count))
        let avgLat = pipelineLatencies.isEmpty ? 0.0 : (pipelineLatencies.reduce(0, +) / Double(pipelineLatencies.count))

        return PerformanceSnapshot(
            captureFPS: capFPS,
            inferenceFPS: infFPS,
            mailboxWaitMs: avgWait,
            inferenceDurationP50Ms: p50,
            inferenceDurationP95Ms: p95,
            pipelineToEventMs: avgLat,
            isLatencyEstimated: isLatencyEstimatedState,
            droppedFrames: droppedFramesCount
        )
    }

    private func calculateFPS(times: [TimeInterval]) -> Double {
        guard times.count >= 2, let first = times.first, let last = times.last else {
            return 0.0
        }
        let duration = last - first
        guard duration > 0 else { return 0.0 }
        return Double(times.count - 1) / duration
    }

    private func percentile(sorted: [Double], p: Double) -> Double {
        guard !sorted.isEmpty else { return 0.0 }
        let index = Int(Double(sorted.count - 1) * p)
        return sorted[index]
    }
}
