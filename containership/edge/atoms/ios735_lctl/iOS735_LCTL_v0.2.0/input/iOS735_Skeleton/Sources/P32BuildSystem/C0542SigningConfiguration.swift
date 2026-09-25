// Generated from checklist component 542 — do not hand-edit the contract block; regenerate.
// Build System · build system layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0542SigningConfiguration: AppComponent {
    public static let contract = ComponentContract(
        id: 542,
        name: "Signing Configuration",
        phase: 32,
        phaseName: "Build System",
        layer: "build system",
        purpose: "Signing Configuration: the build system responsibility named by checklist component 542 (Build System).",
        inputs: ["Signing Configuration configuration (typed, validated)", "ComponentContext"],
        outputs: ["Signing Configuration state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "configuration determinism, versioning, signing, reproducibility, artifacts",
        budgets: [QualityBudget(metric: "configuration determinism", unit: "count", limit: 100.0), QualityBudget(metric: "versioning", unit: "count", limit: 250.0), QualityBudget(metric: "signing", unit: "count", limit: 250.0), QualityBudget(metric: "reproducibility", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-configuration", part: "Layered configuration providers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Signing Configuration reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Signing Configuration and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Signing Configuration: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Signing Configuration closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Signing Configuration to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
