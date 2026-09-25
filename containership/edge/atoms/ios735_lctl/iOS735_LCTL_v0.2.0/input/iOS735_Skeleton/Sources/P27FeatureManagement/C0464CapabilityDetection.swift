// Generated from checklist component 464 — do not hand-edit the contract block; regenerate.
// Feature Management · feature management layer · control family: general

import Foundation
import ComponentKit

public struct C0464CapabilityDetection: AppComponent {
    public static let contract = ComponentContract(
        id: 464,
        name: "Capability Detection",
        phase: 27,
        phaseName: "Feature Management",
        layer: "feature management",
        purpose: "Capability Detection: the feature management responsibility named by checklist component 464 (Feature Management).",
        inputs: ["Capability Detection configuration (typed, validated)", "ComponentContext"],
        outputs: ["Capability Detection state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "flag lifecycle, remote config, rollout safety, capability gates, kill switches",
        budgets: [QualityBudget(metric: "flag lifecycle", unit: "count", limit: 100.0), QualityBudget(metric: "remote config", unit: "count", limit: 250.0), QualityBudget(metric: "rollout safety", unit: "count", limit: 250.0), QualityBudget(metric: "capability gates", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Capability Detection, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Capability Detection.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Capability Detection, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Capability Detection.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Capability Detection while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
