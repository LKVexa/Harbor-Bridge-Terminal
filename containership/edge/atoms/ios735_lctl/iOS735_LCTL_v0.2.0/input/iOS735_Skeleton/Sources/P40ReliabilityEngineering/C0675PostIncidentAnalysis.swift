// Generated from checklist component 675 — do not hand-edit the contract block; regenerate.
// Reliability Engineering · reliability engineering layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0675PostIncidentAnalysis: AppComponent {
    public static let contract = ComponentContract(
        id: 675,
        name: "Post-Incident Analysis",
        phase: 40,
        phaseName: "Reliability Engineering",
        layer: "reliability engineering",
        purpose: "Post-Incident Analysis: the reliability engineering responsibility named by checklist component 675 (Reliability Engineering).",
        inputs: ["Post-Incident Analysis configuration (typed, validated)", "ComponentContext"],
        outputs: ["Post-Incident Analysis state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "SLOs, recovery, integrity, rollback, diagnostics, post-incident learning",
        budgets: [QualityBudget(metric: "SLOs", unit: "count", limit: 100.0), QualityBudget(metric: "recovery", unit: "count", limit: 250.0), QualityBudget(metric: "integrity", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-distributed-tracing", part: "Tracing API (spans)", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Post-Incident Analysis reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Post-Incident Analysis and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Post-Incident Analysis: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Post-Incident Analysis closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Post-Incident Analysis to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
