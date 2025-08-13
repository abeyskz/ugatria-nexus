//
//  AudioRecorder.swift
//  PocoriConversation
//
//  誤検出軽減＋AudioSession修正版
//

import SwiftUI
import AVFoundation

// MARK: - VAD機能付きAudioRecorder クラス
class AudioRecorder: ObservableObject {
    @Published var isListening = false      // 常時監視状態
    @Published var isRecording = false      // 実際の録音状態
    @Published var isThinking = false      // 実際の思考中状態
    @Published var transcriptionResult = ""
    @Published var statusMessage = ""
    
    private var whisperStartTime: Date?
    
    // 🔧 VAD設定（誤検出軽減）
    private var volumeThreshold: Float = -17.0        // -20.0 → -17.0 (誤検出軽減)
    private var silenceDuration: TimeInterval = 2.0   // 無音検出時間（秒）
    private var monitoringInterval: TimeInterval = 0.08 // 0.05 → 0.08 (適度な監視間隔)
    
    // タイマーとカウンター
    private var silenceTimer: Timer?
    private var monitoringTimer: Timer?
    private var lastSoundTime: Date?
    
    // 録音関連
    private var audioRecorder: AVAudioRecorder?        // 実際の録音用
    private var monitoringRecorder: AVAudioRecorder?   // 監視用
    private var audioSession = AVAudioSession.sharedInstance()
    
