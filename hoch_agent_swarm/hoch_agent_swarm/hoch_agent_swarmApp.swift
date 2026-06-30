//
//  hoch_agent_swarmApp.swift
//  hoch_agent_swarm
//
//  Created by Michael Hoch on 6/30/26.
//

import SwiftUI
import CoreData

@main
struct hoch_agent_swarmApp: App {
    let persistenceController = PersistenceController.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.managedObjectContext, persistenceController.container.viewContext)
        }
    }
}
