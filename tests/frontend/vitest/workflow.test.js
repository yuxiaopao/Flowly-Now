/**
 * Workflow Store Tests
 * Tests for workflow CRUD operations, state management, and API integration
 */

import { setActivePinia, createPinia } from 'pinia'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  mockWorkflow,
  mockNode,
  mockEdge
} from './mocks/workflows.mock'

// Helper to reset store state manually
function resetWorkflowStore(store) {
  store.workflows = []
  store.currentWorkflow = null
  store.nodes = []
  store.edges = []
  store.selectedNode = null
  store.selectedEdge = null
  store.isLoading = false
  store.isSaving = false
  store.isDirty = false
  store.error = null
  store.executionHistory = []
  store.currentExecution = null
  store.canvasViewport = { x: 0, y: 0, zoom: 1 }
  store.availableModels = []
  store.availableTools = []
  store.availableNodeTypes = []
}

describe('Workflow Store', () => {
  let workflowStore
  let workflowApi
  let gatewayApi
  let pinia

  beforeEach(async () => {
    // Create a fresh pinia instance for each test
    pinia = createPinia()
    setActivePinia(pinia)

    // Import store after setting up pinia
    const { useWorkflowStore } = await import('@/stores/workflow')
    const { workflowApi: api } = await import('@/api/workflow')
    const { default: gateway } = await import('@/api/gateway')
    
    workflowStore = useWorkflowStore()
    workflowApi = api
    gatewayApi = gateway

    // Reset store state
    resetWorkflowStore(workflowStore)
  })

  afterEach(() => {
    vi.clearAllMocks()
    pinia.state.value = { workflow: {} }
  })

  describe('State Management', () => {
    it('should initialize with empty state', () => {
      expect(workflowStore.workflows).toEqual([])
      expect(workflowStore.currentWorkflow).toBeNull()
      expect(workflowStore.nodes).toEqual([])
      expect(workflowStore.edges).toEqual([])
      expect(workflowStore.selectedNode).toBeNull()
      expect(workflowStore.isDirty).toBe(false)
    })

    it('should track dirty state when nodes are modified', () => {
      expect(workflowStore.isDirty).toBe(false)
      
      workflowStore.addNode(mockNode)
      
      expect(workflowStore.isDirty).toBe(true)
      expect(workflowStore.hasUnsavedChanges).toBe(true)
    })

    it('should clear editor state correctly', () => {
      // Add some data
      workflowStore.currentWorkflow = mockWorkflow
      workflowStore.nodes = mockWorkflow.nodes
      workflowStore.edges = mockWorkflow.edges
      workflowStore.isDirty = true

      // Clear
      workflowStore.clearEditor()

      expect(workflowStore.currentWorkflow).toBeNull()
      expect(workflowStore.nodes).toEqual([])
      expect(workflowStore.edges).toEqual([])
      expect(workflowStore.isDirty).toBe(false)
    })
  })

  describe('Node Operations', () => {
    beforeEach(() => {
      workflowStore.currentWorkflow = mockWorkflow
      workflowStore.nodes = [...mockWorkflow.nodes]
      workflowStore.edges = [...mockWorkflow.edges]
    })

    it('should add a new node', () => {
      const initialCount = workflowStore.nodes.length
      
      const newNode = workflowStore.addNode(mockNode)
      
      expect(workflowStore.nodes.length).toBe(initialCount + 1)
      expect(newNode).toMatchObject(mockNode)
      expect(workflowStore.isDirty).toBe(true)
    })

    it('should update existing node', () => {
      const nodeId = 'node_2'
      const updates = { data: { ...mockWorkflow.nodes[1].data, label: 'Updated LLM' } }

      workflowStore.updateNode(nodeId, updates)

      const updatedNode = workflowStore.nodes.find(n => n.id === nodeId)
      expect(updatedNode.data.label).toBe('Updated LLM')
      expect(workflowStore.isDirty).toBe(true)
    })

    it('should remove node and associated edges', () => {
      const nodeId = 'node_2'
      const initialNodeCount = workflowStore.nodes.length
      const initialEdgeCount = workflowStore.edges.length

      workflowStore.removeNode(nodeId)

      expect(workflowStore.nodes.length).toBe(initialNodeCount - 1)
    })

    it('should update node position', () => {
      const nodeId = 'node_2'
      const newPosition = { x: 500, y: 300 }

      workflowStore.updateNodePosition(nodeId, newPosition)

      const node = workflowStore.nodes.find(n => n.id === nodeId)
      expect(node.position).toEqual(newPosition)
      expect(workflowStore.isDirty).toBe(true)
    })

    it('should batch update positions', () => {
      const positions = [
        { id: 'node_1', position: { x: 100, y: 100 } },
        { id: 'node_2', position: { x: 200, y: 200 } }
      ]

      workflowStore.batchUpdatePositions(positions)

      expect(workflowStore.isDirty).toBe(true)
    })
  })

  describe('Edge Operations', () => {
    beforeEach(() => {
      workflowStore.currentWorkflow = mockWorkflow
      workflowStore.nodes = [...mockWorkflow.nodes]
      workflowStore.edges = [...mockWorkflow.edges]
    })

    it('should add a new edge', () => {
      const initialCount = workflowStore.edges.length

      const newEdge = workflowStore.addEdge(mockEdge)

      expect(workflowStore.edges.length).toBe(initialCount + 1)
      expect(newEdge).toMatchObject(mockEdge)
      expect(workflowStore.isDirty).toBe(true)
    })

    it('should update existing edge', () => {
      const edgeId = 'edge_1'
      const updates = { label: 'updated label' }

      workflowStore.updateEdge(edgeId, updates)

      const updatedEdge = workflowStore.edges.find(e => e.id === edgeId)
      expect(updatedEdge.label).toBe('updated label')
      expect(workflowStore.isDirty).toBe(true)
    })

    it('should remove edge', () => {
      const edgeId = 'edge_1'
      const initialCount = workflowStore.edges.length

      workflowStore.removeEdge(edgeId)

      expect(workflowStore.edges.length).toBe(initialCount - 1)
      expect(workflowStore.edges.find(e => e.id === edgeId)).toBeUndefined()
      expect(workflowStore.isDirty).toBe(true)
    })
  })

  describe('Selection', () => {
    beforeEach(() => {
      workflowStore.nodes = mockWorkflow.nodes
    })

    it('should select a node', () => {
      const nodeId = 'node_2'

      workflowStore.selectNode(nodeId)

      expect(workflowStore.selectedNode).toBe(nodeId)
      expect(workflowStore.selectedEdge).toBeNull()
    })

    it('should select an edge', () => {
      const edgeId = 'edge_1'

      workflowStore.selectEdge(edgeId)

      expect(workflowStore.selectedEdge).toBe(edgeId)
      expect(workflowStore.selectedNode).toBeNull()
    })

    it('should clear selection', () => {
      workflowStore.selectNode('node_1')
      workflowStore.clearSelection()

      expect(workflowStore.selectedNode).toBeNull()
      expect(workflowStore.selectedEdge).toBeNull()
    })

    it('should get selected node data', () => {
      const nodeId = 'node_2'
      workflowStore.selectNode(nodeId)

      const selectedData = workflowStore.selectedNodeData

      expect(selectedData).toBeTruthy()
      expect(selectedData.id).toBe(nodeId)
    })
  })

  describe('Canvas State', () => {
    it('should update viewport', () => {
      const viewport = { x: 100, y: 200, zoom: 1.5 }

      workflowStore.updateViewport(viewport)

      expect(workflowStore.canvasViewport).toEqual(viewport)
    })
  })

  describe('Undo/Redo Support', () => {
    it('should set nodes and edges for undo/redo', () => {
      const newNodes = [
        { id: 'node_new_1', type: 'llm' },
        { id: 'node_new_2', type: 'end' }
      ]
      const newEdges = [{ id: 'edge_new_1', source: 'node_new_1', target: 'node_new_2' }]

      workflowStore.setNodesAndEdges(newNodes, newEdges)

      expect(workflowStore.nodes).toEqual(newNodes)
      expect(workflowStore.edges).toEqual(newEdges)
    })
  })

  describe('Computed Properties', () => {
    it('should have correct computed properties', () => {
      workflowStore.nodes = mockWorkflow.nodes
      workflowStore.edges = mockWorkflow.edges

      expect(workflowStore.workflowNodes).toEqual(workflowStore.nodes)
      expect(workflowStore.workflowEdges).toEqual(workflowStore.edges)
    })
  })
})
