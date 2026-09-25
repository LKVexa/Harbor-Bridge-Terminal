// Generated from checklist component 576 — do not hand-edit the contract block; regenerate.
// Beta Distribution · beta distribution layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0576PreReleaseAcceptanceGates: AppComponent {
    public static let contract = ComponentContract(
        id: 576,
        name: "Pre-Release Acceptance Gates",
        phase: 34,
        phaseName: "Beta Distribution",
        layer: "beta distribution",
        purpose: "Pre-Release Acceptance Gates: the beta distribution responsibility named by checklist component 576 (Beta Distribution).",
        inputs: ["Pre-Release Acceptance Gates configuration (typed, validated)", "ComponentContext"],
        outputs: ["Pre-Release Acceptance Gates state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "TestFlight governance, cohorts, diagnostics, feedback, acceptance criteria",
        budgets: [QualityBudget(metric: "TestFlight governance", unit: "count", limit: 100.0), QualityBudget(metric: "cohorts", unit: "count", limit: 250.0), QualityBudget(metric: "diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "feedback", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Pre-Release Acceptance Gates reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Pre-Release Acceptance Gates and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Pre-Release Acceptance Gates: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Pre-Release Acceptance Gates closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Pre-Release Acceptance Gates to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
