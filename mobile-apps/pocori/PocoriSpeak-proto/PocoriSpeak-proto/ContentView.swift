import SwiftUI
import AVFoundation

// MARK: - メインビュー
struct ContentView: View {
    @StateObject private var speechManager = SpeechManager()
    @State private var inputText = "こんにちは！私はポコリです。今日はいい天気ですね〜"
    
    var body: some View {
        VStack(spacing: 20) {
            // ヘッダー
            VStack {
                Text("🌤️ ポコリ")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Speak Proto - 音声合成システム")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.top)
            
            Spacer()
            
            // 音声生成エリア
            VStack(spacing: 15) {
                // テキスト入力
                VStack(alignment: .leading) {
                    Text("ポコリに話してもらう内容:")
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    TextEditor(text: $inputText)
                        .frame(minHeight: 100, maxHeight: 150)
                        .padding(8)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(8)
                        .border(Color.gray.opacity(0.3), width: 1)
                }
                
                // 音声生成ボタン
                Button(action: {
                    speechManager.generateSpeech(text: inputText)
                }) {
                    HStack {
                        if speechManager.isGenerating {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                        } else {
                            Image(systemName: "waveform.circle.fill")
                                .font(.title2)
                        }
                        
                        Text(speechManager.isGenerating ? "音声生成中..." : "🌤️ ポコリ音声を生成")
                            .fontWeight(.medium)
                    }
                    .foregroundColor(.white)
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(
                        speechManager.isGenerating || inputText.isEmpty ?
                        Color.gray : Color.blue
                    )
                    .cornerRadius(10)
                }
                .disabled(speechManager.isGenerating || inputText.isEmpty)
                
                // 音声再生コントロール
                if speechManager.hasAudio {
                    VStack(spacing: 10) {
                        Text("🎵 音声準備完了")
                            .font(.subheadline)
                            .foregroundColor(.green)
                        
                        HStack(spacing: 20) {
                            // 再生/停止ボタン
                            Button(action: {
                                if speechManager.isPlaying {
                                    speechManager.stopAudio()
                                } else {
                                    speechManager.playAudio()
                                }
                            }) {
                                HStack {
                                    Image(systemName: speechManager.isPlaying ? "stop.fill" : "play.fill")
                                        .font(.title2)
                                    Text(speechManager.isPlaying ? "停止" : "再生")
                                        .fontWeight(.medium)
                                }
                                .foregroundColor(.white)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 10)
                                .background(speechManager.isPlaying ? Color.red : Color.green)
                                .cornerRadius(8)
                            }
                            
                            // リセットボタン
                            Button(action: {
                                speechManager.resetAudio()
                            }) {
                                HStack {
                                    Image(systemName: "arrow.counterclockwise")
                                    Text("リセット")
                                }
                                .foregroundColor(.blue)
                                .padding(.horizontal, 15)
                                .padding(.vertical, 10)
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(8)
                            }
                        }
                    }
                    .padding()
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(10)
                }
            }
            .padding(.horizontal)
            
            Spacer()
            
            // ステータス表示
            if !speechManager.statusMessage.isEmpty {
                Text(speechManager.statusMessage)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            
            // プリセットテキストボタン
            VStack {
                Text("サンプルテキスト:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(SpeechManager.sampleTexts, id: \.self) { sample in
                            Button(sample) {
                                inputText = sample
                            }
                            .font(.caption)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color.blue.opacity(0.1))
                            .foregroundColor(.blue)
                            .cornerRadius(15)
                        }
                    }
                    .padding(.horizontal)
                }
            }
            .padding(.bottom)
        }
    }
}

// MARK: - 音声管理クラス
class SpeechManager: NSObject, ObservableObject {
    @Published var isGenerating = false
    @Published var isPlaying = false
    @Published var hasAudio = false
    @Published var statusMessage = ""
    // 処理時間測定用
    private var speakStartTime: Date?
    
    private var audioPlayer: AVAudioPlayer?
    
