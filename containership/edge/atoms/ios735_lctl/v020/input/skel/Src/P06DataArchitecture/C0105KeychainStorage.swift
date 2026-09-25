// Generated from checklist component 105 — do not hand-edit the contract block; regenerate.
// Data Architecture · data architecture layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0105KeychainStorage: AppComponent {
    public static let contract = ComponentContract(
        id: 105,
        name: "Keychain Storage",
        phase: 6,
        phaseName: "Data Architecture",
        layer: "data architecture",
        purpose: "Keychain Storage: the data architecture responsibility named by checklist component 105 (Data Architecture).",
        inputs: ["Keychain Storage configuration (typed, validated)", "ComponentContext"],
        outputs: ["Keychain Storage state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Security", "LocalAuthentication", "AuthenticationServices"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "schema ownership, persistence semantics, migrations, serialization, consistency",
        budgets: [QualityBudget(metric: "schema ownership", unit: "count", limit: 100.0), QualityBudget(metric: "persistence semantics", unit: "count", limit: 250.0), QualityBudget(metric: "migrations", unit: "count", limit: 250.0), QualityBudget(metric: "serialization", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-system", part: "Typed file-system/syscall wrappers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-protobuf", part: "Protocol Buffers runtime", license: "Apache-2.0 (unverified)", mode: .packageDependency), DonorPart(car: "swift-openapi-generator", part: "Build-time OpenAPI client generation plugin", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Keychain Storage, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Keychain Storage secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Keychain Storage: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Keychain Storage inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Keychain Storage fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
