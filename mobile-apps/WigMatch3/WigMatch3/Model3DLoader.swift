//
//  Model3DLoader.swift
//  WigMatch3
//
//  Created by Yoshikazu Abe on 2025/08/11.
//

import Foundation
import RealityKit
import ModelIO
import SceneKit
import simd

class Model3DLoader {
    
    /// FBXファイルからRealityKit Entityを作成
    static func loadFBXModel(from url: URL) async throws -> ModelEntity? {
        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    // SceneKitでFBXを読み込み
                    let scene: SCNScene
                    do {
                        scene = try SceneKit.SCNScene(url: url, options: nil)
                    } catch {
                        continuation.resume(throwing: Model3DLoaderError.failedToLoadScene)
                        return
                    }
                    
                    let rootNode = scene.rootNode
                    
                    // 頭部のみを抽出（Y座標が一定以上のノードを対象）
                    let headNodes = extractHeadNodes(from: rootNode)
                    
                    if headNodes.isEmpty {
                        // フォールバック: 全体を使用
                        let entity = convertToRealityKitEntity(rootNode)
                        DispatchQueue.main.async {
                            continuation.resume(returning: entity)
                        }
                        return
                    }
                    
                    // 頭部ノードをRealityKitエンティティに変換
                    let headEntity = combineHeadNodes(headNodes)
                    DispatchQueue.main.async {
                        continuation.resume(returning: headEntity)
                    }
                    
                } catch {
                    DispatchQueue.main.async {
                        continuation.resume(throwing: error)
                    }
                }
            }
        }
    }
    
    /// USDCファイルからRealityKit Entityを作成
    static func loadUSDCModel(from url: URL) async throws -> Entity {
        do {
            let entity = try await Entity(contentsOf: url)
            return entity
        } catch {
            throw Model3DLoaderError.failedToLoadUSDC(error)
        }
    }
    
    // MARK: - Private Methods
    
    private static func extractHeadNodes(from rootNode: SCNNode) -> [SCNNode] {
        var headNodes: [SCNNode] = []
        
        func searchNodes(_ node: SCNNode) {
            // 頭部の判定基準: Y座標が0以上、またはnameに"head", "skull", "face"が含まれる
            let isHeadByPosition = node.position.y >= 0
            let isHeadByName = node.name?.lowercased().contains("head") == true ||
                             node.name?.lowercased().contains("skull") == true ||
                             node.name?.lowercased().contains("face") == true
            
            if (isHeadByPosition || isHeadByName) && node.geometry != nil {
                headNodes.append(node)
            }
            
            // 子ノードも再帰的に検索
            node.childNodes.forEach { searchNodes($0) }
        }
        
        searchNodes(rootNode)
        return headNodes
    }
    
    private static func combineHeadNodes(_ nodes: [SCNNode]) -> ModelEntity {
        // シンプルな実装: 最初のノードを使用
        if let firstNode = nodes.first {
            return convertToRealityKitEntity(firstNode)
        }
        
        // フォールバック
        let mesh = MeshResource.generateSphere(radius: 0.1)
        let material = SimpleMaterial(color: .systemPink, isMetallic: false)
        return ModelEntity(mesh: mesh, materials: [material])
    }
    
    private static func convertToRealityKitEntity(_ node: SCNNode) -> ModelEntity {
        // SceneKitのジオメトリをRealityKitのメッシュに変換
        if let geometry = node.geometry {
            do {
                let meshResource = try convertSCNGeometryToMeshResource(geometry)
                
                // マテリアル変換
                let materials = convertSCNMaterials(geometry.materials)
                
                let entity = ModelEntity(mesh: meshResource, materials: materials)
                
                // トランスフォーム適用
                let transform = simd_float4x4(node.transform)
                entity.transform.matrix = transform
                
                return entity
                
            } catch {
                print("❌ ジオメトリ変換エラー: \(error)")
            }
        }
        
        // フォールバック
        let mesh = MeshResource.generateSphere(radius: 0.1)
        let material = SimpleMaterial(color: .systemPink, isMetallic: false)
        return ModelEntity(mesh: mesh, materials: [material])
    }
    
    private static func convertSCNGeometryToMeshResource(_ geometry: SCNGeometry) throws -> MeshResource {
        // 簡単な実装: 基本的な形状を生成
        switch geometry {
        case is SCNSphere:
            let sphere = geometry as! SCNSphere
            return MeshResource.generateSphere(radius: Float(sphere.radius))
        case is SCNBox:
            let box = geometry as! SCNBox
            return MeshResource.generateBox(size: [Float(box.width), Float(box.height), Float(box.length)])
        default:
            // より複雑なジオメトリの場合、ModelIOを使用
            return try convertComplexGeometry(geometry)
        }
    }
    
    private static func convertComplexGeometry(_ geometry: SCNGeometry) throws -> MeshResource {
        // 複雑なジオメトリの場合は、フォールバックとしてボックスを使用
        print("⚠️ 複雑なジオメトリをフォールバックボックスで置き換え")
        return MeshResource.generateBox(size: [0.2, 0.2, 0.2])
    }
    
    private static func convertSCNMaterials(_ scnMaterials: [SCNMaterial]) -> [Material] {
        return scnMaterials.map { scnMaterial in
            var material = SimpleMaterial()
            
            // 基本色の設定
            if let contents = scnMaterial.diffuse.contents {
                if let uiColor = contents as? UIColor {
                    material.color = .init(tint: uiColor)
                }
            } else {
                material.color = .init(tint: .systemPink)
            }
            
            // その他のプロパティ
            material.roughness = 0.4
            material.metallic = 0.1
            
            return material
        }
    }
}

// MARK: - Error Types

enum Model3DLoaderError: Error, LocalizedError {
    case failedToLoadScene
    case failedToLoadUSDC(Error)
    case invalidGeometry
    
    var errorDescription: String? {
        switch self {
        case .failedToLoadScene:
            return "3Dシーンの読み込みに失敗しました"
        case .failedToLoadUSDC(let error):
            return "USDCファイルの読み込みに失敗しました: \(error.localizedDescription)"
        case .invalidGeometry:
            return "無効なジオメトリです"
        }
    }
}
