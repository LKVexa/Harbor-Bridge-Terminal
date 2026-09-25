// Generated from checklist component 589 — do not hand-edit the contract block; regenerate.
// App Store Distribution · App Store distribution layer · control family: mediaSession

import Foundation
import ComponentKit

public struct C0589AppPreviewMedia: AppComponent {
    public static let contract = ComponentContract(
        id: 589,
        name: "App Preview Media",
        phase: 35,
        phaseName: "App Store Distribution",
        layer: "App Store distribution",
        purpose: "App Preview Media: the App Store distribution responsibility named by checklist component 589 (App Store Distribution).",
        inputs: ["App Preview Media configuration (typed, validated)", "ComponentContext"],
        outputs: ["App Preview Media state snapshot", "structured ComponentError on failure", "privacy-safe diagnostics events"],
        sideEffects: ["none at skeleton stage"],
        invariants: ["lifecycle transitions follow Lifecycle.transitions; illegal ones are refused", "every external input passes InputBounds before use", "no capability is requested before it is declared and justified", "no sensitive metadata key reaches a log sink in clear"],
        frameworks: ["SwiftUI", "AVFoundation", "AVKit", "PhotosUI"],
        capabilities: [],
        platform: PlatformSupport(requiresHardware: [], fallback: "degrade to a read-only / disabled state with an explanatory message"),
        budgetDomain: "App Store Connect metadata, compliance, signing, review readiness, release control",
        budgets: [QualityBudget(metric: "App Store Connect metadata", unit: "count", limit: 100.0), QualityBudget(metric: "compliance", unit: "count", limit: 250.0), QualityBudget(metric: "signing", unit: "count", limit: 250.0), QualityBudget(metric: "review readiness", unit: "count", limit: 250.0)],
        family: .mediaSession,
        userVisible: false,
        donors: [DonorPart(car: "swift-binary-parsing", part: "Safe binary parsing", license: "Apache-2.0", mode: .packageDependency), DonorPart(car: "swift-play-experimental", part: "Swift playground/experimental tooling", license: "Apache-2.0", mode: .patternOnly), DonorPart(car: "swift-collections", part: "Deque, OrderedDictionary, Heap, BitSet", license: "Apache-2.0", mode: .packageDependency)]
    )

    public static let familyDeclaration = FamilyDeclaration(family: .mediaSession, clauses: [
        FamilyClause(control: 21, statement: "Define capture/playback session topology, interruption handling, route changes, permissions, and lifecycle behavior for App Preview Media.", evidence: .skeletonDeclared),
        FamilyClause(control: 22, statement: "Test App Preview Media with calls, alarms, AirPods/Bluetooth routes, backgrounding, low storage, camera denial, and microphone denial.", evidence: .skeletonDeclared),
        FamilyClause(control: 23, statement: "Bound memory and disk use for App Preview Media by controlling buffering, decode surfaces, temporary files, and media retention.", evidence: .productDecision),
        FamilyClause(control: 24, statement: "Validate metadata orientation, timestamps, color space, audio session category/mode, and codec/container compatibility for App Preview Media.", evidence: .skeletonDeclared),
        FamilyClause(control: 25, statement: "Ensure media generated or accessed by App Preview Media follows explicit privacy, export, deletion, and user-consent rules.", evidence: .productDecision),
    ])

    let context: ComponentContext
    public init(context: ComponentContext) { self.context = context }
}
