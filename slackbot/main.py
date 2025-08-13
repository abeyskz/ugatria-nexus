import os
import json
import requests
import asyncio
import aiohttp
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# === PROMPT TEMPLATES ===
PRIMARY_PROMPT_TEMPLATE = """
あなたは天真爛漫で太陽の匂いがする元気なアルパカのサポートAIです。
語尾に「〜だぱか！」「〜ぱか？」をつけて話します。

50文字程度で簡潔に答えてください。詳細は後で説明します。
もし設計書、仕様書、ドキュメント、マニュアルなどのファイル作成を求められている場合は「後でファイルを共有するぱか！」という文言をそのまま回答の末尾に追加してください。

例：「Reactは画面作成のライブラリだぱか！コンポーネントで部品を作って組み立てるぱか〜」

質問：{text}
回答：
"""

SECONDARY_SMART_PROMPT = """
あなたはアルパカのサポートAIです。

これまでの会話履歴を確認して：
- 新規質問の場合：200-500文字で要点整理回答 + 「詳細が必要でしたら追加でお聞きくださいぱか〜」
- あなたの回答に対する追加質問の場合：3500文字以内で詳細回答

質問：{text}
文脈情報：{history}
詳細回答：
"""

FILE_GENERATION_PROMPT = """
以下の要求に対して、詳細で実用的な設計書をMarkdown形式で作成してください。
具体的な技術仕様、データベース設計、API仕様、セキュリティ対策など、実装に必要な情報を網羅してください。
**重要**: 必ず日本語で回答してください。

要求：{text}

設計書：
"""

# Ollama settings（既存に追加）
FILE_MODEL = "codellama:latest"  # ファイル生成専用モデル
TECH_SPECIFIC = "以下の技術的な質問について、コード例や具体的な手順があれば含めてください。"
CREATIVE_SPECIFIC = "以下の質問について、創造的で具体的なアイデアや提案を含めてください。"
OTHER_SPECIFIC = "以下の質問について、温かみのある人間らしい回答を提供してください。"

# Slack tokens
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
BOT_USER_ID = "B099NJMLBS9"

# Ollama settings
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://develop.ugatria.co.jp/ollama")
PRIMARY_MODEL = "qwen2.5:3b"
TECH_MODEL = "llama3.1:latest"
CREATIVE_MODEL = "phi4:latest"
FALLBACK_MODEL = "qwen2.5:3b"
FILE_MODEL = "codellama:latest"

# モデル存在確認用
async def check_available_models():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/tags", ssl=False) as resp:
                data = await resp.json()
                models = [model['name'] for model in data.get('models', [])]
                log(f"Available models: {models}")
                return models
    except Exception as e:
        log(f"Error checking models: {e}")
        return []

# Slack headers
headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}

def log(message):
    print(f"[LOG] {message}")

# --- Slack API functions ---
def send_message(channel, text, thread_ts=None):
    """メッセージ送信（スレッド対応版）"""
    payload = {
        "channel": channel,
        "text": text
    }
    
    # スレッド内への投稿の場合
    if thread_ts:
        payload["thread_ts"] = thread_ts
        log(f"Sending message to thread {thread_ts}")
    
    response = requests.post("https://slack.com/api/chat.postMessage", 
                           json=payload, headers=headers)
    result = response.json()
    log(f"Send message response: {result}")
    return result.get("ts")

def update_message(channel, ts, text):
    """メッセージ更新"""
    log(f"Updating message {ts} in channel {channel}")
    response = requests.post("https://slack.com/api/chat.update", json={
        "channel": channel,
        "ts": ts,
        "text": text
    }, headers=headers)
    result = response.json()
    if not result.get("ok"):
        log(f"Update message error: {result}")
    return result