    // サンプルテキスト
    static let sampleTexts = [
        "こんにちは〜ふわふわですね",
        "今日はいいお天気ですね",
        "ほわほわ〜楽しそうです",
        "なるほど〜そうなんですね",
        "ふーん、面白いですね"
    ]
    
    override init() {
        super.init()
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback)
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            statusMessage = "オーディオセッション設定エラー: \(error.localizedDescription)"
        }
    }
    
    // MARK: - OpenAI TTS API呼び出し
    func generateSpeech(text: String) {
        guard !text.isEmpty else { return }
        
        isGenerating = true
        hasAudio = false
        statusMessage = "OpenAI TTS APIで音声を生成中..."
        
        callOpenAITTS(text: text)
    }
    
    private func callOpenAITTS(text: String) {
        // 処理時間測定開始
        speakStartTime = Date()
        print("🔊 Speak API処理開始: \(Date())")
        
        let apiKey = "[OPENAI_API_KEY_PLACEHOLDER]"
        let url = URL(string: "https://api.openai.com/v1/audio/speech")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody: [String: Any] = [
            "model": "tts-1",           // 高速版（tts-1-hdは高品質版）
            "input": text,
            "voice": "nova",           // 中性的・活発な声
            "response_format": "mp3",
            "speed": 1.0               // 1.0が標準速度（0.25〜4.0）
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "リクエスト作成エラー: \(error.localizedDescription)"
                self.isGenerating = false
            }
            return
        }
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                if let error = error {
                    self.statusMessage = "通信エラー: \(error.localizedDescription)"
                    self.isGenerating = false
                    return
                }
                
                guard let data = data else {
                    self.statusMessage = "データ取得エラー"
                    self.isGenerating = false
                    return
                }
                
                // HTTP状態確認
                if let httpResponse = response as? HTTPURLResponse {
                    if httpResponse.statusCode != 200 {
                        self.statusMessage = "API エラー: \(httpResponse.statusCode)"
                        self.isGenerating = false
                        return
                    }
                }
                
                // 音声データをAVAudioPlayerに設定
                self.setupAudioPlayer(with: data)
            }
        }.resume()
    }
    
    private func setupAudioPlayer(with audioData: Data) {
        do {
            audioPlayer = try AVAudioPlayer(data: audioData)
            audioPlayer?.delegate = self
            audioPlayer?.prepareToPlay()
            
            hasAudio = true
            statusMessage = "音声生成完了！再生ボタンを押してください"
            isGenerating = false
            
            // 処理時間測定終了
            if let startTime = speakStartTime {
                let processingTime = Date().timeIntervalSince(startTime)
                print("🔊 Speak API処理完了: \(String(format: "%.2f", processingTime))秒 - 音声生成完了")
            }
            
        } catch {
            statusMessage = "音声プレイヤー設定エラー: \(error.localizedDescription)"
            isGenerating = false
        }
    }
    
    // MARK: - 音声再生制御
    func playAudio() {
        guard let player = audioPlayer else {
            statusMessage = "音声データがありません"
            return
        }
        
        isPlaying = true
        statusMessage = "🎵 ポコリが話しています..."
        player.play()
    }
    
    func stopAudio() {
        audioPlayer?.stop()
        isPlaying = false
        statusMessage = "音声を停止しました"
        
        // 停止後は先頭に戻す
        audioPlayer?.currentTime = 0
    }
    
    func resetAudio() {
        audioPlayer?.stop()
        audioPlayer = nil
        hasAudio = false
        isPlaying = false
        statusMessage = ""
    }
}

// MARK: - AVAudioPlayerDelegate
extension SpeechManager: AVAudioPlayerDelegate {
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async {
            self.isPlaying = false
            self.statusMessage = flag ? "再生完了！" : "再生エラーが発生しました"
        }
    }
    
    func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        DispatchQueue.main.async {
            self.isPlaying = false
            self.statusMessage = "音声デコードエラー: \(error?.localizedDescription ?? "不明なエラー")"
        }
    }
}

// MARK: - プレビュー
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
