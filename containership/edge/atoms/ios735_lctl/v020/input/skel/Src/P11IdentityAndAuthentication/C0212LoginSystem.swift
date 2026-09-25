// Generated from checklist component 212 — do not hand-edit the contract block; regenerate.
// Identity and Authentication · identity/authentication layer · control family: analyticsMinimization

import Foundation
import ComponentKit

public struct C0212LoginSystem: AppComponent {
    public static let contract = ComponentContract(
        id: 212,
        name: "Login System",
        phase: 11,
        phaseName: "Identity and Authentication",
        layer: "identity/authentication",
        purpose: "Login System: the identity/authentication responsibility named by checklist component 212 (Identity and Authentication).",
        inputs: ["Login System configuration (typed, validated)", "ComponentContext"],
        outputs: ["Login System state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "identity proofing, session security, token lifecycle, authorization boundaries",
        budgets: [QualityBudget(metric: "identity proofing", unit: "count", limit: 100.0), QualityBudget(metric: "session security", unit: "count", limit: 250.0), QualityBudget(metric: "token lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "authorization boundaries", unit: "count", limit: 250.0)],
        family: .analyticsMinimization,
        userVisible: false,
        donors: [DonorPart(car: "swift-system", part: "Typed file-system/syscall wrappers", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-crypto", part: "CryptoKit-compatible crypto API", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .analyticsMinimization, clauses: [
        FamilyClause(control: 21, statement: "Define the exact questions Login System must answer and prohibit collection that has no operational or product purpose.", evidence: .productDecision),
        FamilyClause(control: 22, statement: "Give Login System a stable schema with event/metric versioning, units, dimensions, sampling rules, and cardinality limits.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Redact or hash sensitive values before they enter Login System; never rely solely on downstream cleanup.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Login System during offline use, retries, duplicate delivery, clock skew, app upgrades, and partial backend outages.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Create dashboards/alerts or diagnostic queries that prove Login System is actionable rather than merely collected.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
