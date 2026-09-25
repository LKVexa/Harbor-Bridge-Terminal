// Generated from checklist component 135 — do not hand-edit the contract block; regenerate.
// Networking and API Infrastructure · networking/API layer · control family: general

import Foundation
import ComponentKit

public struct C0135RetryEngine: AppComponent {
    public static let contract = ComponentContract(
        id: 135,
        name: "Retry Engine",
        phase: 7,
        phaseName: "Networking and API Infrastructure",
        layer: "networking/API",
        purpose: "Retry Engine: the networking/API responsibility named by checklist component 135 (Networking and API Infrastructure).",
        inputs: ["Retry Engine configuration (typed, validated)", "ComponentContext"],
        outputs: ["Retry Engine state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "transport correctness, request lifecycle, protocol contracts, resilience, security",
        budgets: [QualityBudget(metric: "transport correctness", unit: "count", limit: 100.0), QualityBudget(metric: "request lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "protocol contracts", unit: "count", limit: 250.0), QualityBudget(metric: "resilience", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-runtime", part: "OpenAPI runtime types and middleware", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-http-types", part: "Currency HTTP request/response types", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Retry Engine, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Retry Engine.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Retry Engine, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Retry Engine.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Retry Engine while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
