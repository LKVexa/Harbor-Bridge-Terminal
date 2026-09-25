// Lifecycle (x.05), concurrency isolation (x.07), structured errors (x.09),
// input bounds (x.10), least-privilege capabilities (x.12).

import Foundation

public enum LifecycleState: String, Sendable, CaseIterable {
    case uninitialized, initializing, active, suspended, restoring, upgrading, tearingDown, terminated, failed
}

/// Legal lifecycle transitions. Anything not listed is refused.
public enum Lifecycle {
    public static let transitions: [LifecycleState: Set<LifecycleState>] = [
        .uninitialized: [.initializing, .restoring, .upgrading],
        .initializing: [.active, .failed, .tearingDown],
        .restoring: [.active, .failed, .initializing],
        .upgrading: [.initializing, .failed],
        .active: [.suspended, .tearingDown, .failed],
        .suspended: [.active, .tearingDown, .failed],
        .tearingDown: [.terminated, .failed],
        .failed: [.tearingDown, .initializing],
        .terminated: [],
    ]
    public static func isLegal(_ from: LifecycleState, _ to: LifecycleState) -> Bool {
        transitions[from]?.contains(to) ?? false
    }
}

/// What the caller should do with a failure (x.09).
public enum Disposition: String, Sendable, CaseIterable { case retry, fallback, userAction, escalate, terminal }
/// Which layer failed, so diagnostics can distinguish them (x.19).
public enum FailureDomain: String, Sendable, CaseIterable { case configuration, dependency, data, runtime, permission }

public struct ComponentError: Error, Equatable, Sendable, CustomStringConvertible {
    public enum Code: String, Sendable, CaseIterable {
        case invalidTransition, inputTooLarge, inputMalformed, inputEmpty, dependencyUnavailable
        case permissionNotYetJustified, capabilityUndeclared, cancelled, budgetExceeded, notImplemented
    }
    public let component: ComponentID
    public let code: Code
    public let domain: FailureDomain
    public let disposition: Disposition
    public let detail: String
    public init(_ component: ComponentID, _ code: Code, detail: String = "") {
        self.component = component; self.code = code; self.detail = detail
        let c = ComponentError.classify(code)
        self.domain = c.0; self.disposition = c.1
    }
    /// Total mapping: every code has exactly one domain and disposition.
    public static func classify(_ code: Code) -> (FailureDomain, Disposition) {
        switch code {
        case .invalidTransition: return (.runtime, .terminal)
        case .inputTooLarge, .inputMalformed, .inputEmpty: return (.data, .userAction)
        case .dependencyUnavailable: return (.dependency, .retry)
        case .permissionNotYetJustified, .capabilityUndeclared: return (.permission, .escalate)
        case .cancelled: return (.runtime, .fallback)
        case .budgetExceeded: return (.runtime, .escalate)
        case .notImplemented: return (.configuration, .fallback)
        }
    }
    public var description: String { "\(component) \(code.rawValue) [\(domain.rawValue)/\(disposition.rawValue)] \(detail)" }
}

/// Defensive bounds applied to every external input (x.10).
public struct InputBounds: Sendable, Hashable {
    public let maxBytes: Int
    public let allowEmpty: Bool
    public let rejectControlCharacters: Bool
    public init(maxBytes: Int = 1 << 20, allowEmpty: Bool = false, rejectControlCharacters: Bool = true) {
        self.maxBytes = maxBytes; self.allowEmpty = allowEmpty; self.rejectControlCharacters = rejectControlCharacters
    }
    public func validate(_ data: Data, for id: ComponentID) throws {
        if data.isEmpty && !allowEmpty { throw ComponentError(id, .inputEmpty) }
        if data.count > maxBytes { throw ComponentError(id, .inputTooLarge, detail: "\(data.count) > \(maxBytes)") }
    }
    public func validate(_ text: String, for id: ComponentID) throws {
        try validate(Data(text.utf8), for: id)
        if rejectControlCharacters, text.unicodeScalars.contains(where: { $0.properties.generalCategory == .control && $0 != "\n" && $0 != "\t" }) {
            throw ComponentError(id, .inputMalformed, detail: "control character")
        }
    }
}

/// A sensitive capability. Requests are refused until a user-facing justification is recorded (x.12).
public enum Capability: String, Sendable, CaseIterable {
    case camera, microphone, photoLibrary, location, locationAlways, contacts, calendars, reminders
    case bluetooth, localNetwork, motion, health, homeKit, notifications, tracking, speech, nfc, faceID
    case backgroundProcessing, backgroundFetch, remoteNotifications, network
}

public actor PermissionGate {
    public private(set) var justified: [Capability: String] = [:]
    public private(set) var requested: [Capability] = []
    private let declared: Set<Capability>
    private let owner: ComponentID
    public init(owner: ComponentID, declared: [Capability]) { self.owner = owner; self.declared = Set(declared) }
    public func justify(_ c: Capability, reason: String) { justified[c] = reason }
    /// Returns only when the capability is declared *and* justified by an in-context user action.
    public func request(_ c: Capability) throws {
        guard declared.contains(c) else { throw ComponentError(owner, .capabilityUndeclared, detail: c.rawValue) }
        guard justified[c] != nil else { throw ComponentError(owner, .permissionNotYetJustified, detail: c.rawValue) }
        requested.append(c)
    }
}
