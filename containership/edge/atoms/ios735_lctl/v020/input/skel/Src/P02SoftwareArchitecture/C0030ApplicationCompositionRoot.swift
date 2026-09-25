// Generated from checklist component 30 — do not hand-edit the contract block; regenerate.
// Software Architecture · software architecture layer · control family: general

import Foundation
import ComponentKit

public struct C0030ApplicationCompositionRoot: AppComponent {
    public static let contract = ComponentContract(
        id: 30,
        name: "Application Composition Root",
        phase: 2,
        phaseName: "Software Architecture",
        layer: "software architecture",
        purpose: "Application Composition Root: the software architecture responsibility named by checklist component 30 (Software Architecture).",
        inputs: ["Application Composition Root configuration (typed, validated)", "ComponentContext"],
        outputs: ["Application Composition Root state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "module contracts, dependency direction, state ownership, testable boundaries",
        budgets: [QualityBudget(metric: "module contracts", unit: "count", limit: 100.0), QualityBudget(metric: "dependency direction", unit: "count", limit: 250.0), QualityBudget(metric: "state ownership", unit: "count", limit: 250.0), QualityBudget(metric: "testable boundaries", unit: "count", limit: 250.0)],
        family: .general,
        userVisible: false,
        donors: [DonorPart(car: "swift-openapi-runtime", part: "OpenAPI runtime types and middleware", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swiftpm-on-llbuild2", part: "SwiftPM on llbuild2", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .general, clauses: [
        FamilyClause(control: 21, statement: "Define the functional and non-functional contract for Application Composition Root, including inputs, outputs, ownership, invariants, and lifecycle.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Identify platform APIs, entitlements, configuration, dependencies, and availability constraints required by Application Composition Root.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Document failure modes and degraded behavior for Application Composition Root, including unavailable services, malformed state, and interrupted execution.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Create deterministic tests for normal, boundary, invalid, concurrent, and lifecycle-transition behavior of Application Composition Root.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Instrument only the operational signals needed to diagnose Application Composition Root while protecting user data and secrets.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
