//
//  WigMatchMainView.swift
//  WigMatch3
//
//  Created by Yoshikazu Abe on 2025/08/11.
//

import SwiftUI
import RealityKit
import simd

struct WigMatchMainView: View {
    @StateObject private var viewModel = WigMatchViewModel()
    @State private var currentRotation = matrix_identity_float4x4
    @State private var lastRotation = matrix_identity_float4x4
    
    var body: some View {
        NavigationStack {
            ZStack {
                // 3D表示エリア
                WigMatchARView(viewModel: viewModel)
                    .ignoresSafeArea()
                
                // 情報表示パネル（右上）
                VStack {
                    HStack {
                        Spacer()
                        infoPanel
                            .padding(.trailing, 10)
                            .padding(.top, 10)
                    }
                    Spacer()
                }
                
                // コントロールUI（下部）
                VStack {
                    Spacer()
                    
                    controlPanel
                        .padding(.horizontal)
                        .padding(.bottom, 50)
                }
            }
            .navigationTitle("Wig Match 3D")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private var controlPanel: some View {
        HStack(spacing: 15) {
            // モード切替ボタン
            Button(viewModel.controlMode.displayName) {
                viewModel.switchToNextMode()
            }
            .font(.headline)
            .padding()
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(10)
            
            // リセットボタン
            Button("Reset") {
                viewModel.resetView()
            }
            .font(.headline)
            .padding()
            .background(Color.red)
            .foregroundColor(.white)
            .cornerRadius(10)
        }
    }
    
    // 情報表示パネル
    private var infoPanel: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("BODY")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.pink)
            
            Text("Scale: \(String(format: "%.2f", viewModel.headScale))")
                .font(.caption)
                .foregroundColor(.white)
            
            Text("Pos: (\(String(format: "%.2f", viewModel.headPosition.x)), \(String(format: "%.2f", viewModel.headPosition.y)), \(String(format: "%.2f", viewModel.headPosition.z)))")
                .font(.caption)
                .foregroundColor(.white)
            
            Divider()
                .background(Color.white)
            
            Text("WIG")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.brown)
            
            Text("Scale: \(String(format: "%.3f", viewModel.wigScale))")
                .font(.caption)
                .foregroundColor(.white)
            
            Text("Pos: (\(String(format: "%.2f", viewModel.wigPosition.x)), \(String(format: "%.2f", viewModel.wigPosition.y)), \(String(format: "%.2f", viewModel.wigPosition.z)))")
                .font(.caption)
                .foregroundColor(.white)
        }
        .padding(10)
        .background(Color.black.opacity(0.7))
        .cornerRadius(8)
    }
}

struct WigMatchARView: UIViewRepresentable {
    let viewModel: WigMatchViewModel
    
    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)
        
        // 環境設定
        arView.environment.background = .color(.black)
        arView.renderOptions.insert(.disablePersonOcclusion)
        arView.renderOptions.insert(.disableDepthOfField)
        
        // ライティング設定（最適化）
        let mainLight = Entity()
        let mainDirectionalLight = DirectionalLightComponent(color: .white, intensity: 5000)
        mainLight.components.set(mainDirectionalLight)
        mainLight.look(at: [0, 0, 0], from: [1, 2, 1], relativeTo: nil)
        
        let fillLight = Entity()
        let fillDirectionalLight = DirectionalLightComponent(color: .white, intensity: 2000)
        fillLight.components.set(fillDirectionalLight)
        fillLight.look(at: [0, 0, 0], from: [-1, 1, 1], relativeTo: nil)
        
        // アンカー作成
        let anchor = AnchorEntity()
        anchor.addChild(mainLight)
        anchor.addChild(fillLight)
        arView.scene.addAnchor(anchor)
        
        // ViewModelにARViewを設定
        viewModel.setupARView(arView, anchor: anchor)
        
        // ジェスチャー設定
        let panGesture = UIPanGestureRecognizer(target: context.coordinator, action: #selector(context.coordinator.handlePan(_:)))
        panGesture.minimumNumberOfTouches = 1
        panGesture.maximumNumberOfTouches = 1
        
        let twoFingerPanGesture = UIPanGestureRecognizer(target: context.coordinator, action: #selector(context.coordinator.handleTwoFingerPan(_:)))
        twoFingerPanGesture.minimumNumberOfTouches = 2
        twoFingerPanGesture.maximumNumberOfTouches = 2
        
        let pinchGesture = UIPinchGestureRecognizer(target: context.coordinator, action: #selector(context.coordinator.handlePinch(_:)))
        
        arView.addGestureRecognizer(panGesture)
        arView.addGestureRecognizer(twoFingerPanGesture)
        arView.addGestureRecognizer(pinchGesture)
        
        return arView
    }
    
    func updateUIView(_ uiView: ARView, context: Context) {
        // ViewModel の変更を反映
        viewModel.updateView()
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(viewModel: viewModel)
    }
    
    class Coordinator: NSObject {
        let viewModel: WigMatchViewModel
        private var lastPanTranslation: CGPoint = .zero
        private var lastTwoFingerTranslation: CGPoint = .zero
        
        init(viewModel: WigMatchViewModel) {
            self.viewModel = viewModel
        }
        
        // 一本指スワイプ: 回転
        @objc func handlePan(_ gesture: UIPanGestureRecognizer) {
            let translation = gesture.translation(in: gesture.view)
            
            switch gesture.state {
            case .began:
                lastPanTranslation = translation
            case .changed:
                let deltaX = Float(translation.x - lastPanTranslation.x) * 0.01
                let deltaY = Float(translation.y - lastPanTranslation.y) * 0.01
                
                Task { @MainActor in
                    viewModel.rotateModel(deltaX: deltaX, deltaY: deltaY)
                }
                lastPanTranslation = translation
            case .ended, .cancelled:
                lastPanTranslation = .zero
            default:
                break
            }
        }
        
        // 二本指スワイプ: 平行移動
        @objc func handleTwoFingerPan(_ gesture: UIPanGestureRecognizer) {
            let translation = gesture.translation(in: gesture.view)
            
            switch gesture.state {
            case .began:
                lastTwoFingerTranslation = translation
            case .changed:
                let deltaX = Float(translation.x - lastTwoFingerTranslation.x) * 0.001
                let deltaY = Float(translation.y - lastTwoFingerTranslation.y) * 0.001
                
                Task { @MainActor in
                    viewModel.moveModel(deltaX: deltaX, deltaY: deltaY)
                }
                lastTwoFingerTranslation = translation
            case .ended, .cancelled:
                lastTwoFingerTranslation = .zero
            default:
                break
            }
        }
        
        // ピンチ: 拡大縮小
        @objc func handlePinch(_ gesture: UIPinchGestureRecognizer) {
            let scale = Float(gesture.scale)
            Task { @MainActor in
                viewModel.scaleModel(scale: scale)
            }
            gesture.scale = 1.0
        }
    }
}

#Preview {
    WigMatchMainView()
}
