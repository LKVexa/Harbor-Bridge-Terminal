// Generated from checklist component 440 — do not hand-edit the contract block; regenerate.
// Logging and Observability · observability layer · control family: capabilityDetection

import Foundation
import ComponentKit

public struct C0440BatteryPowerMetrics: AppComponent {
    public static let contract = ComponentContract(
        id: 440,
        name: "Battery/Power Metrics",
        phase: 25,
        phaseName: "Logging and Observability",
        layer: "observability",
        purpose: "Battery/Power Metrics: the observability responsibility named by checklist component 440 (Logging and Observability).",
        inputs: ["Battery/Power Metrics configuration (typed, validated)", "ComponentContext"],
        outputs: ["Battery/Power Metrics state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["OSLog", "MetricKit"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "structured telemetry, privacy-safe diagnostics, metrics, traces, crash evidence",
        budgets: [QualityBudget(metric: "structured telemetry", unit: "count", limit: 100.0), QualityBudget(metric: "privacy-safe diagnostics", unit: "count", limit: 250.0), QualityBudget(metric: "metrics", unit: "count", limit: 250.0), QualityBudget(metric: "traces", unit: "count", limit: 250.0)],
        family: .capabilityDetection,
        userVisible: false,
        donors: [DonorPart(car: "swift-log", part: "Structured logging API (Logger, LogHandler, MetadataProvider)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-metrics", part: "Metrics API (Counter, Recorder, Timer, Gauge)", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .capabilityDetection, clauses: [
        FamilyClause(control: 21, statement: "Implement explicit capability detection for Battery/Power Metrics and provide a safe fallback when hardware or authorization is unavailable.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Model Battery/Power Metrics as a state machine covering discovery, connection/start, active use, interruption, recovery, and teardown.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Validate Battery/Power Metrics against noisy measurements, duplicate callbacks, disconnects, permission changes, and app lifecycle transitions.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Bound polling/sampling rates and background activity so Battery/Power Metrics respects battery, thermal, and system resource constraints.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add device-matrix tests on representative physical hardware because simulator coverage is insufficient for Battery/Power Metrics.", evidence: .deviceRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
