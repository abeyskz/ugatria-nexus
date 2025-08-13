import SwiftUI
import AVFoundation

// MARK: - PAD値構造体
struct PADValues {
    let pleasure: Double    // 快-不快 (-5 ~ +5)
    let arousal: Double     // 覚醒-沈静 (-5 ~ +5)
    let dominance: Double   // 支配-服従 (-5 ~ +5)
    
    var description: String {
        return "P:\(String(format: "%.1f", pleasure)) A:\(String(format: "%.1f", arousal)) D:\(String(format: "%.1f", dominance))"
    }
}

// MARK: - メインビュー
struct ContentView: View {
    @StateObject private var audioRecorder = AudioRecorder()
    
    var body: some View {
        VStack(spacing: 30) {
            // ポコリタイトル
            VStack {
                Text("🌤️ ポコリ")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Listen Proto + PAD Analysis")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // 録音ボタンエリア
            VStack(spacing: 20) {
                // 録音状態表示
                Text(audioRecorder.isRecording ? "🎤 録音中..." : "🎤 準備完了")
                    .font(.title2)
                    .foregroundColor(audioRecorder.isRecording ? .red : .blue)
                
                // 録音ボタン
                Button(action: {
                    if audioRecorder.isRecording {
                        audioRecorder.stopRecording()
                    } else {
                        audioRecorder.startRecording()
                    }
                }) {
                    ZStack {
                        Circle()
                            .fill(audioRecorder.isRecording ? Color.red : Color.blue)
                            .frame(width: 120, height: 120)
                        
                        Image(systemName: audioRecorder.isRecording ? "stop.fill" : "mic.fill")
                            .font(.system(size: 40))
                            .foregroundColor(.white)
                    }
                }
                .scaleEffect(audioRecorder.isRecording ? 1.1 : 1.0)
                .animation(.easeInOut(duration: 0.1), value: audioRecorder.isRecording)
            }
            
            Spacer()
            
            // 認識結果表示エリア
            VStack(alignment: .leading, spacing: 15) {
                Text("認識結果:")
                    .font(.headline)
                
                ScrollView {
                    Text(audioRecorder.transcriptionResult.isEmpty ?
                         "音声を録音してください" : audioRecorder.transcriptionResult)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(10)
                }
                .frame(height: 100)
                
                // PAD分析結果表示エリア
                if audioRecorder.padValues != nil || audioRecorder.isAnalyzingPAD {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("PAD感情分析:")
                            .font(.headline)
                            .foregroundColor(.purple)
                        
                        if audioRecorder.isAnalyzingPAD {
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.8)
                                Text("感情分析中...")
                                    .font(.body)
                                    .foregroundColor(.secondary)
                            }
                            .padding()
                            .background(Color.purple.opacity(0.1))
                            .cornerRadius(10)
                        } else if let pad = audioRecorder.padValues {
                            VStack(spacing: 8) {
                                HStack {
                                    Text("Pleasure (快-不快):")
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                    Spacer()
                                    Text(String(format: "%.1f", pad.pleasure))
                                        .font(.body)
                                        .foregroundColor(pad.pleasure > 0 ? .green : .red)
                                }
                                
                                HStack {
                                    Text("Arousal (覚醒-沈静):")
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                    Spacer()
                                    Text(String(format: "%.1f", pad.arousal))
                                        .font(.body)
                                        .foregroundColor(pad.arousal > 0 ? .orange : .blue)
                                }
                                
                                HStack {
                                    Text("Dominance (支配-服従):")
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                    Spacer()
                                    Text(String(format: "%.1f", pad.dominance))
                                        .font(.body)
                                        .foregroundColor(pad.dominance > 0 ? .purple : .gray)
                                }
                                
                                Text("感情語: \(audioRecorder.emotionLabel)")
                                    .font(.body)
                                    .foregroundColor(.primary)
                                    .padding(.top, 5)
                            }
                            .padding()
                            .background(Color.purple.opacity(0.1))
                            .cornerRadius(10)
                        }
                    }
                }
            }
            .padding(.horizontal)
            
            // ステータス表示
            if !audioRecorder.statusMessage.isEmpty {
                Text(audioRecorder.statusMessage)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal)
            }
            
            Spacer()
        }
        .padding()
        .onAppear {
            audioRecorder.requestPermission()
        }
    }
}

// MARK: - AudioRecorder クラス
class AudioRecorder: ObservableObject {
    @Published var isRecording = false
    @Published var transcriptionResult = ""
    @Published var statusMessage = ""
    @Published var padValues: PADValues? = nil
    @Published var emotionLabel = ""
    @Published var isAnalyzingPAD = false
    
    private var whisperStartTime: Date?
    private var padStartTime: Date?
    
    private var audioRecorder: AVAudioRecorder?
    private var audioSession = AVAudioSession.sharedInstance()
    
