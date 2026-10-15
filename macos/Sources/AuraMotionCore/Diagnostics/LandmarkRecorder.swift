import Foundation

public struct RecordedSession: Codable, Sendable {
    public let sessionID: String
    public let startTime: Date
    public let samples: [HandSample]
}

/// Opt-in local recorder storing anonymized HandSample sequences for regression testing.
public final class LandmarkRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var recordedSamples: [HandSample] = []
    public private(set) var isRecording = false

    public init() {}

    public func start() {
        lock.lock()
        defer { lock.unlock() }
        recordedSamples.removeAll()
        isRecording = true
    }

    public func record(sample: HandSample) {
        lock.lock()
        defer { lock.unlock() }
        guard isRecording else { return }
        recordedSamples.append(sample)
    }

    public func stopAndSave() -> URL? {
        lock.lock()
        defer { lock.unlock() }
        guard isRecording else { return nil }
        isRecording = false

        let session = RecordedSession(
            sessionID: UUID().uuidString,
            startTime: Date(),
            samples: recordedSamples
        )

        guard let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            return nil
        }
        let dir = appSupport.appendingPathComponent("AuraMotion/Recordings", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        let fileURL = dir.appendingPathComponent("session_\(Int(Date().timeIntervalSince1970)).json")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        if let data = try? encoder.encode(session) {
            try? data.write(to: fileURL)
            return fileURL
        }
        return nil
    }
}
