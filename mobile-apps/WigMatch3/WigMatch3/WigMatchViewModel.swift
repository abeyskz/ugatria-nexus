//
//  WigMatchViewModel.swift
//  WigMatch3
//
//  Created by Yoshikazu Abe on 2025/08/11.
//
//  【シンプル版】
//

import Foundation
import RealityKit
import SwiftUI
import simd

// 操作モードの定義
enum ControlMode: CaseIterable {
    case wig
    case body
    case both
    
    var displayName: String {
        switch self {
        case .wig: return "WIG"
        case .body: return "BODY"
        case .both: return "BOTH"
        }
    }
}

@MainActor
class WigMatchViewModel: ObservableObject {
    @Published var controlMode: ControlMode = .both
    
    // 情報表示用のプロパティ
    @Published var headScale: Float = 3.0
    @Published var wigScale: Float = 0.40
    @Published var headPosition: simd_float3 = simd_float3(0, 0, 0)
    @Published var wigPosition: simd_float3 = simd_float3(0, 0.02, 0)
    
    private var arView: ARView?
    private var anchor: AnchorEntity?
    private var modelContainer: Entity?
    private var headModel: ModelEntity?
    private var wigModel: ModelEntity?
    
    // 内部状態の管理
    private var rotationX: Float = 0.0
    private var rotationY: Float = 0.0
    private var internalHeadScale: Float = 1.0
    private var internalWigScale: Float = 0.05
    private var yPosition: Float = -0.3
    private var wigOffsetX: Float = 0.0
    private var wigOffsetY: Float = 0.02
    private var wigOffsetZ: Float = 0.0
    private var isWigVisible: Bool = true

    // ARViewの初期設定
    func setupARView(_ arView: ARView, anchor: AnchorEntity) {
        self.arView = arView
        self.anchor = anchor
        
        // モデルを配置するコンテナを作成
        modelContainer = Entity()
        // 初期位置を設定
        updatePosition()
        anchor.addChild(modelContainer!)
        
        // モデルの読み込みを非同期で開始
        Task {
            await loadAndDisplayModels()
        }
    }
    
    // モデルを読み込んで表示するメイン処理
    private func loadAndDisplayModels() async {
        
        // --- 1. ヘッドモデルの読み込み ---
        do {
            // USD形式でヘッドモデルを読み込み
            let head = try await ModelEntity.loadModel(named: "abe_head.usdc")
            // ヘッドモデルの位置を中心に調整
            head.position = [0, 0, 0]
            modelContainer?.addChild(head)
            self.headModel = head
            print("✅ ヘッドモデル読み込み成功")
        } catch {
            print("❌ ヘッドモデル読み込み失敗: \(error)")
            // 失敗した場合は、代替の球体を表示
            createFallbackHeadModel()
        }
        
        // --- 2. Wigモデルの読み込み ---
        do {
            // RealityKitの標準機能で直接USDCを読み込み
            let wig = try await ModelEntity.loadModel(named: "kanata_hair.usdc")
            // 初期位置を設定し、後で調整される
            modelContainer?.addChild(wig)
            self.wigModel = wig
            print("✅ Wigモデル読み込み成功")
        } catch {
            print("❌ Wigモデル読み込み失敗: \(error)")
            // 失敗した場合は、代替の箱を表示
            createFallbackWigModel()
        }
        
        // --- 3. 初期状態を設定 ---
        resetView()
    }

    // MARK: - フォールバック（代替モデル作成）
    
    private func createFallbackHeadModel() {
        guard let modelContainer = modelContainer else { return }
        let headMesh = MeshResource.generateSphere(radius: 0.1)
        let headMaterial = SimpleMaterial(color: .systemPink, isMetallic: false)
        let headEntity = ModelEntity(mesh: headMesh, materials: [headMaterial])
        modelContainer.addChild(headEntity)
        self.headModel = headEntity
        print("⚠️ フォールバック頭部モデル（球体）作成")
    }
    
    private func createFallbackWigModel() {
        guard let modelContainer = modelContainer else { return }
        let wigMesh = MeshResource.generateBox(size: [0.12, 0.05, 0.12])
        let wigMaterial = SimpleMaterial(color: .systemBrown, isMetallic: false)
        let wigEntity = ModelEntity(mesh: wigMesh, materials: [wigMaterial])
        wigEntity.position.y = 0.05
        modelContainer.addChild(wigEntity)
        self.wigModel = wigEntity
        print("⚠️ フォールバックWigモデル（箱）作成")
    }

