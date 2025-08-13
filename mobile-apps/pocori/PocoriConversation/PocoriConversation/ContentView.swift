//
//  ContentView.swift
//  PocoriConversation
//
//  PAD分析統合対応版
//
import SwiftUI
import AVFAudio

struct ContentView: View {
    @StateObject private var audioRecorder = AudioRecorder()
    @StateObject private var chatManager = ChatManager()
    @StateObject private var speechManager = SpeechManager()
    
    @State private var isExpanded = false
    @State private var conversations: [ConversationItem] = [
        ConversationItem(speaker: .user, text: "おはよう"),
        ConversationItem(speaker: .pocori, text: "おはよう〜！今日はいい天気だね〜")
    ]
    @State private var currentExpression: PocoriExpression = .sleeping
    
    var body: some View {
        ZStack {
            // 夕方の空色グラデーション背景
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(red: 1.0, green: 0.8, blue: 0.6), // 温かいオレンジ
                    Color(red: 1.0, green: 0.7, blue: 0.8), // 淡いピンク
                    Color(red: 0.9, green: 0.8, blue: 1.0), // 薄紫
                    Color(red: 0.8, green: 0.9, blue: 1.0)  // 淡い空色
                ]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
            
            VStack(spacing: 0) {
                // デバッグ状態表示（PAD統合版）
                VStack(spacing: 4) {
                    Text("🔧 Complete System Status (PAD統合版)")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.7))
                    
                    HStack(spacing: 12) {
                        // Listen状態
                        VStack(spacing: 2) {
                            Text("Listen")
                                .font(.caption2)
                                .foregroundColor(.white.opacity(0.6))
                            Text(audioRecorder.isListening ? (audioRecorder.isRecording ? "🎤 録音" : "👂 監視") : "😴 停止")
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.8))
                        }
                        
