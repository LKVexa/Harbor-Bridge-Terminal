// Generated from checklist component 597 — do not hand-edit the contract block; regenerate.
// App Store Distribution · App Store distribution layer · control family: reproducibleBuild

import Foundation
import ComponentKit

public struct C0597PhasedRelease: AppComponent {
    public static let contract = ComponentContract(
        id: 597,
        name: "Phased Release",
        phase: 35,
        phaseName: "App Store Distribution",
        layer: "App Store distribution",
        purpose: "Phased Release: the App Store distribution responsibility named by checklist component 597 (App Store Distribution).",
        inputs: ["Phased Release configuration (typed, validated)", "ComponentContext"],
        outputs: ["Phased Release state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "App Store Connect metadata, compliance, signing, review readiness, release control",
        budgets: [QualityBudget(metric: "App Store Connect metadata", unit: "count", limit: 100.0), QualityBudget(metric: "compliance", unit: "count", limit: 250.0), QualityBudget(metric: "signing", unit: "count", limit: 250.0), QualityBudget(metric: "review readiness", unit: "count", limit: 250.0)],
        family: .reproducibleBuild,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections", part: "Deque, OrderedDictionary, Heap, BitSet", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .reproducibleBuild, clauses: [
        FamilyClause(control: 21, statement: "Make Phased Release reproducible from version-controlled configuration with pinned toolchain/dependency inputs wherever feasible.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Apply least-privilege credentials to Phased Release and keep signing keys, API keys, profiles, and tokens out of build logs/artifacts.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Define immutable provenance for Phased Release: commit SHA, dependency resolution, build number, toolchain, signing identity, and generated artifact digest.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Fail Phased Release closed on missing tests, signing mismatches, entitlement drift, privacy-manifest errors, or policy-gate failures.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Retain sufficient evidence from Phased Release to reproduce, promote, reject, or roll back a release without rebuilding unverified code.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