    // MARK: - ユーザー操作
    
    // モード切替メソッド
    func switchToNextMode() {
        switch controlMode {
        case .wig:
            controlMode = .body
        case .body:
            controlMode = .both
        case .both:
            controlMode = .wig
        }
    }
    
    // 情報表示用データの更新
    private func updateDisplayInfo() {
        // Head情報の更新
        if let headModel = headModel {
            headPosition = headModel.position
        }
        
        // Wig情報の更新
        if let wigModel = wigModel {
            wigPosition = wigModel.position
        }
    }
    
    // 回転（選択されたモードに応じて）
    func rotateModel(deltaX: Float, deltaY: Float) {
        switch controlMode {
        case .wig:
            rotateWig(deltaX: deltaX, deltaY: deltaY)
        case .body:
            rotateHead(deltaX: deltaX, deltaY: deltaY)
        case .both:
            rotateBoth(deltaX: deltaX, deltaY: deltaY)
        }
    }

    // スケール（選択されたモードに応じて）
    func scaleModel(scale: Float) {
        switch controlMode {
        case .wig:
            scaleWig(scale: scale)
        case .body:
            scaleHead(scale: scale)
        case .both:
            scaleBoth(scale: scale)
        }
    }
    
    // 移動（選択されたモードに応じて）（カメラ座標系）
    func moveModel(deltaX: Float, deltaY: Float) {
        // 横回転のみを考慮して、カメラ座標系での移動を計算
        let rotY = simd_quatf(angle: rotationY, axis: [0, 1, 0])
        
        // カメラ座標系での移動ベクトルをワールド座標系に変換
        let cameraMovement = simd_float3(deltaX, -deltaY, 0) // Y軸は逆向き
        let worldMovement = rotY.act(cameraMovement)
        
        switch controlMode {
        case .wig:
            moveWigInWorld(worldMovement: worldMovement)
        case .body:
            moveHeadInWorld(worldMovement: worldMovement)
        case .both:
            moveBothInWorld(worldMovement: worldMovement)
        }
    }
    
    // MARK: - モード別処理メソッド
    
    // Wigのみ回転（横回転のみ）
    private func rotateWig(deltaX: Float, deltaY: Float) {
        guard let wigModel = wigModel else { return }
        // 縦回転は無効化し、横回転（Y軸）のみ適用
        let rotY = simd_quatf(angle: deltaX, axis: [0, 1, 0])
        let newRotation = simd_mul(rotY, wigModel.transform.rotation)
        wigModel.transform.rotation = newRotation
    }
    
    // 頭部のみ回転（横回転のみ）
    private func rotateHead(deltaX: Float, deltaY: Float) {
        guard let headModel = headModel else { return }
        // 縦回転は無効化し、横回転（Y軸）のみ適用
        let rotY = simd_quatf(angle: deltaX, axis: [0, 1, 0])
        let newRotation = simd_mul(rotY, headModel.transform.rotation)
        headModel.transform.rotation = newRotation
    }
    
    // 両方回転（横回転のみ）
    private func rotateBoth(deltaX: Float, deltaY: Float) {
        // 縦回転（rotationX）は無効化し、横回転（rotationY）のみ適用
        rotationY += deltaX
        updateRotation()
    }
    
    // Wigのみスケール
    private func scaleWig(scale: Float) {
        wigScale *= scale
        wigScale = max(0.01, min(5.0, wigScale))
        updateWigTransform()
    }
    
    // 頭部のみスケール
    private func scaleHead(scale: Float) {
        headScale *= scale
        headScale = max(0.01, min(5.0, headScale))
        updateHeadTransform()
    }
    
    // 両方スケール
    private func scaleBoth(scale: Float) {
        headScale *= scale
        wigScale *= scale
        headScale = max(0.01, min(5.0, headScale))
        wigScale = max(0.01, min(5.0, wigScale))
        updateHeadTransform()
        updateWigTransform()
    }
    
