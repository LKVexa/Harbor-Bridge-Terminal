// The checklist gives each component five family-specific controls (x.21...x.25).
// 20 families were measured in the source checklist; each is modelled here.

public enum ControlFamily: Int, Sendable, CaseIterable {
    case general = 0, mlModel, visualStates, trustBoundary, voiceOver, capabilityDetection
    case dataModel, locationAuthorization, reproducibleBuild, wireContract, syncMerge
    case renderBudget, backgroundMode, analyticsMinimization, testOwnership, pushPayload
    case mediaSession, storeKitTruth, localeFormatting, documentationOwnership

    public var title: String {
        switch self {
        case .general: return "Functional contract"
        case .mlModel: return "Model / tensor contract"
        case .visualStates: return "Visual state coverage"
        case .trustBoundary: return "Trust boundary and attacker model"
        case .voiceOver: return "VoiceOver on physical hardware"
        case .capabilityDetection: return "Hardware capability detection"
        case .dataModel: return "Data ownership and schema"
        case .locationAuthorization: return "Location authorization and accuracy"
        case .reproducibleBuild: return "Reproducible build and provenance"
        case .wireContract: return "Wire-level API contract"
        case .syncMerge: return "Sync merge and conflict semantics"
        case .renderBudget: return "Frame, memory and precision budgets"
        case .backgroundMode: return "Background execution mapping"
        case .analyticsMinimization: return "Analytics question set and minimization"
        case .testOwnership: return "Test ownership and CI stage"
        case .pushPayload: return "APNs / local payload schema"
        case .mediaSession: return "Capture/playback session topology"
        case .storeKitTruth: return "Verified StoreKit transaction truth"
        case .localeFormatting: return "Locale-aware formatting"
        case .documentationOwnership: return "Documentation ownership and cadence"
        }
    }
}

/// What it takes to close a control honestly.
public enum EvidenceNeed: String, Sendable, CaseIterable {
    /// The skeleton declares or implements it; still needs a compile + test run to verify.
    case skeletonDeclared
    /// Needs a run on a physical device / Instruments / VoiceOver.
    case deviceRun
    /// Needs an accountable human (security review, DoD sign-off).
    case humanReview
    /// Needs a product decision (data retention, thresholds, what to collect).
    case productDecision
    /// Needs a CI pipeline with signing identity and provenance capture.
    case ciRun
}

public struct FamilyClause: Hashable, Sendable {
    public let control: Int          // 21...25
    public let statement: String
    public let evidence: EvidenceNeed
    public init(control: Int, statement: String, evidence: EvidenceNeed) {
        precondition((21...25).contains(control))
        self.control = control; self.statement = statement; self.evidence = evidence
    }
}

public struct FamilyDeclaration: Hashable, Sendable {
    public let family: ControlFamily
    public let clauses: [FamilyClause]
    public init(family: ControlFamily, clauses: [FamilyClause]) {
        precondition(clauses.map(\.control) == [21, 22, 23, 24, 25], "family declaration must cover x.21...x.25 in order")
        self.family = family; self.clauses = clauses
    }
}
