// Generated from checklist component 187 — do not hand-edit the contract block; regenerate.
// Security Architecture · security architecture layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0187EncryptionAtRest: AppComponent {
    public static let contract = ComponentContract(
        id: 187,
        name: "Encryption-at-Rest",
        phase: 10,
        phaseName: "Security Architecture",
        layer: "security architecture",
        purpose: "Encryption-at-Rest: the security architecture responsibility named by checklist component 187 (Security Architecture).",
        inputs: ["Encryption-at-Rest configuration (typed, validated)", "ComponentContext"],
        outputs: ["Encryption-at-Rest state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CryptoKit", "DeviceCheck"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "threat boundaries, cryptography, credential protection, secure state transitions",
        budgets: [QualityBudget(metric: "threat boundaries", unit: "count", limit: 100.0), QualityBudget(metric: "cryptography", unit: "count", limit: 250.0), QualityBudget(metric: "credential protection", unit: "count", limit: 250.0), QualityBudget(metric: "secure state transitions", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-homomorphic-encryption", part: "Homomorphic encryption / private information retrieval", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Encryption-at-Rest, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Encryption-at-Rest secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Encryption-at-Rest: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Encryption-at-Rest inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Encryption-at-Rest fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
