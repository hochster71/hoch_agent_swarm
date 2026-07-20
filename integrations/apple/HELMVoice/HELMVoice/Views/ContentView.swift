import SwiftUI

struct ContentView: View {
    @StateObject private var client = HELMVoiceClient()
    @State private var voiceInputText = ""
    @State private var outputMessage = ""
    @State private var isRecording = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                ConnectionStatusView(isConnected: client.isConnected)
                
                Spacer()
                
                // Voice / text command input
                VStack(spacing: 12) {
                    TextField("Enter voice command transcript...", text: $voiceInputText)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .padding(.horizontal)
                    
                    HStack(spacing: 20) {
                        Button(action: toggleRecording) {
                            HStack {
                                Image(systemName: isRecording ? "stop.fill" : "mic.fill")
                                Text(isRecording ? "Stop Recording" : "Push to Talk")
                            }
                            .padding()
                            .foregroundColor(.white)
                            .background(isRecording ? Color.red : Color.blue)
                            .cornerRadius(10)
                        }
                        
                        Button(action: submitCommand) {
                            Text("Submit Command")
                                .padding()
                                .foregroundColor(.white)
                                .background(Color.green)
                                .cornerRadius(10)
                        }
                    }
                }
                
                // Output console
                VStack(alignment: .leading, spacing: 8) {
                    Text("Gateway Output Console:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text(outputMessage.isEmpty ? "Idle" : outputMessage)
                        .font(.body)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(8)
                }
                .padding(.horizontal)
                
                Spacer()
                
                NavigationLink(destination: VoiceEventHistoryView()) {
                    Text("View Auditable Events History")
                        .font(.footnote)
                        .foregroundColor(.blue)
                }
                .padding(.bottom)
            }
            .navigationTitle("HELM Voice Companion")
        }
    }
    
    private func toggleRecording() {
        isRecording.toggle()
        if isRecording {
            voiceInputText = ""
            outputMessage = "Listening..."
        } else {
            voiceInputText = "status summary"
            outputMessage = "Recording completed."
        }
    }
    
    private func submitCommand() {
        guard !voiceInputText.isEmpty else { return }
        outputMessage = "Sending request to HELM Gateway..."
        
        client.sendVoiceRequest(intent: "helm.status.summary", utterance: voiceInputText) { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let response):
                    outputMessage = response.speechResponse
                    client.lastResponse = response.speechResponse
                    client.isConnected = true
                case .failure(let error):
                    outputMessage = "Error: \(error.localizedDescription)"
                    client.isConnected = false
                }
            }
        }
    }
}
