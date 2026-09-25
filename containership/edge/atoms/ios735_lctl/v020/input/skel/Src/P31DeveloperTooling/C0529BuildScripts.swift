// Generated from checklist component 529 — do not hand-edit the contract block; regenerate.
// Developer Tooling · developer tooling layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0529BuildScripts: AppComponent {
    public static let contract = ComponentContract(
        id: 529,
        name: "Build Scripts",
        phase: 31,
        phaseName: "Developer Tooling",
        layer: "developer tooling",
        purpose: "Build Scripts: the developer tooling responsibility named by checklist component 529 (Developer Tooling).",
        inputs: ["Build Scripts configuration (typed, validated)", "ComponentContext"],
        outputs: ["Build Scripts state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "repeatable local setup, signing/devices, generators, diagnostics, developer velocity",
        budgets: [QualityBudget(metric: "repeatable local setup", unit: "count", limit: 100.0), QualityBudget(metric: "signing/devices", unit: "count", limit: 250.0), QualityBudget(metric: "generators", unit: "count", limit: 250.0), QualityBudget(metric: "diagnostics", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-argument-parser", part: "CLI argument parsing (build tooling only)", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-tools-support-async", part: "Async tooling support", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Build Scripts reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Build Scripts and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Build Scripts: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Build Scripts closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Build Scripts to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
