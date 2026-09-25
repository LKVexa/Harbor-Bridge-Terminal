// Generated from checklist component 326 — do not hand-edit the contract block; regenerate.
// Device Hardware Integration · device hardware layer · control family: capabilityDetection

import Foundation
import ComponentKit

public struct C0326NearbyInteraction: AppComponent {
    public static let contract = ComponentContract(
        id: 326,
        name: "Nearby Interaction",
        phase: 18,
        phaseName: "Device Hardware Integration",
        layer: "device hardware",
        purpose: "Nearby Interaction: the device hardware responsibility named by checklist component 326 (Device Hardware Integration).",
        inputs: ["Nearby Interaction configuration (typed, validated)", "ComponentContext"],
        outputs: ["Nearby Interaction state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [.uwb], fallback: "hide the feature and explain why when uwb is unavailable"),
        budgetDomain: "capability discovery, session lifecycle, hardware errors, power/thermal constraints",
        budgets: [QualityBudget(metric: "capability discovery", unit: "count", limit: 100.0), QualityBudget(metric: "session lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "hardware errors", unit: "count", limit: 250.0), QualityBudget(metric: "power/thermal constraints", unit: "count", limit: 250.0)],
        family: .capabilityDetection,
        userVisible: false,
        donors: [DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .capabilityDetection, clauses: [
        FamilyClause(control: 21, statement: "Implement explicit capability detection for Nearby Interaction and provide a safe fallback when hardware or authorization is unavailable.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Model Nearby Interaction as a state machine covering discovery, connection/start, active use, interruption, recovery, and teardown.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Validate Nearby Interaction against noisy measurements, duplicate callbacks, disconnects, permission changes, and app lifecycle transitions.", evidence: .skeletonDeclared),
        FamilyClause(control: 24, statement: "Bound polling/sampling rates and background activity so Nearby Interaction respects battery, thermal, and system resource constraints.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Add device-matrix tests on representative physical hardware because simulator coverage is insufficient for Nearby Interaction.", evidence: .deviceRun),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
