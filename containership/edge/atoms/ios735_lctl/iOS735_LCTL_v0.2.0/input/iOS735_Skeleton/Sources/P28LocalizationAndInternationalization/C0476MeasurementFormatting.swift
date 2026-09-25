// Generated from checklist component 476 — do not hand-edit the contract block; regenerate.
// Localization and Internationalization · localization layer · control family: localeFormatting

import Foundation
import ComponentKit

public struct C0476MeasurementFormatting: AppComponent {
    public static let contract = ComponentContract(
        id: 476,
        name: "Measurement Formatting",
        phase: 28,
        phaseName: "Localization and Internationalization",
        layer: "localization",
        purpose: "Measurement Formatting: the localization responsibility named by checklist component 476 (Localization and Internationalization).",
        inputs: ["Measurement Formatting configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Measurement Formatting state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "locale semantics, formatting, RTL behavior, translation QA, pseudo-localization",
        budgets: [QualityBudget(metric: "locale semantics", unit: "count", limit: 100.0), QualityBudget(metric: "formatting", unit: "count", limit: 250.0), QualityBudget(metric: "RTL behavior", unit: "count", limit: 250.0), QualityBudget(metric: "translation QA", unit: "count", limit: 250.0)],
        family: .localeFormatting,
        userVisible: true,
        donors: [DonorPart(car: "swift-distributed-tracing-extras", part: "Tracing semantic conventions", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .localeFormatting, clauses: [
        FamilyClause(control: 21, statement: "Ensure Measurement Formatting uses locale-aware Foundation formatting and never assembles user-visible grammar from concatenated fragments.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Test Measurement Formatting with long translations, RTL scripts, non-Latin digits, different calendars, and extreme number/date values.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Separate developer identifiers from localized values so Measurement Formatting can evolve translations without breaking runtime lookup keys.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Include pseudo-localization coverage for Measurement Formatting to expose clipping, hard-coded strings, mirrored-layout defects, and unlocalized assets.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Define translation ownership, review, fallback locale, stale-string detection, and release gating for Measurement Formatting.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
