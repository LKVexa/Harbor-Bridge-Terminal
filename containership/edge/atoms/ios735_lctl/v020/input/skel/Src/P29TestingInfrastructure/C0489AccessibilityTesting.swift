// Generated from checklist component 489 — do not hand-edit the contract block; regenerate.
// Testing Infrastructure · testing layer · control family: voiceOver

import Foundation
import ComponentKit

public struct C0489AccessibilityTesting: AppComponent {
    public static let contract = ComponentContract(
        id: 489,
        name: "Accessibility Testing",
        phase: 29,
        phaseName: "Testing Infrastructure",
        layer: "testing",
        purpose: "Accessibility Testing: the testing responsibility named by checklist component 489 (Testing Infrastructure).",
        inputs: ["Accessibility Testing configuration (typed, validated)", "ComponentContext", "user interaction events"],
        outputs: ["Accessibility Testing state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Accessibility", "UIKit", "XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "test isolation, deterministic fixtures, coverage, failure injection, CI execution",
        budgets: [QualityBudget(metric: "test isolation", unit: "count", limit: 100.0), QualityBudget(metric: "deterministic fixtures", unit: "count", limit: 250.0), QualityBudget(metric: "coverage", unit: "count", limit: 250.0), QualityBudget(metric: "failure injection", unit: "count", limit: 250.0)],
        family: .voiceOver,
        userVisible: true,
        donors: []
    )

    public static let familyDeclaration = FamilyDeclaration(family: .voiceOver, clauses: [
        FamilyClause(control: 21, statement: "Test Accessibility Testing with VoiceOver enabled on physical hardware and verify meaningful spoken order and rotor behavior.", evidence: .deviceRun),
        FamilyClause(control: 22, statement: "Verify Accessibility Testing at the largest supported accessibility text sizes without clipping, overlap, hidden controls, or lost functionality.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Ensure Accessibility Testing does not rely solely on color, motion, shape, audio, or spatial position to communicate essential meaning.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Validate Accessibility Testing with Reduce Motion, Increase Contrast, Differentiate Without Color, and relevant accessibility settings enabled.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add automated accessibility assertions where possible and retain manual test evidence for interactions automation cannot validate.", evidence: .skeletonDeclared),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
