// Generated from checklist component 236 — do not hand-edit the contract block; regenerate.
// Privacy Architecture · privacy architecture layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0236PrivacyPreservingAnalytics: AppComponent {
    public static let contract = ComponentContract(
        id: 236,
        name: "Privacy-Preserving Analytics",
        phase: 12,
        phaseName: "Privacy Architecture",
        layer: "privacy architecture",
        purpose: "Privacy-Preserving Analytics: the privacy architecture responsibility named by checklist component 236 (Privacy Architecture).",
        inputs: ["Privacy-Preserving Analytics configuration (typed, validated)", "ComponentContext"],
        outputs: ["Privacy-Preserving Analytics state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["AppTrackingTransparency"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "data inventory, consent, privacy manifests, tracking rules, minimization",
        budgets: [QualityBudget(metric: "data inventory", unit: "count", limit: 100.0), QualityBudget(metric: "consent", unit: "count", limit: 250.0), QualityBudget(metric: "privacy manifests", unit: "count", limit: 250.0), QualityBudget(metric: "tracking rules", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-homomorphic-encryption", part: "Homomorphic encryption / private information retrieval", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-homomorphic-encryption-protobuf", part: "HE protobuf schemas", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-nio-oblivious-http", part: "Oblivious HTTP (privacy relay)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Privacy-Preserving Analytics must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Privacy-Preserving Analytics a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Privacy-Preserving Analytics; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Privacy-Preserving Analytics during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Privacy-Preserving Analytics is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
