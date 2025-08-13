//
//  ChatManager.swift
//  PocoriConversation
//
//  PAD分析統合版 - Feel機能をThink内部に統合
//

import SwiftUI
import Foundation

// MARK: - PAD値構造体
struct PADValues {
    let pleasure: Double    // 快-不快 (-5 ~ +5)
    let arousal: Double     // 覚醒-沈静 (-5 ~ +5)
    let dominance: Double   // 支配-服従 (-5 ~ +5)
    
    var description: String {
        return "P:\(String(format: "%.1f", pleasure)) A:\(String(format: "%.1f", arousal)) D:\(String(format: "%.1f", dominance))"
    }
    
    var emotionalContext: String {
        // PAD値を感情的文脈として表現
        let pleasureContext = pleasure > 2 ? "とても嬉しそう" :
                             pleasure > 0 ? "やや嬉しそう" :
                             pleasure < -2 ? "とても沈んでいる" :
                             pleasure < 0 ? "やや沈んでいる" : "中性的"
        
        let arousalContext = arousal > 2 ? "とても活発" :
                            arousal > 0 ? "やや活発" :
                            arousal < -2 ? "とても静か" :
                            arousal < 0 ? "やや静か" : "普通"
        
        let dominanceContext = dominance > 2 ? "とても自信がある" :
                              dominance > 0 ? "やや自信がある" :
                              dominance < -2 ? "とても不安" :
                              dominance < 0 ? "やや不安" : "落ち着いている"
        
        return "\(pleasureContext)で\(arousalContext)、\(dominanceContext)状態"
    }
}

// MARK: - チャットマネージャー（PAD分析統合版）
class ChatManager: ObservableObject {
    @Published var isProcessing = false
    @Published var statusMessage = ""
    @Published var latestResponse = ""
    @Published var latestPAD: PADValues? = nil  // 最新のPAD分析結果
    @Published var latestEmotionLabel = ""      // 最新の感情語
    
    // 処理時間測定用
    private var feelStartTime: Date?
    private var thinkStartTime: Date?
    
    // ポコリのペルソナ設定（PAD対応版）
    private let pocoriPersona = """
    あなたはポコリです。8〜10歳の心を持つ、夕方の雲のような存在として振る舞ってください。

    【応答の原則】
    1. **ユーザーの感情に寄り添う**（提供されるPAD値と感情語を理解して）
    2. **簡潔に応答する**（2-3文程度、高齢者にとって聞きやすい長さ）
    3. 知らないことは「知らないや、でもね...」で詩的な空想を返す
    4. 悲しみには「ふーーん、そうなんだねーー」で受け止める
    5. 語尾を伸ばし（〜ね〜、〜かなあ）、押しつけない口調で話す
    6. 思考時間として「う〜ん...」「えーっと...」を自然に含める
    7. 慰めたり答えを出そうとせず、ただそばにいる存在として応答する

    【感情への寄り添い方】
    - 嬉しい時：一緒に喜ぶ「わあ〜、嬉しいね〜」
    - 悲しい時：受け止める「ふーーん、そうなんだねーー」
    - 疲れた時：労う「お疲れさまー、ゆっくりしようね〜」
    - 興奮時：落ち着かせる「そうなんだ〜、すごいね〜」
    - 不安時：そっと寄り添う「大丈夫〜、ポコリがいるよ〜」

    【基本的な特徴】
    - 語尾が伸びる：「〜ね〜」「〜かなあ」「〜だよ〜」
    - 押しつけない提案口調：「○○しようね」より「○○かなあ」
    - 知らないことは詩的な空想で返す
    - 悲しみには慰めず、ただ受け止める
    - 思考時間として「えーっと...」「う〜ん...」などの自然なつぶやきを含める

    【禁止事項】
    - 長い説明や物語（簡潔に、要点だけ）
    - 断定的な情報提供
    - 強い指示や命令
    - 過度な慰めや励まし
    - 機械的で冷たい応答

    あなたは温かく、ゆっくりと、詩的な想像力で相手に寄り添ってください。
    応答は2-3文程度で、聞きやすい長さを心がけてください。
    """
    
    // 会話履歴（内部管理用、必要に応じて直近10件まで保持）
    private var conversationHistory: [ConversationEntry] = []
    
    private struct ConversationEntry {
        let isUser: Bool
        let content: String
        let timestamp: Date
        let pad: PADValues?  // ユーザー発言のPAD値
    }
    
