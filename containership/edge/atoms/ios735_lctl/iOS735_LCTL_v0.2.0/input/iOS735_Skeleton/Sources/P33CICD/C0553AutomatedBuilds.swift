// Generated from checklist component 553 — do not hand-edit the contract block; regenerate.
// CI/CD · CI/CD layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0553AutomatedBuilds: AppComponent {
    public static let contract = ComponentContract(
        id: 553,
        name: "Automated Builds",
        phase: 33,
        phaseName: "CI/CD",
        layer: "CI/CD",
        purpose: "Automated Builds: the CI/CD responsibility named by checklist component 553 (CI/CD).",
        inputs: ["Automated Builds configuration (typed, validated)", "ComponentContext"],
        outputs: ["Automated Builds state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "pipeline integrity, automated evidence, signing/release automation, rollback, auditability",
        budgets: [QualityBudget(metric: "pipeline integrity", unit: "count", limit: 100.0), QualityBudget(metric: "automated evidence", unit: "count", limit: 250.0), QualityBudget(metric: "signing/release automation", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-tools-support-async", part: "Async tooling support", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Automated Builds reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Automated Builds and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Automated Builds: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Automated Builds closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Automated Builds to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