                        // Feel+Think状態（統合）
                        VStack(spacing: 2) {
                            Text("Feel+Think")
                                .font(.caption2)
                                .foregroundColor(.white.opacity(0.6))
                            Text(chatManager.isProcessing ? "🤔💭 処理中" : "⏸️ 待機")
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.8))
                        }
                        
                        // Speak状態
                        VStack(spacing: 2) {
                            Text("Speak")
                                .font(.caption2)
                                .foregroundColor(.white.opacity(0.6))
                            Text(speechManager.isGenerating ? "🔊 生成中" : (speechManager.isPlaying ? "🎵 再生中" : "⏸️ 待機"))
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.8))
                        }
                        
                        // 表情状態
                        VStack(spacing: 2) {
                            Text("Expression")
                                .font(.caption2)
                                .foregroundColor(.white.opacity(0.6))
                            Text("😊 \(currentExpression.rawValue.replacingOccurrences(of: "pocori_", with: ""))")
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    
                    // PAD分析結果表示（新機能）
                    if let pad = chatManager.latestPAD, !chatManager.latestEmotionLabel.isEmpty {
                        VStack(spacing: 4) {
                            Text("😊 感情分析結果")
                                .font(.caption)
                                .foregroundColor(.yellow.opacity(0.9))
                                .fontWeight(.semibold)
                            
                            HStack(spacing: 8) {
                                // Pleasure
                                VStack(spacing: 1) {
                                    Text("P")
                                        .font(.caption2)
                                        .foregroundColor(.white.opacity(0.6))
                                    Text(String(format: "%.1f", pad.pleasure))
                                        .font(.caption)
                                        .foregroundColor(pad.pleasure > 0 ? .green : .red)
                                        .fontWeight(.medium)
                                }
                                
                                // Arousal
                                VStack(spacing: 1) {
                                    Text("A")
                                        .font(.caption2)
                                        .foregroundColor(.white.opacity(0.6))
                                    Text(String(format: "%.1f", pad.arousal))
                                        .font(.caption)
                                        .foregroundColor(pad.arousal > 0 ? .orange : .blue)
                                        .fontWeight(.medium)
                                }
                                
                                // Dominance
                                VStack(spacing: 1) {
                                    Text("D")
                                        .font(.caption2)
                                        .foregroundColor(.white.opacity(0.6))
                                    Text(String(format: "%.1f", pad.dominance))
                                        .font(.caption)
                                        .foregroundColor(pad.dominance > 0 ? .purple : .gray)
                                        .fontWeight(.medium)
                                }
                                
                                // 感情語
                                Text("「\(chatManager.latestEmotionLabel)」")
                                    .font(.caption)
                                    .foregroundColor(.white.opacity(0.9))
                                    .fontWeight(.medium)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(
                                        Capsule()
                                            .fill(Color.white.opacity(0.2))
                                    )
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.black.opacity(0.2))
                        )
                    }
                    
                    // ステータスメッセージ表示
                    let statusMessage = getCurrentStatusMessage()
                    if !statusMessage.isEmpty {
                        Text("📍 \(statusMessage)")
                            .font(.caption2)
                            .foregroundColor(.white.opacity(0.6))
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.top, 10)
                .padding(.horizontal, 16)
                
                // ポコリ表示領域（メイン）
                PocoriDisplayArea(
                    currentExpression: $currentExpression,
                    latestPAD: chatManager.latestPAD,
                    emotionLabel: chatManager.latestEmotionLabel
                )
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                
                // テキスト表示領域（下部）
                ConversationArea(
                    conversations: conversations,
                    isExpanded: $isExpanded
                )
            }
        }
        .onAppear {
            // アプリ起動時に音声監視開始
            audioRecorder.requestPermission()
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                audioRecorder.startListening()
                currentExpression = .listening
            }
        }
        .onDisappear {
            // アプリ終了時に全システム停止
            audioRecorder.stopListening()
            speechManager.stopAudio()
        }
        // MARK: - Listen状態監視
        .onReceive(audioRecorder.$isListening) { isListening in
            if isListening && !audioRecorder.isRecording && !chatManager.isProcessing && !speechManager.isGenerating {
                currentExpression = .listening
                print("🎯 状態変更: listening")
            } else if !isListening {
                currentExpression = .sleeping
                print("🎯 状態変更: sleeping")
            }
        }
        .onReceive(audioRecorder.$isRecording) { isRecording in
            if isRecording {
                currentExpression = .listening  // 録音中も listening のまま
                print("🎯 状態変更: recording (表情: listening)")
            }
        }
        .onReceive(audioRecorder.$transcriptionResult) { result in
            if !result.isEmpty {
                // Whisper完了 → マイクオフ
                audioRecorder.stopListening()
                print("🎙️ 聞き取り完了 → マイクオフ")
                // 音声認識完了 → thinking状態
                currentExpression = .thinking
                print("🎯 状態変更: thinking (Feel+Think統合処理開始)")
                
                // 会話履歴にユーザー発言追加
                conversations.append(ConversationItem(speaker: .user, text: result))
                
                // ChatManagerでFeel+Think統合処理開始
                chatManager.generateResponse(to: result)
                
                // 音声認識結果をクリア（次の録音のため）
                audioRecorder.transcriptionResult = ""
            }
        }
        // MARK: - Feel+Think統合状態監視
        .onReceive(chatManager.$isProcessing) { isProcessing in
            audioRecorder.setThinkingState(isProcessing)
            print("🎯 ChatManager.isProcessing (Feel+Think統合) = \(isProcessing)")
            
            if isProcessing {
                currentExpression = .thinking
                print("🎯 状態変更: thinking (Feel+Think処理中)")
            } else if !speechManager.isGenerating && !speechManager.isPlaying {
                // Feel+Think完了、かつSpeak処理中でない場合のみlistening復帰を検討
                print("🎯 Feel+Think完了、Speak待機中")
            }
        }
        // MARK: - PAD分析結果監視（新機能）
        .onReceive(chatManager.$latestPAD) { pad in
            if let pad = pad {
                print("😊 PAD分析完了: P:\(pad.pleasure) A:\(pad.arousal) D:\(pad.dominance)")
                print("😊 感情語: \(chatManager.latestEmotionLabel)")
            }
        }
        // MARK: - Think完了監視
        .onReceive(chatManager.$latestResponse) { response in
            if !response.isEmpty {
                print("🎯 Feel+Think統合処理完了: \(response)")
                
                // thinking状態から一旦リセット
                if currentExpression == .thinking {
                    currentExpression = .sleeping  // 音声生成開始前に一瞬リセット
                    print("🎯 状態変更: thinking → sleeping (音声生成準備)")
                }
                
                // 会話履歴にポコリ応答追加
                conversations.append(ConversationItem(speaker: .pocori, text: response))
                
                // 音声合成開始
                speechManager.generateSpeech(text: response)
                
                // ChatManagerの応答をクリア（次回のため）
                chatManager.latestResponse = ""
            }
        }
        // MARK: - Speak状態監視
        .onReceive(speechManager.$hasAudio) { hasAudio in
            if hasAudio && !speechManager.isPlaying {
                // 音声生成完了 → speaking状態 + 自動再生開始
                currentExpression = .speaking
                print("🎵 自動再生開始")
                speechManager.playAudio()
            }
        }
        .onReceive(speechManager.$isPlaying) { isPlaying in
           if !isPlaying && speechManager.hasAudio {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    // AudioSessionを明示的に.recordに戻す
                    do {
                        try AVAudioSession.sharedInstance().setCategory(.record, mode: .default)
                        try AVAudioSession.sharedInstance().setActive(true)
                        print("🔊 AudioSessionを.recordに戻しました")
                    } catch {
                        print("❌ AudioSession切り替え失敗: \(error)")
                    }
                    
                    // 強制的にマイク監視を再開（isListeningの状態に関係なく）
                    audioRecorder.startListening()
                    currentExpression = .listening
                    print("🎙️ 応答完了 → マイク監視強制再開")
                }
                
                speechManager.resetAudio()
            }
        }
    }
    
    // MARK: - 統合ステータスメッセージ
    private func getCurrentStatusMessage() -> String {
        if !audioRecorder.statusMessage.isEmpty {
            return audioRecorder.statusMessage
        } else if !chatManager.statusMessage.isEmpty {
            return chatManager.statusMessage
        } else if !speechManager.statusMessage.isEmpty {
            return speechManager.statusMessage
        }
        return ""
    }
}

