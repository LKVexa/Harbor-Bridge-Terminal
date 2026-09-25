// Generated from checklist component 360 — do not hand-edit the contract block; regenerate.
// Commerce · commerce layer · control family: storeKitTruth

import Foundation
import ComponentKit

public struct C0360Subscriptions: AppComponent {
    public static let contract = ComponentContract(
        id: 360,
        name: "Subscriptions",
        phase: 20,
        phaseName: "Commerce",
        layer: "commerce",
        purpose: "Subscriptions: the commerce responsibility named by checklist component 360 (Commerce).",
        inputs: ["Subscriptions configuration (typed, validated)", "ComponentContext"],
        outputs: ["Subscriptions state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["StoreKit", "PassKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "StoreKit transactions, entitlement truth, server verification, restore/refund behavior",
        budgets: [QualityBudget(metric: "StoreKit transactions", unit: "count", limit: 100.0), QualityBudget(metric: "entitlement truth", unit: "count", limit: 250.0), QualityBudget(metric: "server verification", unit: "count", limit: 250.0), QualityBudget(metric: "restore/refund behavior", unit: "count", limit: 250.0)],
        family: .storeKitTruth,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections", part: "Deque, OrderedDictionary, Heap, BitSet", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .storeKitTruth, clauses: [
        FamilyClause(control: 21, statement: "Treat verified StoreKit/server transaction state—not local UI state—as the source of truth for Subscriptions.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Make Subscriptions idempotent across duplicate transaction updates, interrupted purchases, device changes, restores, refunds, and revocations.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Test Subscriptions using StoreKit testing plus sandbox/TestFlight scenarios covering expiration, renewal, billing retry, grace period, and cancellation.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Separate product presentation from entitlement evaluation so Subscriptions cannot grant access before verification completes.", evidence: .productDecision),
        FamilyClause(control: 25, statement: "Retain privacy-safe audit evidence for Subscriptions sufficient to reconcile user access with transaction history.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
