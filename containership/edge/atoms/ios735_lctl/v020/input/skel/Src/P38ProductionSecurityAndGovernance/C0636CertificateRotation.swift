// Generated from checklist component 636 — do not hand-edit the contract block; regenerate.
// Production Security and Governance · security/governance layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0636CertificateRotation: AppComponent {
    public static let contract = ComponentContract(
        id: 636,
        name: "Certificate Rotation",
        phase: 38,
        phaseName: "Production Security and Governance",
        layer: "security/governance",
        purpose: "Certificate Rotation: the security/governance responsibility named by checklist component 636 (Production Security and Governance).",
        inputs: ["Certificate Rotation configuration (typed, validated)", "ComponentContext"],
        outputs: ["Certificate Rotation state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation.URLSession", "Network"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "secure SDLC, supply chain, access control, incident response, compliance evidence",
        budgets: [QualityBudget(metric: "secure SDLC", unit: "count", limit: 100.0), QualityBudget(metric: "supply chain", unit: "count", limit: 250.0), QualityBudget(metric: "access control", unit: "count", limit: 250.0), QualityBudget(metric: "incident response", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-asn1", part: "ASN.1 DER parsing", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-certificates", part: "X.509 certificate parsing/verification", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-tls", part: "TLS implementation", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Certificate Rotation, including compromised-device and replay scenarios.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Keep Certificate Rotation secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Certificate Rotation: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Certificate Rotation inputs.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Record auditable evidence that Certificate Rotation fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
