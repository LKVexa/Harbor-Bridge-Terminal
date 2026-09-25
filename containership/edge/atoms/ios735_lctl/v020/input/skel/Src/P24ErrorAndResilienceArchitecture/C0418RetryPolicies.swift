// Generated from checklist component 418 — do not hand-edit the contract block; regenerate.
// Error and Resilience Architecture · resilience layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0418RetryPolicies: AppComponent {
    public static let contract = ComponentContract(
        id: 418,
        name: "Retry Policies",
        phase: 24,
        phaseName: "Error and Resilience Architecture",
        layer: "resilience",
        purpose: "Retry Policies: the resilience responsibility named by checklist component 418 (Error and Resilience Architecture).",
        inputs: ["Retry Policies configuration (typed, validated)", "ComponentContext"],
        outputs: ["Retry Policies state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "error taxonomy, recovery paths, fallbacks, corruption handling, user-safe degradation",
        budgets: [QualityBudget(metric: "error taxonomy", unit: "count", limit: 100.0), QualityBudget(metric: "recovery paths", unit: "count", limit: 250.0), QualityBudget(metric: "fallbacks", unit: "count", limit: 250.0), QualityBudget(metric: "corruption handling", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: []
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Retry Policies reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Retry Policies and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Retry Policies: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Retry Policies closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Retry Policies to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