// ポコリ表情の種類
enum PocoriExpression: String, CaseIterable {
    case sleeping = "pocori_sleeping"
    case listening = "pocori_listening"
    case thinking = "pocori_thinking"
    case speaking = "pocori_speaking"
    case happy = "pocori_happy"
    case confused = "pocori_confused"
    case angry = "pocori_angry"
    case crying = "pocori_crying"
    case surprised1 = "pocori_surprised"
    case surprised2 = "pocori_surprised2"
}

// ポコリ表示領域（PAD対応版）
struct PocoriDisplayArea: View {
    @Binding var currentExpression: PocoriExpression
    let latestPAD: PADValues?
    let emotionLabel: String
    
    @State private var isFloating = false
    @State private var isRotating = false
    
    var body: some View {
        ZStack {
            // ポコリの画像表示
            Image(currentExpression.rawValue)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 140, height: 140)
                .rotationEffect(.degrees(shouldRotate ? (isRotating ? 360 : 0) : 0))
                .offset(y: isFloating ? -8 : 8)
                .animation(
                    Animation.easeInOut(duration: 2.5).repeatForever(autoreverses: true),
                    value: isFloating
                )
                .animation(
                    shouldRotate ?
                    Animation.linear(duration: 6.0).repeatForever(autoreverses: false) :
                    .easeInOut(duration: 0.3),
                    value: isRotating
                )
                .onAppear {
                    isFloating = true
                }
                .onChange(of: currentExpression) {
                    print("🎭 表情変更: → \(currentExpression)")
                    if currentExpression == .thinking {
                        isRotating = true
                        print("🌀 回転開始: thinking (Feel+Think統合処理)")
                    } else {
                        isRotating = false
                        print("⏹️ 回転停止: \(currentExpression.rawValue)")
                    }
                }
            
            // PAD分析中の表示（オプション）
            if currentExpression == .thinking && !emotionLabel.isEmpty {
                VStack {
                    Spacer()
                    Text("感情を感じています...")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            Capsule()
                                .fill(Color.black.opacity(0.3))
                        )
                        .offset(y: 20)
                }
            }
        }
    }
    
    // 思考中の時だけ回転
    private var shouldRotate: Bool {
        currentExpression == .thinking
    }
}

// 会話表示領域
struct ConversationArea: View {
    let conversations: [ConversationItem]
    @Binding var isExpanded: Bool
    
    var body: some View {
        VStack(spacing: 8) {
            if !isExpanded {
                // 簡潔表示（最新2件のみ）
                CompactConversationView(conversations: Array(conversations.suffix(2)))
            } else {
                // 展開表示（全履歴）
                ExpandedConversationView(conversations: conversations)
            }
            
            // 展開/折りたたみボタン
            Button(action: {
                withAnimation(.easeInOut(duration: 0.3)) {
                    isExpanded.toggle()
                }
            }) {
                HStack {
                    Image(systemName: isExpanded ? "chevron.down" : "chevron.up")
                    Text(isExpanded ? "たたむ" : "ひろげる")
                }
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(.primary.opacity(0.7))
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(
                    Capsule()
                        .fill(Color.white.opacity(0.3))
                        .blur(radius: 10)
                )
            }
            .padding(.bottom, 20)
        }
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color.white.opacity(0.2))
                .blur(radius: 20)
        )
        .padding(.horizontal, 16)
    }
}

// 簡潔表示ビュー
struct CompactConversationView: View {
    let conversations: [ConversationItem]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(conversations, id: \.id) { item in
                HStack(alignment: .top, spacing: 8) {
                    Text(item.speaker == .user ? "👤" : "🌤️")
                        .font(.system(size: 18))
                    
                    Text(item.text)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(.primary.opacity(0.8))
                        .multilineTextAlignment(.leading)
                    
                    Spacer()
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 16)
    }
}

// 展開表示ビュー
struct ExpandedConversationView: View {
    let conversations: [ConversationItem]
    
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 12) {
                ForEach(conversations, id: \.id) { item in
                    HStack(alignment: .top, spacing: 12) {
                        Text(item.speaker == .user ? "👤" : "🌤️")
                            .font(.system(size: 20))
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.text)
                                .font(.system(size: 16, weight: .medium))
                                .foregroundColor(.primary.opacity(0.8))
                                .multilineTextAlignment(.leading)
                            
                            Text(item.timestamp, style: .time)
                                .font(.system(size: 12))
                                .foregroundColor(.secondary.opacity(0.6))
                        }
                        
                        Spacer()
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.white.opacity(0.1))
                    )
                }
            }
            .padding(.vertical, 16)
        }
        .frame(maxHeight: UIScreen.main.bounds.height * 0.5)
    }
}

// データモデル
struct ConversationItem {
    let id = UUID()
    let speaker: Speaker
    let text: String
    let timestamp: Date = Date()
}

enum Speaker {
    case user
    case pocori
}

#Preview {
    ContentView()
}
