import SwiftUI

struct VoiceEventHistoryView: View {
    @State private var events: [VoiceEventStub] = [
        VoiceEventStub(id: "VOICE-EVT-1", action: "helm.status.summary", status: "ALLOW", timestamp: "Just Now"),
        VoiceEventStub(id: "VOICE-EVT-2", action: "helm.operator_hold.enable", status: "CONFIRMATION_REQUIRED", timestamp: "5m ago")
    ]
    
    var body: some View {
        List(events) { event in
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(event.id)
                        .font(.caption)
                        .fontDesign(.monospaced)
                    Spacer()
                    Text(event.status)
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(statusColor(event.status))
                        .foregroundColor(.white)
                        .cornerRadius(4)
                }
                
                Text(event.action)
                    .font(.body)
                
                Text(event.timestamp)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .navigationTitle("Event History")
    }
    
    private func statusColor(_ status: String) -> Color {
        switch status {
        case "ALLOW": return Color.green
        case "CONFIRMATION_REQUIRED": return Color.orange
        default: return Color.red
        }
    }
}

struct VoiceEventStub: Identifiable {
    let id: String
    let action: String
    let status: String
    let timestamp: String
}