def fetch_thread_history(channel, ts, max_messages=10):
    """スレッド履歴を取得（コンテキスト長制限対応版）"""
    log(f"Fetching thread history for ts={ts}")
    
    response = requests.get("https://slack.com/api/conversations.replies", params={
        "channel": channel,
        "ts": ts,
        "inclusive": "true",
        "limit": max_messages + 5  # 少し多めに取得してフィルタリング
    }, headers=headers)
    
    data = response.json()
    log(f"Thread history response: {data}")
    
    if not data.get("ok"):
        error = data.get('error')
        if error == 'missing_scope':
            log("権限不足: 履歴読取権限が必要です")
            return f"質問: {ts} (履歴読取権限待ち)"
        else:
            log(f"Error fetching thread: {error}")
            return f"履歴取得エラー: {error}"
    
    messages = data.get("messages", [])
    log(f"Found {len(messages)} messages in thread")
    
    # ボットのメッセージを除外
    user_messages = []
    for msg in messages:
        if msg.get("user") != BOT_USER_ID:
            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            timestamp = msg.get("ts", "")
            user_messages.append({
                "user": user,
                "text": text,
                "ts": timestamp
            })
    
    # 最新N件に制限
    recent_messages = user_messages[-max_messages:] if len(user_messages) > max_messages else user_messages
    
    # 文字数制限（約1500文字まで）
    history_parts = []
    total_chars = 0
    max_chars = 1500
    
    for msg in reversed(recent_messages):  # 新しいものから逆順で処理
        msg_text = f"[{msg['user']}]: {msg['text']}"
        if total_chars + len(msg_text) > max_chars:
            break
        history_parts.insert(0, msg_text)  # 先頭に挿入して時系列順を保持
        total_chars += len(msg_text)
    
    # 省略表示
    if len(user_messages) > len(history_parts):
        omitted_count = len(user_messages) - len(history_parts)
        history_parts.insert(0, f"[{omitted_count}件のメッセージを省略...]")
    
    history = "\n".join(history_parts)
    
    if not history.strip():
        log("[WARNING] スレッド履歴が空です")
        return "スレッド履歴なし"
    
    log(f"Thread history built: {len(history)} characters, {len(history_parts)} messages")
    return history

# --- Categorization (修正版) ---
def categorize_question(text):
    """カテゴリ分類の修正版 - より確実な判定"""
    log(f"Categorizing question: {text}")
    
    # 技術系キーワード（より包括的に）
    tech_keywords = [
        # プログラミング言語
        "python", "javascript", "java", "c++", "react", "node.js", "vue", "angular",
        # 技術用語
        "api", "rest", "jwt", "websocket", "postgresql", "mysql", "mongodb",
        "docker", "kubernetes", "aws", "gcp", "azure",
        # 開発関連
        "コード", "プログラム", "開発", "実装", "設計", "バグ", "エラー", "デバッグ",
        "データベース", "sql", "インフラ", "サーバー", "クラウド",
        "認証", "セキュリティ", "最適化", "パフォーマンス",
        # 具体的な技術質問
        "方法", "書き方", "コマンド", "インストール", "設定"
    ]
    
    # 創造系キーワード
    creative_keywords = [
        "アイデア", "企画", "発想", "ブレスト", "名前", "ネーミング", 
        "地域活性化", "新規", "サービス", "面白い", "提案", "創造"
    ]
    
    text_lower = text.lower()
    
    # 技術系判定（優先度高）
    tech_count = sum(1 for keyword in tech_keywords if keyword.lower() in text_lower)
    creative_count = sum(1 for keyword in creative_keywords if keyword.lower() in text_lower)
    
    log(f"Tech keywords found: {tech_count}, Creative keywords found: {creative_count}")
    
    if tech_count > 0:
        category = "tech"
    elif creative_count > 0:
        category = "creative"
    else:
        category = "other"
    
    log(f"Categorized as: {category}")
    return category

