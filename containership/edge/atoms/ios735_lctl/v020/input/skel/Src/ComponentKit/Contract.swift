// ComponentKit — shared machinery for the 735-component iOS skeleton.
// Controls served here: x.01/x.21 (contract), x.02 (availability), x.03 (frameworks),
// x.08 (strong typing), x.13 (quality budgets, PROPOSED until an owner approves).

import Foundation

/// Strongly typed component identifier (checklist component number 1...735).
public struct ComponentID: Hashable, Comparable, Sendable, CustomStringConvertible {
    public let rawValue: Int
    public init(_ rawValue: Int) {
        precondition((1...735).contains(rawValue), "ComponentID out of range: \(rawValue)")
        self.rawValue = rawValue
    }
    public static func < (lhs: ComponentID, rhs: ComponentID) -> Bool { lhs.rawValue < rhs.rawValue }
    public var description: String { String(format: "C%04d", rawValue) }
}

/// Strongly typed phase identifier (checklist phase 1...43).
public struct PhaseID: Hashable, Comparable, Sendable {
    public let rawValue: Int
    public init(_ rawValue: Int) {
        precondition((1...43).contains(rawValue), "PhaseID out of range: \(rawValue)")
        self.rawValue = rawValue
    }
    public static func < (lhs: PhaseID, rhs: PhaseID) -> Bool { lhs.rawValue < rhs.rawValue }
}

/// Accountable owner. The skeleton never invents one: every contract ships `.unassigned`.
public enum Owner: Hashable, Sendable {
    case unassigned
    case team(String)
    public var isAssigned: Bool { if case .unassigned = self { return false } else { return true } }
}

public struct OSVersion: Hashable, Comparable, Sendable {
    public let major: Int
    public let minor: Int
    public init(_ major: Int, _ minor: Int = 0) { self.major = major; self.minor = minor }
    public static func < (a: OSVersion, b: OSVersion) -> Bool { (a.major, a.minor) < (b.major, b.minor) }
}

/// Minimum OS the component supports, hardware it needs, and its fallback when absent (x.02).
public struct PlatformSupport: Hashable, Sendable {
    public let minimumIOS: OSVersion
    public let iPadOS: Bool
    public let requiresHardware: [HardwareCapability]
    public let fallback: String
    public init(minimumIOS: OSVersion = OSVersion(17), iPadOS: Bool = true,
                requiresHardware: [HardwareCapability] = [], fallback: String) {
        self.minimumIOS = minimumIOS; self.iPadOS = iPadOS
        self.requiresHardware = requiresHardware; self.fallback = fallback
    }
}

public enum HardwareCapability: String, Hashable, Sendable, CaseIterable {
    case camera, microphone, gps, bluetoothLE, nfc, lidar, trueDepth, motion, barometer, uwb, haptics, neuralEngine, metalGPU
}

/// One measurable budget. Thresholds are PROPOSED until an owner approves them (x.13).
public struct QualityBudget: Hashable, Sendable {
    public enum Approval: Hashable, Sendable { case proposed, approved(by: String) }
    public let metric: String
    public let unit: String
    public let limit: Double
    public var approval: Approval
    public init(metric: String, unit: String, limit: Double, approval: Approval = .proposed) {
        self.metric = metric; self.unit = unit; self.limit = limit; self.approval = approval
    }
    public enum Verdict: Equatable, Sendable { case withinProposed, exceedsProposed, withinApproved, exceedsApproved }
    public func evaluate(_ measured: Double) -> Verdict {
        let ok = measured <= limit
        switch approval {
        case .proposed: return ok ? .withinProposed : .exceedsProposed
        case .approved: return ok ? .withinApproved : .exceedsApproved
        }
    }
}

/// A part pulled (or referenced) from a GitHub Junkyard car.
public struct DonorPart: Hashable, Sendable {
    public enum Mode: String, Hashable, Sendable { case vendored, packageDependency, patternOnly }
    public let car: String
    public let part: String
    public let license: String
    public let mode: Mode
    public init(car: String, part: String, license: String, mode: Mode) {
        self.car = car; self.part = part; self.license = license; self.mode = mode
    }
}

/// The engineering contract every component publishes (x.01 / x.21).
public struct ComponentContract: Hashable, Sendable {
    public let id: ComponentID
    public let name: String
    public let phase: PhaseID
    public let phaseName: String
    public let layer: String
    public let purpose: String
    public var owner: Owner
    public let inputs: [String]
    public let outputs: [String]
    public let sideEffects: [String]
    public let invariants: [String]
    public let frameworks: [String]
    public let entitlements: [String]
    public let capabilities: [Capability]
    public let platform: PlatformSupport
    public let budgetDomain: String
    public let budgets: [QualityBudget]
    public let family: ControlFamily
    public let userVisible: Bool
    public let donors: [DonorPart]

    public init(id: Int, name: String, phase: Int, phaseName: String, layer: String, purpose: String,
                owner: Owner = .unassigned, inputs: [String], outputs: [String], sideEffects: [String],
                invariants: [String], frameworks: [String], entitlements: [String] = [],
                capabilities: [Capability] = [], platform: PlatformSupport, budgetDomain: String,
                budgets: [QualityBudget], family: ControlFamily, userVisible: Bool, donors: [DonorPart]) {
        self.id = ComponentID(id); self.name = name; self.phase = PhaseID(phase); self.phaseName = phaseName
        self.layer = layer; self.purpose = purpose; self.owner = owner; self.inputs = inputs
        self.outputs = outputs; self.sideEffects = sideEffects; self.invariants = invariants
        self.frameworks = frameworks; self.entitlements = entitlements; self.capabilities = capabilities
        self.platform = platform; self.budgetDomain = budgetDomain; self.budgets = budgets
        self.family = family; self.userVisible = userVisible; self.donors = donors
    }

    /// Structural problems a reviewer must see; empty means the contract is complete *as a skeleton*.
    public func contractGaps() -> [String] {
        var gaps: [String] = []
        if !owner.isAssigned { gaps.append("owner unassigned") }
        if purpose.isEmpty { gaps.append("purpose empty") }
        if inputs.isEmpty { gaps.append("inputs empty") }
        if outputs.isEmpty { gaps.append("outputs empty") }
        if invariants.isEmpty { gaps.append("invariants empty") }
        if budgets.isEmpty { gaps.append("no quality budget") }
        if budgets.contains(where: { $0.approval == .proposed }) { gaps.append("budgets proposed, not approved") }
        return gaps
    }
}
