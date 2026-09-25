// Generated from checklist component 493 — do not hand-edit the contract block; regenerate.
// Testing Infrastructure · testing layer · control family: wireContract

import Foundation
import ComponentKit

public struct C0493NetworkTesting: AppComponent {
    public static let contract = ComponentContract(
        id: 493,
        name: "Network Testing",
        phase: 29,
        phaseName: "Testing Infrastructure",
        layer: "testing",
        purpose: "Network Testing: the testing responsibility named by checklist component 493 (Testing Infrastructure).",
        inputs: ["Network Testing configuration (typed, validated)", "ComponentContext", "network responses"],
        outputs: ["Network Testing state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request network only after in-context justification", "network I/O"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation.URLSession", "Network", "XCTest", "Testing"],
        capabilities: [.network],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "test isolation, deterministic fixtures, coverage, failure injection, CI execution",
        budgets: [QualityBudget(metric: "test isolation", unit: "count", limit: 100.0), QualityBudget(metric: "deterministic fixtures", unit: "count", limit: 250.0), QualityBudget(metric: "coverage", unit: "count", limit: 250.0), QualityBudget(metric: "failure injection", unit: "count", limit: 250.0)],
        family: .wireContract,
        userVisible: false,
        donors: [DonorPart(car: "swift-nio-transport-services", part: "NIO on Network.framework (iOS-capable)", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-network-evolution", part: "Networking evolution proposals", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .wireContract, clauses: [
        FamilyClause(control: 21, statement: "Define wire-level contracts for Network Testing, including methods/messages, headers, encodings, status semantics, and version compatibility.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Specify timeout, cancellation, retry, backoff, idempotency, redirect, and duplicate-delivery behavior for Network Testing.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Verify Network Testing under packet loss, latency, captive portal, DNS failure, TLS failure, offline transitions, and constrained networks.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Ensure Network Testing redacts authorization headers, cookies, identifiers, query secrets, and response PII from telemetry.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create contract tests that reject schema drift and prove backward/forward compatibility for supported server versions.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
