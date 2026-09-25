// Generated from checklist component 557 — do not hand-edit the contract block; regenerate.
// CI/CD · CI/CD layer · control family: trustBoundary

import Foundation
import ComponentKit

public struct C0557SecurityScanPipeline: AppComponent {
    public static let contract = ComponentContract(
        id: 557,
        name: "Security Scan Pipeline",
        phase: 33,
        phaseName: "CI/CD",
        layer: "CI/CD",
        purpose: "Security Scan Pipeline: the CI/CD responsibility named by checklist component 557 (CI/CD).",
        inputs: ["Security Scan Pipeline configuration (typed, validated)", "ComponentContext"],
        outputs: ["Security Scan Pipeline state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "pipeline integrity, automated evidence, signing/release automation, rollback, auditability",
        budgets: [QualityBudget(metric: "pipeline integrity", unit: "count", limit: 100.0), QualityBudget(metric: "automated evidence", unit: "count", limit: 250.0), QualityBudget(metric: "signing/release automation", unit: "count", limit: 250.0), QualityBudget(metric: "rollback", unit: "count", limit: 250.0)],
        family: .trustBoundary,
        userVisible: false,
        donors: [DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-argument-parser", part: "CLI argument parsing (build tooling only)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .trustBoundary, clauses: [
        FamilyClause(control: 21, statement: "Define the trust boundary and attacker model specifically for Security Scan Pipeline, including compromised-device and replay scenarios.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Keep Security Scan Pipeline secrets and sensitive material out of source control, logs, analytics payloads, screenshots, and crash attachments.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Document cryptographic/key lifecycle for Security Scan Pipeline: generation, storage, access control, rotation, invalidation, migration, and destruction.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Add negative security tests for malformed, replayed, expired, downgraded, substituted, and unauthorized Security Scan Pipeline inputs.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Record auditable evidence that Security Scan Pipeline fails closed when trust, identity, integrity, or authorization checks cannot be established.", evidence: .ciRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
