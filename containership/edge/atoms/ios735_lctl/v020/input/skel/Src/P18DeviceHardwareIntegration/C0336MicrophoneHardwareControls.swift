// Generated from checklist component 336 — do not hand-edit the contract block; regenerate.
// Device Hardware Integration · device hardware layer · control family: mediaSession

import Foundation
import ComponentKit

public struct C0336MicrophoneHardwareControls: AppComponent {
    public static let contract = ComponentContract(
        id: 336,
        name: "Microphone Hardware Controls",
        phase: 18,
        phaseName: "Device Hardware Integration",
        layer: "device hardware",
        purpose: "Microphone Hardware Controls: the device hardware responsibility named by checklist component 336 (Device Hardware Integration).",
        inputs: ["Microphone Hardware Controls configuration (typed, validated)", "ComponentContext"],
        outputs: ["Microphone Hardware Controls state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request microphone only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["Foundation"],
        capabilities: [.microphone],
        platform: PlatformSupport(requiresHardware: [.microphone], fallback: "hide the feature and explain why when microphone is unavailable"),
        budgetDomain: "capability discovery, session lifecycle, hardware errors, power/thermal constraints",
        budgets: [QualityBudget(metric: "capability discovery", unit: "count", limit: 100.0), QualityBudget(metric: "session lifecycle", unit: "count", limit: 250.0), QualityBudget(metric: "hardware errors", unit: "count", limit: 250.0), QualityBudget(metric: "power/thermal constraints", unit: "count", limit: 250.0)],
        family: .mediaSession,
        userVisible: false,
        donors: [DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-system-metrics", part: "Process metrics (CPU, memory, fds)", license: "Apache-2.0", mode: .patternOnly)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mediaSession, clauses: [
        FamilyClause(control: 21, statement: "Define capture/playback session topology, interruption handling, route changes, permissions, and lifecycle behavior for Microphone Hardware Controls.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Test Microphone Hardware Controls with calls, alarms, AirPods/Bluetooth routes, backgrounding, low storage, camera denial, and microphone denial.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Bound memory and disk use for Microphone Hardware Controls by controlling buffering, decode surfaces, temporary files, and media retention.", evidence: .productDecision),
        FamilyClause(control: 24, statement: "Validate metadata orientation, timestamps, color space, audio session category/mode, and codec/container compatibility for Microphone Hardware Controls.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Ensure media generated or accessed by Microphone Hardware Controls follows explicit privacy, export, deletion, and user-consent rules.", evidence: .productDecision),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
