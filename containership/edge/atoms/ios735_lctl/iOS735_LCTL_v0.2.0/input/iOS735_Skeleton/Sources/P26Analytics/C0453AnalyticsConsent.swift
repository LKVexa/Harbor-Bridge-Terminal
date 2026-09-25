// Generated from checklist component 453 — do not hand-edit the contract block; regenerate.
// Analytics · analytics layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0453AnalyticsConsent: AppComponent {
    public static let contract = ComponentContract(
        id: 453,
        name: "Analytics Consent",
        phase: 26,
        phaseName: "Analytics",
        layer: "analytics",
        purpose: "Analytics Consent: the analytics responsibility named by checklist component 453 (Analytics).",
        inputs: ["Analytics Consent configuration (typed, validated)", "ComponentContext"],
        outputs: ["Analytics Consent state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["AppTrackingTransparency"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "event contracts, data quality, consent, attribution, sampling, reliable delivery",
        budgets: [QualityBudget(metric: "event contracts", unit: "count", limit: 100.0), QualityBudget(metric: "data quality", unit: "count", limit: 250.0), QualityBudget(metric: "consent", unit: "count", limit: 250.0), QualityBudget(metric: "attribution", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-async-algorithms", part: "AsyncSequence debounce/throttle/merge/channel", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-openapi-runtime", part: "OpenAPI runtime types and middleware", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-profile-recorder", part: "In-process sampling profiler", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Analytics Consent must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Analytics Consent a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .productDecision),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Analytics Consent; never rely solely on downstream cleanup.", evidence: .productDecision),
        FamilyClause(control: 24, statement: "Validate Analytics Consent during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .productDecision),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Analytics Consent is actionable rather than merely collected.", evidence: .productDecision),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
