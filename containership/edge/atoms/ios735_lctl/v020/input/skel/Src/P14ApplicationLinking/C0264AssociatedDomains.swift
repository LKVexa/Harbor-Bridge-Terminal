// Generated from checklist component 264 — do not hand-edit the contract block; regenerate.
// Application Linking · application linking layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0264AssociatedDomains: AppComponent {
    public static let contract = ComponentContract(
        id: 264,
        name: "Associated Domains",
        phase: 14,
        phaseName: "Application Linking",
        layer: "application linking",
        purpose: "Associated Domains: the application linking responsibility named by checklist component 264 (Application Linking).",
        inputs: ["Associated Domains configuration (typed, validated)", "ComponentContext"],
        outputs: ["Associated Domains state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "URL trust boundaries, universal links, handoff state, routing validation",
        budgets: [QualityBudget(metric: "URL trust boundaries", unit: "count", limit: 100.0), QualityBudget(metric: "universal links", unit: "count", limit: 250.0), QualityBudget(metric: "handoff state", unit: "count", limit: 250.0), QualityBudget(metric: "routing validation", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-binary-parsing", part: "Safe binary parsing", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-certificates", part: "X.509 certificate parsing/verification", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Associated Domains, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Associated Domains secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Associated Domains: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Associated Domains inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Associated Domains fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
