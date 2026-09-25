// Privacy-safe diagnostics (x.19, x.25) on top of the vendored swift-log and swift-metrics,
// with trace context carried by the vendored swift-service-context.

import Foundation
import Logging
import CoreMetrics
import ServiceContextModule

/// Metadata keys that must never reach a log sink in clear.
public enum SensitiveKeys {
    public static let redacted: Set<String> = [
        "email", "phone", "name", "address", "token", "password", "secret", "authorization",
        "cookie", "location", "latitude", "longitude", "deviceToken", "idfa", "health", "card",
    ]
    public static func isSensitive(_ key: String) -> Bool {
        let k = key.lowercased()
        return redacted.contains { k.contains($0.lowercased()) }
    }
}

public enum ComponentTraceKey: ServiceContextKey {
    public typealias Value = String
    public static var nameOverride: String? { "component-trace-id" }
}

/// Per-component diagnostics: a stable category, a failure domain, redaction on by construction.
public struct Diagnostics: Sendable {
    public let category: String
    private let logger: Logger
    public init(component: ComponentID, name: String) {
        category = "app.component.\(component)"
        var l = Logger(label: category)
        l[metadataKey: "component"] = .string(name)
        logger = l
    }

    public static func redact(_ metadata: [String: String]) -> Logger.Metadata {
        var out: Logger.Metadata = [:]
        for (k, v) in metadata { out[k] = .string(SensitiveKeys.isSensitive(k) ? "<redacted>" : v) }
        return out
    }

    public func event(_ message: String, domain: FailureDomain? = nil, metadata: [String: String] = [:],
                      level: Logger.Level = .info) {
        var md = Diagnostics.redact(metadata)
        if let domain { md["failure.domain"] = .string(domain.rawValue) }
        if let trace = ServiceContext.current?[ComponentTraceKey.self] { md["trace"] = .string(trace) }
        logger.log(level: level, "\(message)", metadata: md)
    }

    public func failure(_ error: ComponentError) {
        event(error.code.rawValue, domain: error.domain,
              metadata: ["disposition": error.disposition.rawValue], level: .error)
    }

    /// Records a measurement against a budget and reports the verdict without claiming approval.
    @discardableResult
    public func record(_ value: Double, against budget: QualityBudget) -> QualityBudget.Verdict {
        Recorder(label: "\(category).\(budget.metric)").record(value)
        let v = budget.evaluate(value)
        if v == .exceedsProposed || v == .exceedsApproved {
            event("budget exceeded", domain: .runtime, metadata: ["metric": budget.metric, "value": String(value)], level: .warning)
        }
        return v
    }
}
