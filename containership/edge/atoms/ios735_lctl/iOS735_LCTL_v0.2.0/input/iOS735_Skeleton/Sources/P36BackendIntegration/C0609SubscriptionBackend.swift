// Generated from checklist component 609 — do not hand-edit the contract block; regenerate.
// Backend Integration · backend integration layer · control family: storeKitTruth

import Foundation
import ComponentKit

public struct C0609SubscriptionBackend: AppComponent {
    public static let contract = ComponentContract(
        id: 609,
        name: "Subscription Backend",
        phase: 36,
        phaseName: "Backend Integration",
        layer: "backend integration",
        purpose: "Subscription Backend: the backend integration responsibility named by checklist component 609 (Backend Integration).",
        inputs: ["Subscription Backend configuration (typed, validated)", "ComponentContext", "network responses"],
        outputs: ["Subscription Backend state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request network only after in-context justification", "network I/O"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["StoreKit", "PassKit"],
        capabilities: [.network],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "mobile/backend contracts, authentication, storage, observability, failure isolation",
        budgets: [QualityBudget(metric: "mobile/backend contracts", unit: "count", limit: 100.0), QualityBudget(metric: "authentication", unit: "count", limit: 250.0), QualityBudget(metric: "storage", unit: "count", limit: 250.0), QualityBudget(metric: "observability", unit: "count", limit: 250.0)],
        family: .storeKitTruth,
        userVisible: false,
        donors: [DonorPart(car: "swift-openapi-runtime", part: "OpenAPI runtime types and middleware", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-generator", part: "Build-time OpenAPI client generation plugin", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .storeKitTruth, clauses: [
        FamilyClause(control: 21, statement: "Treat verified StoreKit/server transaction state—not local UI state—as the source of truth for Subscription Backend.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Make Subscription Backend idempotent across duplicate transaction updates, interrupted purchases, device changes, restores, refunds, and revocations.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Test Subscription Backend using StoreKit testing plus sandbox/TestFlight scenarios covering expiration, renewal, billing retry, grace period, and cancellation.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Separate product presentation from entitlement evaluation so Subscription Backend cannot grant access before verification completes.", evidence: .productDecision),
        FamilyClause(control: 25, statement: "Retain privacy-safe audit evidence for Subscription Backend sufficient to reconcile user access with transaction history.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
