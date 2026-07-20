import Foundation
import AppIntents

struct HELMAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: GetHELMStatusIntent(),
            phrases: [
                "Ask \(.applicationName) for status",
                "Get \(.applicationName) status"
            ],
            shortTitle: "HELM Status",
            systemImageName: "server.rack"
        )
        
        AppShortcut(
            intent: GetHELMAuditPostureIntent(),
            phrases: [
                "Ask \(.applicationName) for audit posture",
                "Get \(.applicationName) audit posture"
            ],
            shortTitle: "HELM Audit Posture",
            systemImageName: "shield.checklist"
        )
        
        AppShortcut(
            intent: ListHELMBlockersIntent(),
            phrases: [
                "Ask \(.applicationName) for blockers",
                "Get \(.applicationName) blockers"
            ],
            shortTitle: "HELM Blockers",
            systemImageName: "exclamationmark.octagon"
        )
        
        AppShortcut(
            intent: ListOnlineAgentsIntent(),
            phrases: [
                "Ask \(.applicationName) which agents are online",
                "Get \(.applicationName) online agents"
            ],
            shortTitle: "HELM Online Agents",
            systemImageName: "person.3"
        )
        
        AppShortcut(
            intent: RunHAFConMonIntent(),
            phrases: [
                "Run \(.applicationName) continuous monitoring"
            ],
            shortTitle: "HELM Run ConMon",
            systemImageName: "play.circle"
        )
        
        AppShortcut(
            intent: EnableOperatorHoldIntent(),
            phrases: [
                "Place \(.applicationName) on operator hold"
            ],
            shortTitle: "HELM Enable Operator Hold",
            systemImageName: "pause.circle"
        )
    }
}
