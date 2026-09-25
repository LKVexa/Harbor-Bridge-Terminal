// Component protocol, the actor that hosts one component's lifecycle, and the registry /
// composition root that boots all 735 in phase order (x.04 boundary, x.05, x.07, x.16).

import Foundation

/// Shared dependencies handed to each component. No globals (x.08).
public struct ComponentContext: Sendable {
    public let environment: String
    public let bounds: InputBounds
    public init(environment: String = "development", bounds: InputBounds = InputBounds()) {
        self.environment = environment; self.bounds = bounds
    }
}

/// Every one of the 735 components conforms. Implementation details stay `internal` to their module.
public protocol AppComponent: Sendable {
    static var contract: ComponentContract { get }
    static var familyDeclaration: FamilyDeclaration { get }
    init(context: ComponentContext)
    /// Accepts one external input; must validate before use.
    func accept(_ input: Data) async throws -> Data
}

public extension AppComponent {
    /// Default behaviour of an unimplemented skeleton component: validate, then refuse honestly.
    func accept(_ input: Data) async throws -> Data {
        try InputBounds().validate(input, for: Self.contract.id)
        throw ComponentError(Self.contract.id, .notImplemented, detail: "skeleton: feature logic not written")
    }
}

/// Receives every accepted lifecycle transition, in order. VEC1Bridge.LifecycleLedger implements it
/// to turn host transitions into VEC1 (Generic Photon) evidence; ComponentKit itself stays VEC-agnostic.
public protocol LifecycleObserver: Sendable {
    func componentDidTransition(_ id: ComponentID, from: LifecycleState, to: LifecycleState) async
}

/// Serialises lifecycle transitions for one component; refuses illegal ones.
public actor ComponentHost {
    public let contract: ComponentContract
    public private(set) var state: LifecycleState = .uninitialized
    public private(set) var history: [LifecycleState] = [.uninitialized]
    public let permissions: PermissionGate
    public let diagnostics: Diagnostics
    public let observer: (any LifecycleObserver)?

    public init(contract: ComponentContract, observer: (any LifecycleObserver)? = nil) {
        self.contract = contract
        self.observer = observer
        permissions = PermissionGate(owner: contract.id, declared: contract.capabilities)
        diagnostics = Diagnostics(component: contract.id, name: contract.name)
    }

    public func transition(to next: LifecycleState) async throws {
        try Task.checkCancellation()
        guard Lifecycle.isLegal(state, next) else {
            let e = ComponentError(contract.id, .invalidTransition, detail: "\(state.rawValue)->\(next.rawValue)")
            diagnostics.failure(e)
            throw e
        }
        let previous = state
        state = next
        history.append(next)
        await observer?.componentDidTransition(contract.id, from: previous, to: next)
    }

    public func start() async throws { try await transition(to: .initializing); try await transition(to: .active) }
    public func suspend() async throws { try await transition(to: .suspended) }
    public func resume() async throws { try await transition(to: .active) }
    public func stop() async throws { try await transition(to: .tearingDown); try await transition(to: .terminated) }
}

/// Registry of every component type; the composition root builds from it.
public struct ComponentRegistry: Sendable {
    public let types: [any AppComponent.Type]
    public init(_ types: [any AppComponent.Type]) { self.types = types }

    public var contracts: [ComponentContract] { types.map { $0.contract }.sorted { $0.id < $1.id } }

    /// Integrity problems: duplicate ids, missing ids, family/declaration mismatch.
    public func integrityProblems(expected: ClosedRange<Int> = 1...735) -> [String] {
        var problems: [String] = []
        let ids = types.map { $0.contract.id.rawValue }
        let dupes = Dictionary(grouping: ids, by: { $0 }).filter { $1.count > 1 }.keys.sorted()
        if !dupes.isEmpty { problems.append("duplicate ids: \(dupes)") }
        let missing = Set(expected).subtracting(ids).sorted()
        if !missing.isEmpty { problems.append("missing ids: \(missing.prefix(20))") }
        for t in types where t.contract.family != t.familyDeclaration.family {
            problems.append("\(t.contract.id) family mismatch")
        }
        return problems
    }
}

/// Boots components in phase order; stops in reverse. Deterministic (x.13 budget domain: startup).
public actor CompositionRoot {
    public let registry: ComponentRegistry
    public private(set) var hosts: [ComponentID: ComponentHost] = [:]
    public let observer: (any LifecycleObserver)?
    public init(registry: ComponentRegistry, observer: (any LifecycleObserver)? = nil) {
        self.registry = registry; self.observer = observer
    }

    public func bootAll() async throws {
        for c in registry.contracts.sorted(by: { ($0.phase, $0.id) < ($1.phase, $1.id) }) {
            let h = ComponentHost(contract: c, observer: observer)
            try await h.start()
            hosts[c.id] = h
        }
    }

    public func stopAll() async throws {
        for id in hosts.keys.sorted(by: >) { try await hosts[id]?.stop() }
    }
}
