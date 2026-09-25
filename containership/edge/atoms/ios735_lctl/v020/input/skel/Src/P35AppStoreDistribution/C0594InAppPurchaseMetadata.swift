// Generated from checklist component 594 — do not hand-edit the contract block; regenerate.
// App Store Distribution · App Store distribution layer · control family: storeKitTruth

import Foundation
import ComponentKit

public struct C0594InAppPurchaseMetadata: AppComponent {
    public static let contract = ComponentContract(
        id: 594,
        name: "In-App Purchase Metadata",
        phase: 35,
        phaseName: "App Store Distribution",
        layer: "App Store distribution",
        purpose: "In-App Purchase Metadata: the App Store distribution responsibility named by checklist component 594 (App Store Distribution).",
        inputs: ["In-App Purchase Metadata configuration (typed, validated)", "ComponentContext"],
        outputs: ["In-App Purchase Metadata state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["StoreKit", "PassKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "App Store Connect metadata, compliance, signing, review readiness, release control",
        budgets: [QualityBudget(metric: "App Store Connect metadata", unit: "count", limit: 100.0), QualityBudget(metric: "compliance", unit: "count", limit: 250.0), QualityBudget(metric: "signing", unit: "count", limit: 250.0), QualityBudget(metric: "review readiness", unit: "count", limit: 250.0)],
        family: .storeKitTruth,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections", part: "Deque, OrderedDictionary, Heap, BitSet", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .storeKitTruth, clauses: [
        FamilyClause(control: 21, statement: "Treat verified StoreKit/server transaction state—not local UI state—as the source of truth for In-App Purchase Metadata.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Make In-App Purchase Metadata idempotent across duplicate transaction updates, interrupted purchases, device changes, restores, refunds, and revocations.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Test In-App Purchase Metadata using StoreKit testing plus sandbox/TestFlight scenarios covering expiration, renewal, billing retry, grace period, and cancellation.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Separate product presentation from entitlement evaluation so In-App Purchase Metadata cannot grant access before verification completes.", evidence: .productDecision),
        FamilyClause(control: 25, statement: "Retain privacy-safe audit evidence for In-App Purchase Metadata sufficient to reconcile user access with transaction history.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
