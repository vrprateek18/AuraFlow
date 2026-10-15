import Foundation

/// Replays recorded HandSample JSON files at original relative timestamps.
public final class LandmarkReplayer: Sendable {
    public init() {}

    public func loadSession(from url: URL) throws -> RecordedSession {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(RecordedSession.self, from: data)
    }
}
