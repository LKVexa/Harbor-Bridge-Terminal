// Generated from checklist component 664 — do not hand-edit the contract block; regenerate.
// Reliability Engineering · reliability engineering layer · control family: general

import Foundation
import ComponentKit

public struct C0664ApplicationSLOs: AppComponent {
    public static let contract = ComponentContract(
        id: 664,
        name: "Application SLOs",
        phase: 40,
        phaseName: "Reliability Engineering",
        layer: "reliability engineering",
        purpose: "Application SLOs: the reliability engineering responsibility named by checklist component 664 (Reliability Engineering).",
        inputs: ["Application SLOs configuration (typed, validated)", "ComponentContext"],
        outputs: ["Application SLOs state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "SLOs, recovery, integrity, rollback, diagnostics, post-incident learning",
        budgets: [QualityBudget(metric: "SLOs", unit: "count", limit: 100.0), QualityBudget(metric: "recovery", unit: "count", limit: 250.0), QualityBudget(metric: "integrity", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Application SLOs, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Application SLOs.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Application SLOs, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Application SLOs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Application SLOs while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
