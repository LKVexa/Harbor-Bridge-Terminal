// Generated from checklist component 214 — do not hand-edit the contract block; regenerate.
// Identity and Authentication · identity/authentication layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0214OAuth2XOIDC: AppComponent {
    public static let contract = ComponentContract(
        id: 214,
        name: "OAuth 2.x / OIDC",
        phase: 11,
        phaseName: "Identity and Authentication",
        layer: "identity/authentication",
        purpose: "OAuth 2.x / OIDC: the identity/authentication responsibility named by checklist component 214 (Identity and Authentication).",
        inputs: ["OAuth 2.x / OIDC configuration (typed, validated)", "ComponentContext"],
        outputs: ["OAuth 2.x / OIDC state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "identity proofing, session security, token lifecycle, authorization boundaries",
        budgets: [QualityBudget(metric: "identity proofing", unit: "count", limit: 100.0), QualityBudget(metric: "session security", unit: "count", limit: 250.0), QualityBudget(metric: "token lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "authorization boundaries", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for OAuth 2.x / OIDC, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep OAuth 2.x / OIDC secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for OAuth 2.x / OIDC: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized OAuth 2.x / OIDC inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that OAuth 2.x / OIDC fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
