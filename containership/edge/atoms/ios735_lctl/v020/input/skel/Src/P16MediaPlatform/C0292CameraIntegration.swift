// Generated from checklist component 292 — do not hand-edit the contract block; regenerate.
// Media Platform · media platform layer · control family: mediaSession

import Foundation
import ComponentKit

public struct C0292CameraIntegration: AppComponent {
    public static let contract = ComponentContract(
        id: 292,
        name: "Camera Integration",
        phase: 16,
        phaseName: "Media Platform",
        layer: "media platform",
        purpose: "Camera Integration: the media platform responsibility named by checklist component 292 (Media Platform).",
        inputs: ["Camera Integration configuration (typed, validated)", "ComponentContext"],
        outputs: ["Camera Integration state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["may request camera only after in-context justification"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["AVFoundation", "AVKit", "PhotosUI"],
        capabilities: [.camera],
        platform: PlatformSupport(requiresHardware: [.camera], fallback: "hide the feature and explain why when camera is unavailable"),
        budgetDomain: "capture/playback sessions, media pipelines, permissions, codecs, interruption handling",
        budgets: [QualityBudget(metric: "capture/playback sessions", unit: "count", limit: 100.0), QualityBudget(metric: "media pipelines", unit: "count", limit: 250.0), QualityBudget(metric: "permissions", unit: "count", limit: 250.0), QualityBudget(metric: "codecs", unit: "count", limit: 250.0)],
        family: .mediaSession,
        userVisible: false,
        donors: [DonorPart(car: "swift-service-context", part: "Task-local context propagation", license: "Apache-2.0", mode: .vendored), DonorPart(car: "swift-binary-parsing", part: "Safe binary parsing", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mediaSession, clauses: [
        FamilyClause(control: 21, statement: "Define capture/playback session topology, interruption handling, route changes, permissions, and lifecycle behavior for Camera Integration.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Test Camera Integration with calls, alarms, AirPods/Bluetooth routes, backgrounding, low storage, camera denial, and microphone denial.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Bound memory and disk use for Camera Integration by controlling buffering, decode surfaces, temporary files, and media retention.", evidence: .productDecision),
        FamilyClause(control: 24, statement: "Validate metadata orientation, timestamps, color space, audio session category/mode, and codec/container compatibility for Camera Integration.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Ensure media generated or accessed by Camera Integration follows explicit privacy, export, deletion, and user-consent rules.", evidence: .productDecision),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
