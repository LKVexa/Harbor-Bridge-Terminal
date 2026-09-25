// Generated from checklist component 728 — do not hand-edit the contract block; regenerate.
// Documentation · documentation layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0728ReleaseGuide: AppComponent {
    public static let contract = ComponentContract(
        id: 728,
        name: "Release Guide",
        phase: 43,
        phaseName: "Documentation",
        layer: "documentation",
        purpose: "Release Guide: the documentation responsibility named by checklist component 728 (Documentation).",
        inputs: ["Release Guide configuration (typed, validated)", "ComponentContext"],
        outputs: ["Release Guide state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "authoritative technical records, ownership, change control, diagrams, operational usability",
        budgets: [QualityBudget(metric: "authoritative technical records", unit: "count", limit: 100.0), QualityBudget(metric: "ownership", unit: "count", limit: 250.0), QualityBudget(metric: "change control", unit: "count", limit: 250.0), QualityBudget(metric: "diagrams", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-markdown", part: "Markdown parse/AST", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-markdown-ui", part: "SwiftUI Markdown rendering", license: "MIT", mode: .packageDependency), DonorPart(car: "swift-snippets", part: "DocC snippet tooling", license: "MIT", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Release Guide reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Release Guide and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Release Guide: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Release Guide closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Release Guide to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
