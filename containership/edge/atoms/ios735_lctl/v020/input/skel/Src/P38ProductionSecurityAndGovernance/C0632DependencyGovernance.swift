// Generated from checklist component 632 — do not hand-edit the contract block; regenerate.
// Production Security and Governance · security/governance layer · control family: general

import Foundation
import ComponentKit

public struct C0632DependencyGovernance: AppComponent {
    public static let contract = ComponentContract(
        id: 632,
        name: "Dependency Governance",
        phase: 38,
        phaseName: "Production Security and Governance",
        layer: "security/governance",
        purpose: "Dependency Governance: the security/governance responsibility named by checklist component 632 (Production Security and Governance).",
        inputs: ["Dependency Governance configuration (typed, validated)", "ComponentContext"],
        outputs: ["Dependency Governance state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "secure SDLC, supply chain, access control, incident response, compliance evidence",
        budgets: [QualityBudget(metric: "secure SDLC", unit: "count", limit: 100.0), QualityBudget(metric: "supply chain", unit: "count", limit: 250.0), QualityBudget(metric: "access control", unit: "count", limit: 250.0), QualityBudget(metric: "incident response", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-http-types", part: "Currency HTTP request/response types", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Dependency Governance, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Dependency Governance.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Dependency Governance, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Dependency Governance.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Dependency Governance while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
