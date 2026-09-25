// Generated from checklist component 559 — do not hand-edit the contract block; regenerate.
// CI/CD · CI/CD layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0559SigningAutomation: AppComponent {
    public static let contract = ComponentContract(
        id: 559,
        name: "Signing Automation",
        phase: 33,
        phaseName: "CI/CD",
        layer: "CI/CD",
        purpose: "Signing Automation: the CI/CD responsibility named by checklist component 559 (CI/CD).",
        inputs: ["Signing Automation configuration (typed, validated)", "ComponentContext"],
        outputs: ["Signing Automation state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "pipeline integrity, automated evidence, signing/release automation, rollback, auditability",
        budgets: [QualityBudget(metric: "pipeline integrity", unit: "count", limit: 100.0), QualityBudget(metric: "automated evidence", unit: "count", limit: 250.0), QualityBudget(metric: "signing/release automation", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-argument-parser", part: "CLI argument parsing (build tooling only)", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Signing Automation reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Signing Automation and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Signing Automation: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Signing Automation closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Signing Automation to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