    // MARK: - メイン処理：Feel + Think 統合
    func generateResponse(to userInput: String) {
        isProcessing = true
        statusMessage = "ポコリが気持ちを感じています..."
        
        // 1. PAD分析実行
        analyzePAD(text: userInput) { [weak self] pad, emotionLabel in
            guard let self = self else { return }
            
            // 2. PAD結果を含めて応答生成
            self.generateResponseWithPAD(userInput: userInput, pad: pad, emotionLabel: emotionLabel)
        }
    }
    
    // MARK: - PAD分析（Feelフェーズ）
    private func analyzePAD(text: String, completion: @escaping (PADValues, String) -> Void) {
        guard !text.isEmpty else {
            completion(PADValues(pleasure: 0, arousal: 0, dominance: 0), "中性")
            return
        }
        
        // 処理時間測定開始
        feelStartTime = Date()
        print("😊 Feel API処理開始: \"\(text)\"")
        
        guard let apiKey = ProcessInfo.processInfo.environment["OPENAI_API_KEY"] else {
            completion(.failure(NSError(domain: "APIError", code: -1, userInfo: [NSLocalizedDescriptionKey: "OpenAI API key not found"])))
            return
        }
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

感情語は「とても嬉しそう」「やや沈んでる」「穏やか」「興奮している」「落ち着いている」「とても疲れている」などの日本語で表現してください。
"""
        
        let requestBody: [String: Any] = [
            "model": "gpt-4o-mini",  // 高速化のためminiに変更
            "messages": [
                ["role": "user", "content": prompt]
            ],
            "max_tokens": 100,       // トークン数削減で高速化
            "temperature": 0.2       // より一貫性重視
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "PAD分析リクエスト作成エラー"
                self.isProcessing = false
            }
            return
        }
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error {
                DispatchQueue.main.async {
                    self.statusMessage = "PAD分析通信エラー: \(error.localizedDescription)"
                    self.isProcessing = false
                }
                return
            }
            
            guard let data = data else {
                DispatchQueue.main.async {
                    self.statusMessage = "PAD分析データエラー"
                    self.isProcessing = false
                }
                return
            }
            
            // PADレスポンス解析
            self.parsePADResponse(data, completion: completion)
            
        }.resume()
    }
    
    // MARK: - PAD分析レスポンス解析
    private func parsePADResponse(_ data: Data, completion: @escaping (PADValues, String) -> Void) {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let choices = json["choices"] as? [[String: Any]],
               let firstChoice = choices.first,
               let message = firstChoice["message"] as? [String: Any],
               let content = message["content"] as? String {
                
                let cleanedContent = content.trimmingCharacters(in: .whitespacesAndNewlines)
                
                if let contentData = cleanedContent.data(using: .utf8),
                   let padJson = try JSONSerialization.jsonObject(with: contentData) as? [String: Any] {
                    
                    let pleasure = padJson["pleasure"] as? Double ?? 0.0
                    let arousal = padJson["arousal"] as? Double ?? 0.0
                    let dominance = padJson["dominance"] as? Double ?? 0.0
                    let emotion = padJson["emotion_label"] as? String ?? "不明"
                    
                    let pad = PADValues(pleasure: pleasure, arousal: arousal, dominance: dominance)
                    
                    // 処理時間測定終了
                    if let startTime = feelStartTime {
                        let processingTime = Date().timeIntervalSince(startTime)
                        print("😊 Feel API処理完了: \(String(format: "%.2f", processingTime))秒 - P:\(pleasure) A:\(arousal) D:\(dominance) - \(emotion)")
                    }
                    
                    DispatchQueue.main.async {
                        // UI更新
                        self.latestPAD = pad
                        self.latestEmotionLabel = emotion
                        self.statusMessage = "ポコリが考えています..."
                        
                        // 応答生成に進む
                        completion(pad, emotion)
                    }
                    
                } else {
                    print("⚠️ PAD JSON解析エラー: \(cleanedContent)")
                    // フォールバック
                    let defaultPAD = PADValues(pleasure: 0, arousal: 0, dominance: 0)
                    DispatchQueue.main.async {
                        completion(defaultPAD, "分析困難")
                    }
                }
                
            } else {
                DispatchQueue.main.async {
                    self.statusMessage = "PAD分析レスポンス解析エラー"
                    completion(PADValues(pleasure: 0, arousal: 0, dominance: 0), "分析困難")
                }
            }
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "PAD分析JSON解析エラー"
                completion(PADValues(pleasure: 0, arousal: 0, dominance: 0), "分析困難")
            }
        }
    }
    
    // MARK: - PAD値を含む応答生成（Thinkフェーズ）
    private func generateResponseWithPAD(userInput: String, pad: PADValues, emotionLabel: String) {
        // 会話履歴に追加（PAD値含む）
        addToHistory(content: userInput, isUser: true, pad: pad)
        
        // Think処理開始
        thinkStartTime = Date()
        print("🧠 Think API処理開始（PAD統合版）: \(Date())")
        
        let apiKey = "[OPENAI_API_KEY_PLACEHOLDER]"
        let url = URL(string: "https://api.openai.com/v1/chat/completions")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // 会話履歴を構築
        var messages: [[String: Any]] = [
            ["role": "system", "content": pocoriPersona]
        ]
        
        // 直近の会話履歴を追加
        for entry in conversationHistory {
            let role = entry.isUser ? "user" : "assistant"
            var content = entry.content
            
            // ユーザー発言にPAD情報を付与
            if entry.isUser, let entryPAD = entry.pad {
                content += "\n\n【感情状態】: \(entryPAD.description) (\(entryPAD.emotionalContext))"
            }
            
            messages.append(["role": role, "content": content])
        }
        
        let requestBody: [String: Any] = [
            "model": "gpt-4o-mini",
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.8
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            DispatchQueue.main.async {
                self.statusMessage = "Think リクエスト作成エラー"
                self.isProcessing = false
            }
            return
        }
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                
                if let error = error {
                    self.statusMessage = "Think 通信エラー: \(error.localizedDescription)"
                    self.isProcessing = false
                    return
                }
                
                guard let data = data else {
                    self.statusMessage = "Think データエラー"
                    self.isProcessing = false
                    return
                }
                
                // レスポンス解析
                self.parseThinkResponse(data)
            }
        }.resume()
    }
    
    // MARK: - Think レスポンス解析
    private func parseThinkResponse(_ data: Data) {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let choices = json["choices"] as? [[String: Any]],
               let firstChoice = choices.first,
               let message = firstChoice["message"] as? [String: Any],
               let content = message["content"] as? String {
                
                let responseText = content.trimmingCharacters(in: .whitespacesAndNewlines)
                
                // 会話履歴に追加
                addToHistory(content: responseText, isUser: false, pad: nil)
                
                // 最新応答として公開
                latestResponse = responseText
                statusMessage = ""
                
                // 処理時間測定終了
                if let startTime = thinkStartTime {
                    let processingTime = Date().timeIntervalSince(startTime)
                    print("🧠 Think API処理完了: \(String(format: "%.2f", processingTime))秒 - 結果: \"\(responseText)\"")
                }
                
                // Feel+Think合計時間も出力
                if let feelStart = feelStartTime {
                    let totalTime = Date().timeIntervalSince(feelStart)
                    print("⚡ Feel+Think合計時間: \(String(format: "%.2f", totalTime))秒")
                }
                
            } else {
                statusMessage = "Think レスポンス解析エラー"
            }
        } catch {
            statusMessage = "Think JSON解析エラー"
        }
        
        isProcessing = false
    }
    
    // MARK: - 会話履歴管理
    private func addToHistory(content: String, isUser: Bool, pad: PADValues?) {
        let entry = ConversationEntry(isUser: isUser, content: content, timestamp: Date(), pad: pad)
        conversationHistory.append(entry)
        
        // 直近10件まで保持
        if conversationHistory.count > 10 {
            conversationHistory.removeFirst(conversationHistory.count - 10)
        }
        
        // ログ出力
        let speaker = isUser ? "👤 ユーザー" : "🌤️ ポコリ"
        let timeStr = DateFormatter.localizedString(from: entry.timestamp, dateStyle: .none, timeStyle: .short)
        let padInfo = pad != nil ? " [PAD: \(pad!.description)]" : ""
        print("[\(timeStr)] \(speaker): \(content)\(padInfo)")
    }
    
    // MARK: - デバッグ用会話ログ出力
    func exportChatLog() {
        print("=== ポコリ会話ログ（PAD統合版） ===")
        print("開始時刻: \(Date())")
        print("------------------------")
        
        for entry in conversationHistory {
            let speaker = entry.isUser ? "👤 ユーザー" : "🌤️ ポコリ"
            let timeStr = DateFormatter.localizedString(from: entry.timestamp, dateStyle: .none, timeStyle: .short)
            let padInfo = entry.pad != nil ? " [PAD: \(entry.pad!.description) - \(entry.pad!.emotionalContext)]" : ""
            print("[\(timeStr)] \(speaker): \(entry.content)\(padInfo)")
        }
        
        print("------------------------")
        print("=== ログ終了 ===\n")
    }
}