    // 録音ファイルのURL
    private var recordingURL: URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                   in: .userDomainMask)[0]
        return documentsPath.appendingPathComponent("recording.m4a")
    }
    
    // MARK: - 権限要求
    func requestPermission() {
        audioSession.requestRecordPermission { granted in
            DispatchQueue.main.async {
                if granted {
                    self.statusMessage = "マイク権限が許可されました"
                } else {
                    self.statusMessage = "マイク権限が必要です"
                }
            }
        }
    }
    
    // MARK: - 録音開始
    func startRecording() {
        do {
            // オーディオセッション設定
            try audioSession.setCategory(.record, mode: .default)
            try audioSession.setActive(true)
            
            // 録音設定
            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 16000,  // Whisper API推奨
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ]
            
            // 録音開始
            audioRecorder = try AVAudioRecorder(url: recordingURL, settings: settings)
            audioRecorder?.record()
            
            isRecording = true
            statusMessage = "録音開始"
            
        } catch {
            statusMessage = "録音開始エラー: \(error.localizedDescription)"
        }
    }
    
    // MARK: - 録音停止
    func stopRecording() {
        audioRecorder?.stop()
        isRecording = false
        statusMessage = "録音停止 - Whisper API送信準備中..."
        
        // 録音停止後、Whisper APIに送信
        sendToWhisperAPI()
    }
    
    // MARK: - Whisper API送信
    private func sendToWhisperAPI() {
        guard FileManager.default.fileExists(atPath: recordingURL.path) else {
            statusMessage = "録音ファイルが見つかりません"
            return
        }
        
        // 処理時間測定開始
        whisperStartTime = Date()
        statusMessage = "Whisper APIに送信中..."
        print("🎙️ Whisper API処理開始: \(Date())")
        
        // OpenAI API設定
        let apiKey = "[OPENAI_API_KEY_PLACEHOLDER]"
        let url = URL(string: "https://api.openai.com/v1/audio/transcriptions")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        
        // マルチパートフォームデータ作成
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var data = Data()
        
        // model パラメータ
        data.append("--\(boundary)\r\n".data(using: .utf8)!)
        data.append("Content-Disposition: form-data; name=\"model\"\r\n\r\n".data(using: .utf8)!)
        data.append("whisper-1\r\n".data(using: .utf8)!)
        
        // language パラメータ（日本語指定）
        data.append("--\(boundary)\r\n".data(using: .utf8)!)
        data.append("Content-Disposition: form-data; name=\"language\"\r\n\r\n".data(using: .utf8)!)
        data.append("ja\r\n".data(using: .utf8)!)
        
        // ファイルデータ
        do {
            let audioData = try Data(contentsOf: recordingURL)
            data.append("--\(boundary)\r\n".data(using: .utf8)!)
            data.append("Content-Disposition: form-data; name=\"file\"; filename=\"recording.m4a\"\r\n".data(using: .utf8)!)
            data.append("Content-Type: audio/mp4\r\n\r\n".data(using: .utf8)!)
            data.append(audioData)
            data.append("\r\n".data(using: .utf8)!)
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "ファイル読み込みエラー: \(error.localizedDescription)"
            }
            return
        }
        
        // 終端
        data.append("--\(boundary)--\r\n".data(using: .utf8)!)
        
        request.httpBody = data
        
        // API送信
        URLSession.shared.dataTask(with: request) { [weak self] responseData, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                if let error = error {
                    self.statusMessage = "API通信エラー: \(error.localizedDescription)"
                    return
                }
                
                guard let httpResponse = response as? HTTPURLResponse else {
                    self.statusMessage = "無効なレスポンス"
                    return
                }
                
                guard let data = responseData else {
                    self.statusMessage = "レスポンスデータなし"
                    return
                }
                
                if httpResponse.statusCode == 200 {
                    // 成功レスポンス解析
                    self.parseWhisperResponse(data)
                } else {
                    // エラーレスポンス処理
                    if let errorMessage = String(data: data, encoding: .utf8) {
                        self.statusMessage = "API エラー (\(httpResponse.statusCode)): \(errorMessage)"
                    } else {
                        self.statusMessage = "API エラー: HTTP \(httpResponse.statusCode)"
                    }
                }
            }
        }.resume()
    }
    
    // MARK: - Whisper レスポンス解析
    private func parseWhisperResponse(_ data: Data) {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let text = json["text"] as? String {
                transcriptionResult = text
                
                // 処理時間測定終了
                if let startTime = whisperStartTime {
                    let processingTime = Date().timeIntervalSince(startTime)
                    print("🎙️ Whisper API処理完了: \(String(format: "%.2f", processingTime))秒 - 結果: \"\(text)\"")
                }
                
                // 📊 PAD分析実行
                analyzePAD(text: text)
                
            } else {
                statusMessage = "レスポンス解析エラー"
            }
        } catch {
            statusMessage = "JSON解析エラー: \(error.localizedDescription)"
        }
    }
    
    // MARK: - PAD分析API呼び出し
    private func analyzePAD(text: String) {
        guard !text.isEmpty else {
            padValues = PADValues(pleasure: 0, arousal: 0, dominance: 0)
            emotionLabel = "中性"
            return
        }
        
        // UI更新：分析開始
        isAnalyzingPAD = true
        statusMessage = "感情分析中..."
        
        // 処理時間測定開始
        padStartTime = Date()
        print("📊 PAD分析開始: \"\(text)\"")
        
        // OpenAI Chat Completion API設定
        let apiKey = "[OPENAI_API_KEY_PLACEHOLDER]"
        let url = URL(string: "https://api.openai.com/v1/chat/completions")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // PAD分析プロンプト
        let prompt = """
あなたは人間の感情を分析するアシスタントです。以下の発言から、感情状態をPleasure（快-不快）、Arousal（覚醒-沈静）、Dominance（支配-服従）の3軸で数値化してください。
各スコアは -5（低い）〜+5（高い）の範囲とします。

【発言】："\(text)"

必ずJSON形式で以下の通りに出力してください：
{
  "pleasure": [数値],
  "arousal": [数値],
  "dominance": [数値],
  "emotion_label": "[感情語]"
}

感情語は「とても嬉しそう」「やや沈んでる」「穏やか」「興奮している」「落ち着いている」などの日本語で表現してください。
"""
        
        // リクエストボディ作成
        let requestBody: [String: Any] = [
            "model": "gpt-4",
            "messages": [
                [
                    "role": "user",
                    "content": prompt
                ]
            ],
            "max_tokens": 150,
            "temperature": 0.3
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "リクエスト作成エラー: \(error.localizedDescription)"
                self.isAnalyzingPAD = false
            }
            return
        }
        
        // API送信
        URLSession.shared.dataTask(with: request) { [weak self] responseData, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                self.isAnalyzingPAD = false
                
                if let error = error {
                    self.statusMessage = "PAD分析API通信エラー: \(error.localizedDescription)"
                    return
                }
                
                guard let httpResponse = response as? HTTPURLResponse else {
                    self.statusMessage = "無効なレスポンス"
                    return
                }
                
                guard let data = responseData else {
                    self.statusMessage = "レスポンスデータなし"
                    return
                }
                
                if httpResponse.statusCode == 200 {
                    // 成功レスポンス解析
                    self.parsePADResponse(data)
                } else {
                    // エラーレスポンス処理
                    if let errorMessage = String(data: data, encoding: .utf8) {
                        self.statusMessage = "PAD分析API エラー (\(httpResponse.statusCode)): \(errorMessage)"
                    } else {
                        self.statusMessage = "PAD分析API エラー: HTTP \(httpResponse.statusCode)"
                    }
                }
            }
        }.resume()
    }
    
    // MARK: - PAD分析レスポンス解析
    private func parsePADResponse(_ data: Data) {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let choices = json["choices"] as? [[String: Any]],
               let firstChoice = choices.first,
               let message = firstChoice["message"] as? [String: Any],
               let content = message["content"] as? String {
                
                // JSON部分を抽出
                let cleanedContent = content.trimmingCharacters(in: .whitespacesAndNewlines)
                
                if let contentData = cleanedContent.data(using: .utf8),
                   let padJson = try JSONSerialization.jsonObject(with: contentData) as? [String: Any] {
                    
                    let pleasure = padJson["pleasure"] as? Double ?? 0.0
                    let arousal = padJson["arousal"] as? Double ?? 0.0
                    let dominance = padJson["dominance"] as? Double ?? 0.0
                    let emotion = padJson["emotion_label"] as? String ?? "不明"
                    
                    // PAD値設定
                    padValues = PADValues(pleasure: pleasure, arousal: arousal, dominance: dominance)
                    emotionLabel = emotion
                    
                    // 処理時間測定終了
                    if let startTime = padStartTime {
                        let processingTime = Date().timeIntervalSince(startTime)
                        print("📊 PAD分析完了: \(String(format: "%.2f", processingTime))秒 - P:\(pleasure) A:\(arousal) D:\(dominance) - \(emotion)")
                    }
                    
                    statusMessage = "音声認識・感情分析完了！"
                    
                } else {
                    print("⚠️ JSON解析エラー: \(cleanedContent)")
                    // フォールバック: デフォルト値設定
                    padValues = PADValues(pleasure: 0, arousal: 0, dominance: 0)
                    emotionLabel = "分析困難"
                    statusMessage = "感情分析完了（デフォルト値）"
                }
                
            } else {
                statusMessage = "PAD分析レスポンス解析エラー"
            }
        } catch {
            statusMessage = "PAD分析JSON解析エラー: \(error.localizedDescription)"
        }
    }
}

// MARK: - プレビュー
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