    // Wigのみ移動
    private func moveWig(deltaX: Float, deltaY: Float) {
        wigOffsetX += deltaX
        wigOffsetY -= deltaY  // Y軸は逆向き
        updateWigPosition()
    }
    
    // 頭部のみ移動
    private func moveHead(deltaX: Float, deltaY: Float) {
        guard let headModel = headModel else { return }
        headModel.position.x += deltaX
        headModel.position.y -= deltaY  // Y軸は逆向き
    }
    
    // 両方移動
    private func moveBoth(deltaX: Float, deltaY: Float) {
        guard let modelContainer = modelContainer else { return }
        modelContainer.position.x += deltaX
        modelContainer.position.y -= deltaY  // Y軸は逆向き
    }
    
    // MARK: - ワールド座標系での移動メソッド
    
    // Wigのみワールド座標系で移動
    private func moveWigInWorld(worldMovement: simd_float3) {
        wigOffsetX += worldMovement.x
        wigOffsetY += worldMovement.y
        wigOffsetZ += worldMovement.z
        updateWigPosition()
    }
    
    // 頭部のみワールド座標系で移動
    private func moveHeadInWorld(worldMovement: simd_float3) {
        guard let headModel = headModel else { return }
        headModel.position.x += worldMovement.x
        headModel.position.y += worldMovement.y
        headModel.position.z += worldMovement.z
    }
    
    // 両方ワールド座標系で移動
    private func moveBothInWorld(worldMovement: simd_float3) {
        guard let modelContainer = modelContainer else { return }
        modelContainer.position.x += worldMovement.x
        modelContainer.position.y += worldMovement.y
        modelContainer.position.z += worldMovement.z
    }
    
    // 回転を適用（全体のコンテナに）- 横回転のみ
    private func updateRotation() {
        guard let modelContainer = modelContainer else { return }
        
        // 横回転（Y軸）のみ適用
        let rotY = simd_quatf(angle: rotationY, axis: [0, 1, 0])
        modelContainer.transform.rotation = rotY
    }
    
    // 頭部の変形を適用
    private func updateHeadTransform() {
        guard let headModel = headModel else { return }
        let scale = simd_float3(repeating: headScale)
        headModel.transform.scale = scale
    }
    
    // Wigの変形を適用
    private func updateWigTransform() {
        guard let wigModel = wigModel else { return }
        let scale = simd_float3(repeating: wigScale)
        wigModel.transform.scale = scale
    }
    
    // Wigの位置を適用
    private func updateWigPosition() {
        guard let wigModel = wigModel else { return }
        wigModel.position = [wigOffsetX, wigOffsetY, wigOffsetZ]
    }
    
    // 全体の位置を適用
    private func updatePosition() {
        guard let modelContainer = modelContainer else { return }
        modelContainer.position = [0, yPosition, -0.3]
    }

    // Wigの位置調整メソッド（三次元用）
    func moveWigPosition(deltaX: Float = 0, deltaY: Float = 0, deltaZ: Float = 0) {
        wigOffsetX += deltaX
        wigOffsetY += deltaY
        wigOffsetZ += deltaZ
        updateWigPosition()
    }
    
    // Wigの位置をリセット
    func resetWigPosition() {
        wigOffsetX = 0.0
        wigOffsetY = 0.02
        wigOffsetZ = 0.0
    }
    
    // 初期状態にリセット
    func resetView() {
        rotationX = 0
        rotationY = 0
        headScale = 3.0   // 頭部の適切なサイズ
        wigScale = 0.40   // Wigの適切なサイズ
        yPosition = -0.3  // 適切な位置
        isWigVisible = true
        resetWigPosition()  // Wig位置もリセット
        updateRotation()
        updateHeadTransform()
        updateWigTransform()
        updateWigPosition()
        updatePosition()
        updateWigVisibility()
    }

    // Wigの表示/非表示
    func toggleWig() {
        isWigVisible.toggle()
        updateWigVisibility()
    }

    private func updateWigVisibility() {
        wigModel?.isEnabled = isWigVisible
    }

    // ビューの更新（UIから呼ばれる）
    func updateView() {
        updateRotation()
        updateHeadTransform()
        updateWigTransform()
        updateWigPosition()
        updatePosition()
        updateWigVisibility()
        updateDisplayInfo()
    }
}
