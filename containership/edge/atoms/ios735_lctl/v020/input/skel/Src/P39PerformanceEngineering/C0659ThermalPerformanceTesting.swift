// Generated from checklist component 659 — do not hand-edit the contract block; regenerate.
// Performance Engineering · performance engineering layer · control family: capabilityDetection

import Foundation
import ComponentKit

public struct C0659ThermalPerformanceTesting: AppComponent {
    public static let contract = ComponentContract(
        id: 659,
        name: "Thermal Performance Testing",
        phase: 39,
        phaseName: "Performance Engineering",
        layer: "performance engineering",
        purpose: "Thermal Performance Testing: the performance engineering responsibility named by checklist component 659 (Performance Engineering).",
        inputs: ["Thermal Performance Testing configuration (typed, validated)", "ComponentContext"],
        outputs: ["Thermal Performance Testing state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["XCTest", "Testing"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "measured budgets, Instruments evidence, memory/CPU/GPU/power optimization",
        budgets: [QualityBudget(metric: "measured budgets", unit: "count", limit: 100.0), QualityBudget(metric: "Instruments evidence", unit: "count", limit: 250.0), QualityBudget(metric: "memory/CPU/GPU/power optimization", unit: "count", limit: 250.0)],
        family: .capabilityDetection,
        userVisible: false,
        donors: [DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-profile-recorder", part: "In-process sampling profiler", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .capabilityDetection, clauses: [
        FamilyClause(control: 21, statement: "Implement explicit capability detection for Thermal Performance Testing and provide a safe fallback when hardware or authorization is unavailable.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Model Thermal Performance Testing as a state machine covering discovery, connection/start, active use, interruption, recovery, and teardown.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Validate Thermal Performance Testing against noisy measurements, duplicate callbacks, disconnects, permission changes, and app lifecycle transitions.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Bound polling/sampling rates and background activity so Thermal Performance Testing respects battery, thermal, and system resource constraints.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add device-matrix tests on representative physical hardware because simulator coverage is insufficient for Thermal Performance Testing.", evidence: .deviceRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
