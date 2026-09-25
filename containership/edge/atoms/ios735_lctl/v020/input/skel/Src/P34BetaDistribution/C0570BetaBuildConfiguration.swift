// Generated from checklist component 570 — do not hand-edit the contract block; regenerate.
// Beta Distribution · beta distribution layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0570BetaBuildConfiguration: AppComponent {
    public static let contract = ComponentContract(
        id: 570,
        name: "Beta Build Configuration",
        phase: 34,
        phaseName: "Beta Distribution",
        layer: "beta distribution",
        purpose: "Beta Build Configuration: the beta distribution responsibility named by checklist component 570 (Beta Distribution).",
        inputs: ["Beta Build Configuration configuration (typed, validated)", "ComponentContext"],
        outputs: ["Beta Build Configuration state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "TestFlight governance, cohorts, diagnostics, feedback, acceptance criteria",
        budgets: [QualityBudget(metric: "TestFlight governance", unit: "count", limit: 100.0), QualityBudget(metric: "cohorts", unit: "count", limit: 250.0), QualityBudget(metric: "diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "feedback", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-tools-support-async", part: "Async tooling support", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Beta Build Configuration reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Beta Build Configuration and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Beta Build Configuration: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Beta Build Configuration closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Beta Build Configuration to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
