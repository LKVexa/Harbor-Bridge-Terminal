// Generated from checklist component 565 — do not hand-edit the contract block; regenerate.
// CI/CD · CI/CD layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0565BuildArtifactRetention: AppComponent {
    public static let contract = ComponentContract(
        id: 565,
        name: "Build Artifact Retention",
        phase: 33,
        phaseName: "CI/CD",
        layer: "CI/CD",
        purpose: "Build Artifact Retention: the CI/CD responsibility named by checklist component 565 (CI/CD).",
        inputs: ["Build Artifact Retention configuration (typed, validated)", "ComponentContext"],
        outputs: ["Build Artifact Retention state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
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
        FamilyClause(control: 21, statement: "Make Build Artifact Retention reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Build Artifact Retention and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .productDecision),
        FamilyClause(control: 23, statement: "Define immutable provenance for Build Artifact Retention: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .productDecision),
        FamilyClause(control: 24, statement: "Fail Build Artifact Retention closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .productDecision),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Build Artifact Retention to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .productDecision),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
