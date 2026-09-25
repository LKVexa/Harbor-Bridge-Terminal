// Generated from checklist component 119 — do not hand-edit the contract block; regenerate.
// Data Architecture · data architecture layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0119DataExportPipeline: AppComponent {
    public static let contract = ComponentContract(
        id: 119,
        name: "Data Export Pipeline",
        phase: 6,
        phaseName: "Data Architecture",
        layer: "data architecture",
        purpose: "Data Export Pipeline: the data architecture responsibility named by checklist component 119 (Data Architecture).",
        inputs: ["Data Export Pipeline configuration (typed, validated)", "ComponentContext"],
        outputs: ["Data Export Pipeline state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "schema ownership, persistence semantics, migrations, serialization, consistency",
        budgets: [QualityBudget(metric: "schema ownership", unit: "count", limit: 100.0), QualityBudget(metric: "persistence semantics", unit: "count", limit: 250.0), QualityBudget(metric: "migrations", unit: "count", limit: 250.0), QualityBudget(metric: "serialization", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-protobuf", part: "Protocol Buffers runtime", license: "Apache-2.0 (unverified)", mode: .packageDependency), DonorPart(car: "swift-openapi-generator", part: "Build-time OpenAPI client generation plugin", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Data Export Pipeline reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Data Export Pipeline and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Data Export Pipeline: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Data Export Pipeline closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Data Export Pipeline to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
