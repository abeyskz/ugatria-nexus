# 🌟 Ugatria Nexus - AI & Development Projects Portfolio

> **統合開発プロジェクト群** - AI、機械学習、モバイルアプリ、Webサービスの実験・開発環境

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Latest-blue)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)

## 📋 プロジェクト一覧

### 🤖 **AI・機械学習系**

#### **[Tesumi System v2.0](./tesumi/)**
> **記憶継承システム** - Memory-Augmented GNN記憶管理 + Claude API統合

- **技術**: Python, FastAPI, PostgreSQL+pgvector, PyTorch, GraphSAGE
- **特徴**: GNNベース記憶管理、自然対話生成、感情モデル統合
- **状態**: 🟢 Ready for Production

#### **[TechWise Test](./techwise-test/)**  
> **技術書推薦システム** - GCNによる書籍カテゴリ分類・推薦

- **技術**: PyTorch Geometric, GCN/GAT, PostgreSQL, scikit-learn
- **特徴**: グラフニューラルネットワークによる書籍推薦、85%分類精度目標
- **状態**: 🟢 完成・テスト済み

### 💬 **チャットボット・対話系**

#### **[Slackbot](./slackbot/)**
> **多機能Slack AI bot** - Ollama連携による企業向けAIアシスタント

- **技術**: Python, Slack Bolt, Ollama API, 複数LLMモデル切り替え
- **特徴**: コンテキスト管理、技術質問対応、ファイル生成機能
- **状態**: 🟡 動作確認済み・要整備

### 📱 **モバイルアプリケーション**

#### **[Mobile Apps](./mobile-apps/)**
> **iOS/Android アプリ開発プロジェクト群**

##### **Pocori Conversation**
- **技術**: iOS (Swift/SwiftUI), 感情認識、会話システム
- **特徴**: キャラクター対話、感情表現、音声認識
- **状態**: 🟡 開発中

##### **WigMatch3**  
- **技術**: React Native / Flutter, マッチングアルゴリズム
- **特徴**: ウィッグマッチングサービス
- **状態**: 🟡 プロトタイプ段階

### 🔬 **実験・研究プロジェクト**

#### **[Hackathon Entry](./hackathon-entry/)**
> **ハッカソン参加プロジェクト**
- **状態**: 🔴 仕様策定中

#### **[Simple MBTI](./simple-mbti/)**
> **MBTI性格診断システム**
- **状態**: 🔴 仕様策定中

#### **[SkillGarden](./skillgarden/)**
> **スキル育成プラットフォーム**
- **状態**: 🔴 仕様策定中

#### **[TechWise](./techwise/)**
> **技術書関連サービス**
- **状態**: 🔴 仕様策定中

### 🧪 **テストプロパティ実験系**

#### **[TestProp Forge](./testprop-forge/)**
> **テストプロパティ生成ツール**
- **状態**: 🔴 仕様策定中

#### **[TestProp Insight](./testprop-insight/)**
> **テストデータ分析プラットフォーム**  
- **状態**: 🔴 仕様策定中

---

## 🏗️ 技術スタック概要

### **バックエンド**
- **Python**: FastAPI, Flask, SQLAlchemy, asyncio
- **Node.js**: Express.js, TypeScript
- **データベース**: PostgreSQL, SQLite, pgvector
- **AI/ML**: PyTorch, PyTorch Geometric, Transformers, scikit-learn

### **フロントエンド**
- **Web**: React, Vue.js, TypeScript
- **Mobile**: iOS (Swift/SwiftUI), Android (Kotlin), React Native, Flutter

### **インフラ・DevOps**
- **コンテナ**: Docker, Docker Compose
- **クラウド**: AWS, GCP (プロジェクトにより)
- **CI/CD**: GitHub Actions
- **監視**: Prometheus, Grafana (予定)

---

## 🚀 セットアップ

### **前提条件**
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### **クイックスタート**

```bash
# リポジトリクローン
git clone https://github.com/[username]/ugatria-nexus.git
cd ugatria-nexus

# 個別プロジェクト起動例
cd tesumi
docker-compose up -d

cd ../slackbot
pip install -r requirements.txt
python main.py
```

### **各プロジェクトの詳細セットアップ**
各プロジェクトフォルダの`README.md`を参照してください。

---

## 📊 プロジェクト状態

| プロジェクト | 状態 | 技術 | 完成度 |
|-------------|------|------|--------|
| Tesumi | 🟢 完成 | Python, FastAPI, GNN | 90% |
| TechWise Test | 🟢 完成 | PyTorch Geometric | 95% |
| Slackbot | 🟡 動作中 | Python, Slack API | 75% |
| Mobile Apps | 🟡 開発中 | iOS/Android | 40% |
| Others | 🔴 計画中 | TBD | 10% |

---

## 🤝 貢献

### **開発フロー**
1. Feature branchを作成
2. 変更を実装
3. テストを実行
4. Pull Requestを作成

### **プロジェクト別貢献**
- **完成プロジェクト**: バグ修正、機能改善、ドキュメント改善
- **開発中プロジェクト**: 機能実装、テスト、UI/UX改善
- **計画中プロジェクト**: 仕様策定、技術選定、プロトタイピング

---

## 📖 ドキュメント

- [アーキテクチャ概要](./docs/ARCHITECTURE.md) *(準備中)*
- [開発ガイドライン](./docs/DEVELOPMENT.md) *(準備中)*
- [デプロイメントガイド](./docs/DEPLOYMENT.md) *(準備中)*

---

## 📄 ライセンス

このプロジェクトは [MIT License](./LICENSE) の下で公開されています。

---

## 📧 連絡先

- **開発者**: [Your Name]
- **組織**: Ugatria
- **GitHub**: [Repository URL]

---

## 🎯 ロードマップ

### **2025 Q3-Q4**
- [ ] Tesumi System v2.1 - 高度な記憶管理機能
- [ ] TechWise Production Release
- [ ] Mobile Apps Beta版リリース
- [ ] 実験プロジェクトの仕様確定

### **2026 Q1**
- [ ] マイクロサービス統合
- [ ] CI/CD パイプライン完成
- [ ] パフォーマンス監視システム導入

---

**🌟 Ugatria Nexus - Where AI meets Innovation**
