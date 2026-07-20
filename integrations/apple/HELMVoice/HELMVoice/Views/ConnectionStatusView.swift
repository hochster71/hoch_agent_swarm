import SwiftUI

struct ConnectionStatusView: View {
    let isConnected: Bool
    
    var body: some View {
        HStack {
            Circle()
                .fill(isConnected ? Color.green : Color.orange)
                .frame(width: 12, height: 12)
            Text(isConnected ? "Gateway Online (Assurance Verified)" : "Gateway Mock/Offline")
                .font(.subheadline)
                .foregroundColor(.primary)
        }
        .padding()
        .background(Color.gray.opacity(0.15))
        .cornerRadius(20)
    }
}
