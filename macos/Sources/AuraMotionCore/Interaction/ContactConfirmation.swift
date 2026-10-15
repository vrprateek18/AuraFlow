import Foundation

/// Requires consistent observations over time, not just a single noisy frame.
/// Missing observations cancel candidates but never count as an explicit release.
public struct ContactConfirmation: Sendable {
    public var duration: TimeInterval = 0.06
    private var start: TimeInterval?
    private var previous: TimeInterval?
    private var frames = 0

    public init(duration: TimeInterval = 0.06) { self.duration = duration }
    public mutating func reset() { start = nil; previous = nil; frames = 0 }
    public mutating func update(matches: Bool, timestamp: TimeInterval) -> Bool {
        guard matches, timestamp.isFinite else { reset(); return false }
        if let previous, timestamp <= previous { return false }
        if let previous, timestamp - previous > 0.15 { reset() }
        if start == nil { start = timestamp }
        previous = timestamp
        frames += 1
        return duration <= 0 || (frames >= 2 && timestamp - (start ?? timestamp) >= duration)
    }
}
