// Generated from checklist component 513 — do not hand-edit the contract block; regenerate.
// Quality Engineering · quality engineering layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0513SecurityScanning: AppComponent {
    public static let contract = ComponentContract(
        id: 513,
        name: "Security Scanning",
        phase: 30,
        phaseName: "Quality Engineering",
        layer: "quality engineering",
        purpose: "Security Scanning: the quality engineering responsibility named by checklist component 513 (Quality Engineering).",
        inputs: ["Security Scanning configuration (typed, validated)", "ComponentContext"],
        outputs: ["Security Scanning state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "static gates, policy enforcement, dependency hygiene, regression prevention",
        budgets: [QualityBudget(metric: "static gates", unit: "count", limit: 100.0), QualityBudget(metric: "policy enforcement", unit: "count", limit: 250.0), QualityBudget(metric: "dependency hygiene", unit: "count", limit: 250.0), QualityBudget(metric: "regression prevention", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections-benchmark", part: "Collection benchmark harness", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Security Scanning, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Security Scanning secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Security Scanning: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Security Scanning inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Security Scanning fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
