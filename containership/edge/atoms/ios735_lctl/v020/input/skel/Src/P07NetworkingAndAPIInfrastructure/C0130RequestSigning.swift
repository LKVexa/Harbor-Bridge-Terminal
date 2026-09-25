// Generated from checklist component 130 — do not hand-edit the contract block; regenerate.
// Networking and API Infrastructure · networking/API layer · control family: wireContract

import Foundation
import ComponentKit

public struct C0130RequestSigning: AppComponent {
    public static let contract = ComponentContract(
        id: 130,
        name: "Request Signing",
        phase: 7,
        phaseName: "Networking and API Infrastructure",
        layer: "networking/API",
        purpose: "Request Signing: the networking/API responsibility named by checklist component 130 (Networking and API Infrastructure).",
        inputs: ["Request Signing configuration (typed, validated)", "ComponentContext"],
        outputs: ["Request Signing state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation.URLSession", "Network"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "transport correctness, request lifecycle, protocol contracts, resilience, security",
        budgets: [QualityBudget(metric: "transport correctness", unit: "count", limit: 100.0), QualityBudget(metric: "request lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "protocol contracts", unit: "count", limit: 250.0), QualityBudget(metric: "resilience", unit: "count", limit: 250.0)],
        family: .wireContract,
        userVisible: false,
        donors: [DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-http-types", part: "Currency HTTP request/response types", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .wireContract, clauses: [
        FamilyClause(control: 21, statement: "Define wire-level contracts for Request Signing, including methods/messages, headers, encodings, status semantics, and version compatibility.", evidence: .ciRun),
        FamilyClause(control: 22, statement: "Specify timeout, cancellation, retry, backoff, idempotency, redirect, and duplicate-delivery behavior for Request Signing.", evidence: .ciRun),
        FamilyClause(control: 23, statement: "Verify Request Signing under packet loss, latency, captive portal, DNS failure, TLS failure, offline transitions, and constrained networks.", evidence: .ciRun),
        FamilyClause(control: 24, statement: "Ensure Request Signing redacts authorization headers, cookies, identifiers, query secrets, and response PII from telemetry.", evidence: .ciRun),
        FamilyClause(control: 25, statement: "Create contract tests that reject schema drift and prove backward/forward compatibility for supported server versions.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