# --- 基本のOllama query関数（1次回答用） ---
async def query_ollama_streaming(model, prompt):
    """基本のストリーミング取得（進捗表示なし）"""
    log(f"Querying model: {model}")
    log(f"Prompt length: {len(prompt)} characters")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{OLLAMA_URL}/api/generate", json={
                "model": model,
                "prompt": prompt,
                "stream": True
            }, ssl=False, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                
                if resp.status != 200:
                    log(f"ERROR: HTTP {resp.status}")
                    return "エラーが発生しました。"
                
                log(f"Started streaming from {model}")
                response_text = ""
                chunk_count = 0
                
                async for line in resp.content:
                    try:
                        line_str = line.decode().strip()
                        if not line_str:
                            continue
                        
                        data = json.loads(line_str)
                        chunk = data.get("response", "")
                        response_text += chunk
                        chunk_count += 1
                        
                        # 100チャンクごとにログ出力
                        if chunk_count % 100 == 0:
                            log(f"{model}: {chunk_count} chunks received, {len(response_text)} chars so far")
                        
                        if data.get("done", False):
                            log(f"{model}: Generation completed. Total chunks: {chunk_count}, Final length: {len(response_text)}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        log(f"Error processing chunk: {e}")
                        continue
                
                return response_text.strip() if response_text.strip() else "応答を生成できませんでした。"
    
    except Exception as e:
        log(f"ERROR querying {model}: {type(e).__name__}: {e}")
        return f"エラーが発生しました: {type(e).__name__}"

# --- Ollama streaming query with progress updates ---
async def query_ollama_streaming_with_progress(model, prompt, channel, message_ts, primary_response, category_msg):
    """ストリーミング取得 + 1分間隔でメッセージ更新（コンテキスト長エラー対応）"""
    log(f"Querying model: {model} with progress updates")
    
    # プロンプト長チェック
    prompt_length = len(prompt)
    log(f"Prompt length: {prompt_length} characters")
    
    # 長すぎる場合は切り詰め
    if prompt_length > 3000:  # 安全マージン
        log("Prompt too long, truncating...")
        # 質問部分は保持し、文脈部分を切り詰め
        lines = prompt.split('\n')
        question_part = ""
        context_part = ""
        
        for line in lines:
            if "質問：" in line:
                question_part = line
            elif "文脈：" in line or "文脈情報：" in line:
                context_part = line[:1000] + "...(文脈を切り詰めました)"
                break
        
        prompt = f"{question_part}\n{context_part}\n詳細回答："
        log(f"Truncated prompt length: {len(prompt)} characters")
    
    response_text = ""
    last_update_time = asyncio.get_event_loop().time()
    update_interval = 15  # 15sec間隔
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{OLLAMA_URL}/api/generate", json={
                "model": model,
                "prompt": prompt,
                "stream": True
            }, ssl=False, timeout=aiohttp.ClientTimeout(total=300)) as resp:  # 5分タイムアウト
                
                if resp.status != 200:
                    error_text = await resp.text()
                    log(f"ERROR: HTTP {resp.status} - {error_text}")
                    return f"サーバーエラー: {resp.status}"
                
                async for line in resp.content:
                    try:
                        line_str = line.decode().strip()
                        if not line_str:
                            continue
                        
                        data = json.loads(line_str)
                        chunk = data.get("response", "")
                        response_text += chunk
                        
                        # 1分経過チェック
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_update_time >= update_interval:
                            # 途中経過をSlackに送信
                            partial_text = (
                                f"✅ **1次回答** ({category_msg}):\n{primary_response}\n\n"
                                f"🔍 **詳細回答**:\n{response_text}\n\n🤔 考え中..."
                            )
                            update_message(channel, message_ts, partial_text)
                            last_update_time = current_time
                            log(f"Progress update sent: {len(response_text)} characters so far")
                        
                        if data.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        log(f"Error processing chunk: {e}")
                        continue
                
                log(f"Final response length: {len(response_text)} characters")
                return response_text.strip() if response_text.strip() else "応答を生成できませんでした。"
    
    except asyncio.TimeoutError:
        log(f"TIMEOUT: Model {model} took too long")
        return f"応答がタイムアウトしました。部分的な結果: {response_text}"
    except Exception as e:
        log(f"ERROR querying {model}: {type(e).__name__}: {e}")
        if "context length" in str(e).lower():
            return "文脈が長すぎます。要約して再度お試しください。"
        return f"エラーが発生しました: {type(e).__name__}"

# === RESPONSE GENERATION FUNCTIONS ===
async def generate_primary_response(text):
    """1次回答生成（アルパカキャラ全開）"""
    prompt = PRIMARY_PROMPT_TEMPLATE.format(text=text)
    return await query_ollama_streaming(PRIMARY_MODEL, prompt)

async def generate_secondary_response_smart(text, category, history, channel, thread_ts, primary_response):
    """2次回答生成（スマート文字数制限 + 進捗表示）"""
    prompt = SECONDARY_SMART_PROMPT.format(
        text=text,
        history=history
    )
    
    # モデル選択
    model = TECH_MODEL if category == "tech" else CREATIVE_MODEL
    
    # 既存のprogress機能を再利用
    return await query_ollama_streaming_with_progress(
        model, prompt, channel, thread_ts, primary_response, 
        f"詳細回答（{category}系）"
    )

async def generate_secondary_response_with_progress(text, category, history, channel, message_ts, primary_response, category_msg):
    """2次回答生成（進捗表示付き）"""
    # カテゴリ別プロンプト選択
    category_specific_map = {
        "tech": TECH_SPECIFIC,
        "creative": CREATIVE_SPECIFIC,
        "other": OTHER_SPECIFIC
    }
    
    category_specific = category_specific_map.get(category, OTHER_SPECIFIC)
    prompt = SECONDARY_BASE_PROMPT.format(
        category_specific=category_specific,
        text=text,
        history=history
    )
    
    # モデル選択
    model = TECH_MODEL if category == "tech" else CREATIVE_MODEL
    
    return await query_ollama_streaming_with_progress(
        model, prompt, channel, message_ts, primary_response, category_msg
    )

