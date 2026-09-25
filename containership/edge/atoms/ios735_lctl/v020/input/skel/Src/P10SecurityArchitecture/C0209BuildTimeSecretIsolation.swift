// Generated from checklist component 209 — do not hand-edit the contract block; regenerate.
// Security Architecture · security architecture layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0209BuildTimeSecretIsolation: AppComponent {
    public static let contract = ComponentContract(
        id: 209,
        name: "Build-Time Secret Isolation",
        phase: 10,
        phaseName: "Security Architecture",
        layer: "security architecture",
        purpose: "Build-Time Secret Isolation: the security architecture responsibility named by checklist component 209 (Security Architecture).",
        inputs: ["Build-Time Secret Isolation configuration (typed, validated)", "ComponentContext"],
        outputs: ["Build-Time Secret Isolation state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "threat boundaries, cryptography, credential protection, secure state transitions",
        budgets: [QualityBudget(metric: "threat boundaries", unit: "count", limit: 100.0), QualityBudget(metric: "cryptography", unit: "count", limit: 250.0), QualityBudget(metric: "credential protection", unit: "count", limit: 250.0), QualityBudget(metric: "secure state transitions", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-llbuild2", part: "Build system engine", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-ntp", part: "NTP time sync", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-tools-support-async", part: "Async tooling support", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Build-Time Secret Isolation, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Build-Time Secret Isolation secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Build-Time Secret Isolation: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Build-Time Secret Isolation inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Build-Time Secret Isolation fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
