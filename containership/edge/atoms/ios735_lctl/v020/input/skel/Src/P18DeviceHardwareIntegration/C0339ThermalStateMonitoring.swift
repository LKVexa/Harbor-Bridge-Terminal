// Generated from checklist component 339 — do not hand-edit the contract block; regenerate.
// Device Hardware Integration · device hardware layer · control family: capabilityDetection

import Foundation
import ComponentKit

public struct C0339ThermalStateMonitoring: AppComponent {
    public static let contract = ComponentContract(
        id: 339,
        name: "Thermal State Monitoring",
        phase: 18,
        phaseName: "Device Hardware Integration",
        layer: "device hardware",
        purpose: "Thermal State Monitoring: the device hardware responsibility named by checklist component 339 (Device Hardware Integration).",
        inputs: ["Thermal State Monitoring configuration (typed, validated)", "ComponentContext"],
        outputs: ["Thermal State Monitoring state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "capability discovery, session lifecycle, hardware errors, power/thermal constraints",
        budgets: [QualityBudget(metric: "capability discovery", unit: "count", limit: 100.0), QualityBudget(metric: "session lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "hardware errors", unit: "count", limit: 250.0), QualityBudget(metric: "power/thermal constraints", unit: "count", limit: 250.0)],
        family: .capabilityDetection,
        userVisible: false,
        donors: [DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .capabilityDetection, clauses: [
        FamilyClause(control: 21, statement: "Implement explicit capability detection for Thermal State Monitoring and provide a safe fallback when hardware or authorization is unavailable.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Model Thermal State Monitoring as a state machine covering discovery, connection/start, active use, interruption, recovery, and teardown.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Validate Thermal State Monitoring against noisy measurements, duplicate callbacks, disconnects, permission changes, and app lifecycle transitions.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Bound polling/sampling rates and background activity so Thermal State Monitoring respects battery, thermal, and system resource constraints.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add device-matrix tests on representative physical hardware because simulator coverage is insufficient for Thermal State Monitoring.", evidence: .deviceRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