    // 録音ファイルのURL
    private var recordingURL: URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                   in: .userDomainMask)[0]
        return documentsPath.appendingPathComponent("recording.m4a")
    }
    
    // 監視用ファイルのURL（実際は使わないが必要）
    private var monitoringURL: URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory,
                                                   in: .userDomainMask)[0]
        return documentsPath.appendingPathComponent("monitoring.m4a")
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
    
    // MARK: - 常時音声監視開始
    func startListening() {
        do {
            // 🔧 AudioSession設定改良（オプション削除）
            try audioSession.setCategory(.record, mode: .default)
            try audioSession.setActive(true)
            
            // 監視用録音設定（軽量設定）
            let monitoringSettings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 16000,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.low.rawValue  // 軽量設定
            ]
            
            // 監視用録音開始
            monitoringRecorder = try AVAudioRecorder(url: monitoringURL, settings: monitoringSettings)
            monitoringRecorder?.isMeteringEnabled = true  // 音量測定有効
            monitoringRecorder?.record()
            
            isListening = true
            statusMessage = "音声監視中..."
            print("🎙️ VAD監視開始（バランス設定：-17.0dB）")
            
            // 音量監視ループ開始
            startMonitoringLoop()
            
        } catch {
            statusMessage = "監視開始エラー: \(error.localizedDescription)"
            print("❌ VAD監視開始エラー: \(error)")
        }
    }
    
    // MARK: - 常時音声監視停止（AudioSession修正版）
    func stopListening() {
        monitoringTimer?.invalidate()
        silenceTimer?.invalidate()
        monitoringRecorder?.stop()
        
        // 🔧 AVAudioRecorderインスタンス完全破棄
        monitoringRecorder = nil
        audioRecorder?.stop()
        audioRecorder = nil
        
        isListening = false
        isRecording = false
        statusMessage = "監視停止"
        print("🎙️ VAD監視停止")
        
        // 🚀 AudioSession問題修正（確実な切り替え）
        do {
            // Step 1: 一旦非アクティブにする
            try audioSession.setActive(false)
            print("🔊 AudioSession一時非アクティブ化完了")
            
            // Step 2: カテゴリを.playbackに切り替え
            try audioSession.setCategory(.playback, mode: .default)
            
            // Step 3: 再アクティブ化
            try audioSession.setActive(true)
            print("🔊 AudioSessionを.playbackに切り替え完了（修正版）")
            
        } catch {
            print("❌ AudioSession切り替え失敗: \(error)")
            
            // 🔧 フォールバック処理
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                do {
                    try self.audioSession.setCategory(.playback, mode: .default)
                    try self.audioSession.setActive(true)
                    print("🔊 AudioSessionフォールバック成功")
                } catch {
                    print("❌ AudioSessionフォールバックも失敗: \(error)")
                }
            }
        }
    }
    
    // MARK: - 音量監視ループ
    private func startMonitoringLoop() {
        monitoringTimer = Timer.scheduledTimer(withTimeInterval: monitoringInterval, repeats: true) { [weak self] _ in
            self?.monitorAudioLevel()
        }
    }
    
    // MARK: - 音量レベル監視（バランス調整版）
    private func monitorAudioLevel() {
        guard let recorder = monitoringRecorder, isListening, !isThinking else { return }
        
        recorder.updateMeters()
        let currentVolume = recorder.averagePower(forChannel: 0)
        
        // 🔧 音声検出時のみデバッグ出力（ノイズ軽減）
        if currentVolume > volumeThreshold {
            print("🔊 音声検出: \(String(format: "%.1f", currentVolume))dB (閾値: \(volumeThreshold)dB)")
        }
        
        if currentVolume > volumeThreshold {
            // 音声検出
            lastSoundTime = Date()
            
            if !isRecording {
                // 録音開始
                autoStartRecording()
            }
            
            // 無音タイマーリセット
            silenceTimer?.invalidate()
            silenceTimer = nil
            
        } else if isRecording {
            // 無音状態で録音中の場合
            if silenceTimer == nil {
                // 無音タイマー開始
                print("⏰ 無音タイマー開始")
                startSilenceTimer()
            }
        }
    }
    
    // MARK: - 無音タイマー開始
    private func startSilenceTimer() {
        silenceTimer = Timer.scheduledTimer(withTimeInterval: silenceDuration, repeats: false) { [weak self] _ in
            print("⏰ 無音タイマー発火 → 録音終了")
            self?.autoStopRecording()
        }
    }
    
    // MARK: - 自動録音開始
    private func autoStartRecording() {
        guard !isRecording else { return }
        
        do {
            // 実際の録音設定（高品質）
            let recordingSettings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 16000,  // Whisper API推奨
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ]
            
            // 録音開始
            audioRecorder = try AVAudioRecorder(url: recordingURL, settings: recordingSettings)
            audioRecorder?.record()
            
            isRecording = true
            statusMessage = "録音中..."
            print("🎙️ 自動録音開始（バランス設定）")
            
        } catch {
            statusMessage = "録音開始エラー: \(error.localizedDescription)"
            print("❌ 自動録音開始エラー: \(error)")
        }
    }
    
    // MARK: - 自動録音終了
    private func autoStopRecording() {
        guard isRecording else { return }
        
        audioRecorder?.stop()
        silenceTimer?.invalidate()
        
        isRecording = false
        statusMessage = "音声処理中..."
        print("🎙️ 自動録音終了")
        
        // 録音停止後、Whisper APIに送信
        sendToWhisperAPI()
    }
    
    // MARK: - Whisper API送信
    private func sendToWhisperAPI() {
        guard FileManager.default.fileExists(atPath: recordingURL.path) else {
            statusMessage = "録音ファイルが見つかりません"
            return
        }
        
        // 録音ファイルサイズチェック
        let fileSize = try? recordingURL.resourceValues(forKeys: [.fileSizeKey]).fileSize
        if let size = fileSize, size < 1000 {  // 1KB未満は無音とみなす
            statusMessage = "音声が検出されませんでした"
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
                statusMessage = "音声認識完了！"
                
                // 処理時間測定終了
                if let startTime = whisperStartTime {
                    let processingTime = Date().timeIntervalSince(startTime)
                    print("🎙️ Whisper API処理完了: \(String(format: "%.2f", processingTime))秒 - 結果: \"\(text)\"")
                }
                
            } else {
                statusMessage = "レスポンス解析エラー"
            }
        } catch {
            statusMessage = "JSON解析エラー: \(error.localizedDescription)"
        }
    }
    
    // MARK: - VAD設定調整（デバッグ用）
    func adjustVADSettings(threshold: Float, silenceDuration: TimeInterval) {
        self.volumeThreshold = threshold
        self.silenceDuration = silenceDuration
        print("🔧 VAD設定変更 - 閾値: \(threshold)dB, 無音時間: \(silenceDuration)秒")
    }
    
    // MARK: - 現在のVAD設定確認
    func printCurrentVADSettings() {
        print("🔧 現在のVAD設定（バランス版）:")
        print("   volumeThreshold: \(volumeThreshold) dB")
        print("   silenceDuration: \(silenceDuration) 秒")
        print("   monitoringInterval: \(monitoringInterval) 秒")
    }
    
    // MARK: - 外部状態制御
    func setThinkingState(_ thinking: Bool) {
        isThinking = thinking
        print("🧠 AudioRecorder.isThinking = \(thinking)")
    }
    
    func pauseListeningForSpeech() {
        print("🎵 音声再生のためマイク一時停止")
        monitoringTimer?.invalidate()
        monitoringRecorder?.stop()
        // isListeningはtrueのまま（一時停止状態）
    }

    func resumeListeningAfterSpeech() {
        print("🎵 音声再生完了、マイク再開")
        if isListening {
            startMonitoringLoop()
        }
    }
}
