//
//  SpeecManager.swift
//  PocoriConversation
//
//  Created by Yoshikazu Abe on 2025/07/03.
//
import SwiftUI
import AVFoundation

// MARK: - 音声管理クラス
class SpeechManager: NSObject, ObservableObject {
    @Published var isGenerating = false
    @Published var isPlaying = false
    @Published var hasAudio = false
    @Published var statusMessage = ""
    // 処理時間測定用
    private var speakStartTime: Date?
    
    private var audioPlayer: AVAudioPlayer?
    
    private var playbackTimer: Timer?
    
    // VoiceVox設定
    //private let voiceVoxBaseURL = "http://develop.ugatria.co.jp/voicevox"
    private let voiceVoxBaseURL = "http://192.168.10.55:50021"
    private let zundimonSpeakerId = 3  // ずんだもん
    
    // サンプルテキスト
    static let sampleTexts = [
        "こんにちは〜なのだ！",
        "今日はいいお天気だっちゃ〜",
        "ほわほわ〜楽しそうなのだ",
        "なるほど〜そうなんだっちゃ",
        "ふーん、面白いのだ〜"
    ]
    
    override init() {
        super.init()
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.setActive(true)
            print("🔊 AudioSession設定完了: category=\(session.category), mode=\(session.mode)")
        } catch {
            statusMessage = "オーディオセッション設定エラー: \(error.localizedDescription)"
            print("❌ AudioSession設定エラー: \(error)")
        }
    }
    
    // MARK: - VoiceVox TTS API呼び出し
    func generateSpeech(text: String) {
        guard !text.isEmpty else { return }
        
        isGenerating = true
        hasAudio = false
        statusMessage = "VoiceVox（ずんだもん）で音声を生成中..."
        
        callVoiceVoxTTS(text: text)
    }
    
    private func callVoiceVoxTTS(text: String) {
        // 処理時間測定開始
        speakStartTime = Date()
        print("🔊 VoiceVox API処理開始: \(Date())")
        
        // Step 1: audio_query作成
        createAudioQuery(text: text) { [weak self] audioQuery in
            guard let self = self, let audioQuery = audioQuery else {
                DispatchQueue.main.async {
                    self?.statusMessage = "audio_query作成エラー"
                    self?.isGenerating = false
                }
                return
            }
            
            // Step 2: synthesis（音声合成）
            self.synthesizeAudio(audioQuery: audioQuery)
        }
    }
    
    private func createAudioQuery(text: String, completion: @escaping (Data?) -> Void) {
        guard let encodedText = text.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) else {
            completion(nil)
            return
        }
        
        let urlString = "\(voiceVoxBaseURL)/audio_query?text=\(encodedText)&speaker=\(zundimonSpeakerId)"
        guard let url = URL(string: urlString) else {
            completion(nil)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        print("🎤 audio_query作成中: \(urlString)")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("❌ audio_query作成エラー: \(error)")
                completion(nil)
                return
            }
            
            guard let data = data else {
                print("❌ audio_queryデータ取得エラー")
                completion(nil)
                return
            }
            
            // HTTP状態確認
            if let httpResponse = response as? HTTPURLResponse {
                print("🎤 audio_query応答: \(httpResponse.statusCode)")
                if httpResponse.statusCode != 200 {
                    print("❌ audio_query APIエラー: \(httpResponse.statusCode)")
                    completion(nil)
                    return
                }
            }
            
            print("✅ audio_query作成成功: \(data.count)バイト")
            completion(data)
        }.resume()
    }
    
    private func synthesizeAudio(audioQuery: Data) {
        let urlString = "\(voiceVoxBaseURL)/synthesis?speaker=\(zundimonSpeakerId)"
        guard let url = URL(string: urlString) else {
            DispatchQueue.main.async {
                self.statusMessage = "synthesis URL作成エラー"
                self.isGenerating = false
            }
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = audioQuery
        
        print("🎵 音声合成中: \(urlString)")
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                if let error = error {
                    self.statusMessage = "synthesis通信エラー: \(error.localizedDescription)"
                    self.isGenerating = false
                    print("❌ synthesis通信エラー: \(error)")
                    return
                }
                
                guard let data = data else {
                    self.statusMessage = "synthesis音声データ取得エラー"
                    self.isGenerating = false
                    print("❌ synthesis音声データ取得エラー")
                    return
                }
                
                // HTTP状態確認
                if let httpResponse = response as? HTTPURLResponse {
                    print("🎵 synthesis応答: \(httpResponse.statusCode)")
                    if httpResponse.statusCode != 200 {
                        self.statusMessage = "synthesis APIエラー: \(httpResponse.statusCode)"
                        self.isGenerating = false
                        print("❌ synthesis APIエラー: \(httpResponse.statusCode)")
                        return
                    }
                }
                
                print("✅ 音声合成成功: \(data.count)バイト")
                // 音声データをAVAudioPlayerに設定
                self.setupAudioPlayer(with: data)
            }
        }.resume()
    }
    
    private func setupAudioPlayer(with audioData: Data) {
        do {
            print("🎵 ずんだもん音声データサイズ: \(audioData.count)バイト")
            audioPlayer = try AVAudioPlayer(data: audioData)
            audioPlayer?.delegate = self
            audioPlayer?.prepareToPlay()
            
            hasAudio = true
            statusMessage = "ずんだもん音声生成完了！再生ボタンを押してください"
            isGenerating = false
            
            // 処理時間測定終了
            if let startTime = speakStartTime {
                let processingTime = Date().timeIntervalSince(startTime)
                print("🔊 VoiceVox API処理完了: \(String(format: "%.2f", processingTime))秒 - ずんだもん音声生成完了")
            }
            
        } catch {
            statusMessage = "音声プレイヤー設定エラー: \(error.localizedDescription)"
            isGenerating = false
            print("❌ 音声プレイヤー設定エラー: \(error)")
        }
    }
    
    // MARK: - 音声再生制御
    func playAudio() {
        guard let player = audioPlayer else {
            print("❌ audioPlayerがnil")
            return
        }
        
        // 再生前にAudioSessionを明示的にアクティブ化
        do {
            try AVAudioSession.sharedInstance().setActive(true)
            print("🔊 AudioSession再アクティブ化成功")
        } catch {
            print("❌ AudioSession再アクティブ化失敗: \(error)")
        }
        
        print("🎵 ずんだもん再生開始 - duration: \(player.duration)秒, volume: \(player.volume)")
        isPlaying = true
        let success = player.play()
        print("🎵 player.play()結果: \(success)")
        
        if !success {
            print("❌ 再生失敗 - prepareToPlay再実行")
            player.prepareToPlay()
            let retrySuccess = player.play()
            print("🎵 リトライ結果: \(retrySuccess)")
        }
        
        // 再生監視タイマー開始（デバッグ用）
        playbackTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] timer in
            guard let self = self, let player = self.audioPlayer else {
                timer.invalidate()
                return
            }
            
            print("🎵 ずんだもん再生状況: isPlaying=\(player.isPlaying), currentTime=\(String(format: "%.1f", player.currentTime))/\(String(format: "%.1f", player.duration))")
            
            // 再生完了チェック
            if !player.isPlaying && player.currentTime >= player.duration {
                print("🎵 ずんだもん再生完了を検出")
                timer.invalidate()
                self.playbackTimer = nil
                DispatchQueue.main.async {
                    self.isPlaying = false
                    self.statusMessage = "ずんだもん再生完了！"
                }
            }
        }
    }

    
    func stopAudio() {
        audioPlayer?.stop()
        isPlaying = false
        statusMessage = "ずんだもん音声を停止しました"
        
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
        print("🎵 ずんだもんaudioPlayerDidFinishPlaying呼び出し - success: \(flag)")
        DispatchQueue.main.async {
            self.isPlaying = false
            self.statusMessage = flag ? "ずんだもん再生完了！" : "ずんだもん再生エラーが発生しました"
            print("🎵 isPlaying = false に設定完了")
        }
    }
    
    func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        DispatchQueue.main.async {
            self.isPlaying = false
            self.statusMessage = "ずんだもん音声デコードエラー: \(error?.localizedDescription ?? "不明なエラー")"
        }
    }
}
