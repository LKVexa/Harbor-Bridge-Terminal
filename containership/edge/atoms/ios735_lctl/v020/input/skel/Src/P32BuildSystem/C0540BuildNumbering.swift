// Generated from checklist component 540 — do not hand-edit the contract block; regenerate.
// Build System · build system layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0540BuildNumbering: AppComponent {
    public static let contract = ComponentContract(
        id: 540,
        name: "Build Numbering",
        phase: 32,
        phaseName: "Build System",
        layer: "build system",
        purpose: "Build Numbering: the build system responsibility named by checklist component 540 (Build System).",
        inputs: ["Build Numbering configuration (typed, validated)", "ComponentContext"],
        outputs: ["Build Numbering state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "configuration determinism, versioning, signing, reproducibility, artifacts",
        budgets: [QualityBudget(metric: "configuration determinism", unit: "count", limit: 100.0), QualityBudget(metric: "versioning", unit: "count", limit: 250.0), QualityBudget(metric: "signing", unit: "count", limit: 250.0), QualityBudget(metric: "reproducibility", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-tools-support-async", part: "Async tooling support", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Build Numbering reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Build Numbering and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Build Numbering: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Build Numbering closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Build Numbering to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