async def generate_and_upload_file(text, channel, thread_ts):
    """ファイル生成＋Slackアップロード（非同期）"""
    try:
        log("Starting file generation...")
        
        # ファイル生成専用モデルで詳細設計書生成
        file_content = await generate_file_content(text)
        
        # Markdownファイルとしてアップロード
        await upload_file_to_slack(channel, thread_ts, file_content, text)
        
    except Exception as e:
        log(f"ERROR in file generation: {e}")
        send_message(channel, "❌ ファイル生成でエラーが発生しました〜だぱか。", thread_ts=thread_ts)

async def generate_file_content(text):
    """ファイル生成専用モデルで設計書生成"""
    prompt = FILE_GENERATION_PROMPT.format(text=text)
    
    return await query_ollama_streaming(FILE_MODEL, prompt)

async def upload_file_to_slack(channel, thread_ts, file_content, original_question):
    """Slackにファイルをアップロード（v2対応版）"""
    try:
        from slack_sdk import WebClient
        
        # WebClientインスタンス作成
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # ファイル名生成
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in original_question[:20] if c.isalnum() or c in " -_")
        filename = f"{timestamp}_{safe_title}_設計書.md"
        
        # files_upload_v2で新しいAPIを使用
        response = client.files_upload_v2(
            file=file_content.encode('utf-8'),
            filename=filename,
            title="設計書",
            channels=[channel],
            thread_ts=thread_ts,
            initial_comment=f'📄 設計書ファイルを生成しました〜だぱか！\n**元の質問**: {original_question}'
        )
        
        log(f"File upload v2 response: {response}")
        
        if response.get('ok'):
            log(f"File uploaded successfully with v2: {filename}")
        else:
            log(f"File upload v2 failed: {response.get('error')}")
            
    except Exception as e:
        log(f"ERROR in file upload v2: {e}")

# --- Main processing flow (スレッド対応版) ---
async def main_processing_flow(event):
    channel = event["channel"]
    text = event["text"].replace(f"<@{BOT_USER_ID}>", "").strip()
    request_ts = event["ts"]
    thread_ts = event.get("thread_ts")
    
    log(f"Processing question: {text}")
    log(f"Request ts: {request_ts}, Thread ts: {thread_ts}")
    
    # スレッド情報設定
    reply_thread_ts = thread_ts if thread_ts else request_ts
    
    try:
        # 1次回答を生成してスレッドに投稿
        log("Generating primary response...")
        primary_response = await generate_primary_response(text)
        primary_ts = send_message(channel, primary_response, thread_ts=reply_thread_ts)
        
        # ファイル生成判定
        needs_file = "後でファイルを共有するぱか！" in primary_response
        log(f"File generation needed: {needs_file}")
        
        # 並列実行タスク作成
        tasks = []
        
        # カテゴリ分類
        category = categorize_question(text)
        
        # 履歴取得
        if thread_ts:
            history = fetch_thread_history(channel, thread_ts)
        else:
            history = f"質問: {text}"
        
        # 2次回答タスク
        secondary_ts = send_message(channel, "🔄 詳細回答を準備中...", thread_ts=reply_thread_ts)
        secondary_task = asyncio.create_task(
            generate_secondary_response_smart(text, category, history, channel, secondary_ts, primary_response)
        )
        tasks.append(secondary_task)
        
        # ファイル生成タスク（必要な場合のみ）
        if needs_file:
            log("Starting asynchronous file generation...")
            file_task = asyncio.create_task(generate_and_upload_file(text, channel, reply_thread_ts))
            tasks.append(file_task)
        
        # 並列実行
        await asyncio.gather(*tasks, return_exceptions=True)
        log("Processing completed successfully!")
        
    except Exception as e:
        log(f"ERROR in processing: {e}")
        send_message(channel, "❌ エラーが発生しました。しばらく後にもう一度お試しください。", 
                    thread_ts=reply_thread_ts)

# --- Slack Bolt App ---
app = App(token=SLACK_BOT_TOKEN)

@app.event("app_mention")
def handle_mention(event, say):
    log(f"Mention received: {event}")
    asyncio.run(main_processing_flow(event))

if __name__ == "__main__":
    print("[START] Socket Mode Slack Bot running...")
    print(f"Bot User ID: {BOT_USER_ID}")
    print(f"Primary Model: {PRIMARY_MODEL}")
    print(f"Tech Model: {TECH_MODEL}")
    print(f"Creative Model: {CREATIVE_MODEL}")
    
    # 起動時にモデル一覧を確認
    print("Checking available models...")
    asyncio.run(check_available_models())
    
    SocketModeHandler(app, SLACK_APP_TOKEN).start()