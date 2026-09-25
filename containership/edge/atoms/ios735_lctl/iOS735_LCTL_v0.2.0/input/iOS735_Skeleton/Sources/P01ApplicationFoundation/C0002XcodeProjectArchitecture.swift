// Generated from checklist component 2 — do not hand-edit the contract block; regenerate.
// Application Foundation · application/bootstrap engineering layer · control family: general

import Foundation
import ComponentKit

public struct C0002XcodeProjectArchitecture: AppComponent {
    public static let contract = ComponentContract(
        id: 2,
        name: "Xcode Project Architecture",
        phase: 1,
        phaseName: "Application Foundation",
        layer: "application/bootstrap engineering",
        purpose: "Xcode Project Architecture: the application/bootstrap engineering responsibility named by checklist component 2 (Application Foundation).",
        inputs: ["Xcode Project Architecture configuration (typed, validated)", "ComponentContext"],
        outputs: ["Xcode Project Architecture state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "build graph, target configuration, runtime initialization, deterministic startup",
        budgets: [QualityBudget(metric: "build graph", unit: "count", limit: 100.0), QualityBudget(metric: "target configuration", unit: "count", limit: 250.0), QualityBudget(metric: "runtime initialization", unit: "p95 ms", limit: 250.0), QualityBudget(metric: "deterministic startup", unit: "p95 ms", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-numerics", part: "Real/Complex numerics", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Xcode Project Architecture, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Xcode Project Architecture.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Xcode Project Architecture, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Xcode Project Architecture.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Xcode Project Architecture while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
