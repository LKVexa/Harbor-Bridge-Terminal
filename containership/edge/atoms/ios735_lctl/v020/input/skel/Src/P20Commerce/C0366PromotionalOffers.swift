// Generated from checklist component 366 — do not hand-edit the contract block; regenerate.
// Commerce · commerce layer · control family: capabilityDetection

import Foundation
import ComponentKit

public struct C0366PromotionalOffers: AppComponent {
    public static let contract = ComponentContract(
        id: 366,
        name: "Promotional Offers",
        phase: 20,
        phaseName: "Commerce",
        layer: "commerce",
        purpose: "Promotional Offers: the commerce responsibility named by checklist component 366 (Commerce).",
        inputs: ["Promotional Offers configuration (typed, validated)", "ComponentContext"],
        outputs: ["Promotional Offers state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request motion only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["CoreMotion", "StoreKit", "PassKit"],
        capabilities: [.motion],
        platform: PlatformSupport(requiresHardware: [.motion], fallback: "hide the feature and explain why when motion is unavailable"),
        budgetDomain: "StoreKit transactions, entitlement truth, server verification, restore/refund behavior",
        budgets: [QualityBudget(metric: "StoreKit transactions", unit: "count", limit: 100.0), QualityBudget(metric: "entitlement truth", unit: "count", limit: 250.0), QualityBudget(metric: "server verification", unit: "count", limit: 250.0), QualityBudget(metric: "restore/refund behavior", unit: "count", limit: 250.0)],
        family: .capabilityDetection,
        userVisible: false,
        donors: [DonorPart(car: "swift-collections", part: "Deque, OrderedDictionary, Heap, BitSet", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-urlsession", part: "URLSession transport for OpenAPI clients, bidirectional streaming", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .capabilityDetection, clauses: [
        FamilyClause(control: 21, statement: "Implement explicit capability detection for Promotional Offers and provide a safe fallback when hardware or authorization is unavailable.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Model Promotional Offers as a state machine covering discovery, connection/start, active use, interruption, recovery, and teardown.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Validate Promotional Offers against noisy measurements, duplicate callbacks, disconnects, permission changes, and app lifecycle transitions.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Bound polling/sampling rates and background activity so Promotional Offers respects battery, thermal, and system resource constraints.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add device-matrix tests on representative physical hardware because simulator coverage is insufficient for Promotional Offers.", evidence: .deviceRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
