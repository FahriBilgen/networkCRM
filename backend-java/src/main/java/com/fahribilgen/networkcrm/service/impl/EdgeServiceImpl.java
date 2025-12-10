package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EdgeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class EdgeServiceImpl implements EdgeService {

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private NodeRepository nodeRepository;

    @Override
    @Transactional
    public EdgeResponse createEdge(EdgeRequest edgeRequest, User user) {
        Node sourceNode = nodeRepository.findById(edgeRequest.getSourceNodeId())
                .orElseThrow(() -> new RuntimeException("Source node not found"));
        Node targetNode = nodeRepository.findById(edgeRequest.getTargetNodeId())
                .orElseThrow(() -> new RuntimeException("Target node not found"));

        if (!sourceNode.getUser().getId().equals(user.getId()) || !targetNode.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to nodes");
        }

        if (sourceNode.getId().equals(targetNode.getId())) {
             throw new RuntimeException("Cannot create self-loop edge");
        }

        validateEdgeType(edgeRequest, sourceNode, targetNode);

        Edge edge = Edge.builder()
                .sourceNode(sourceNode)
                .targetNode(targetNode)
                .type(edgeRequest.getType())
                .weight(edgeRequest.getWeight() != null ? edgeRequest.getWeight() : 1)
                .relationshipStrength(edgeRequest.getRelationshipStrength())
                .relationshipType(edgeRequest.getRelationshipType())
                .lastInteractionDate(edgeRequest.getLastInteractionDate())
                .relevanceScore(edgeRequest.getRelevanceScore())
                .addedByUser(edgeRequest.getAddedByUser())
                .notes(edgeRequest.getNotes())
                .sortOrder(edgeRequest.getSortOrder())
                .build();

        Edge savedEdge = edgeRepository.save(edge);
        return mapToResponse(savedEdge);
    }

    @Override
    @Transactional
    public void deleteEdge(UUID edgeId, User user) {
        Edge edge = edgeRepository.findById(edgeId)
                .orElseThrow(() -> new RuntimeException("Edge not found"));

        if (!edge.getSourceNode().getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to edge");
        }

        edgeRepository.delete(edge);
    }

    @Override
    public List<EdgeResponse> getEdgesForNode(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        List<Edge> edges = edgeRepository.findBySourceNodeId(nodeId);
        return edges.stream().map(this::mapToResponse).collect(Collectors.toList());
    }

    private EdgeResponse mapToResponse(Edge edge) {
        return EdgeResponse.builder()
                .id(edge.getId())
                .sourceNodeId(edge.getSourceNode().getId())
                .targetNodeId(edge.getTargetNode().getId())
                .type(edge.getType())
                .weight(edge.getWeight())
                .relationshipStrength(edge.getRelationshipStrength())
                .relationshipType(edge.getRelationshipType())
                .lastInteractionDate(edge.getLastInteractionDate())
                .relevanceScore(edge.getRelevanceScore())
                .addedByUser(edge.getAddedByUser())
                .notes(edge.getNotes())
                .sortOrder(edge.getSortOrder())
                .build();
    }

    private void validateEdgeType(EdgeRequest edgeRequest, Node sourceNode, Node targetNode) {
        EdgeType type = edgeRequest.getType();
        if (type == null) {
            throw new RuntimeException("Edge type is required");
        }

        NodeType sourceType = sourceNode.getType();
        NodeType targetType = targetNode.getType();

        switch (type) {
            case KNOWS -> {
                if (sourceType != NodeType.PERSON || targetType != NodeType.PERSON) {
                    throw new RuntimeException("KNOWS edges are only allowed between PERSON nodes");
                }
            }
            case SUPPORTS -> {
                if (sourceType != NodeType.PERSON || (targetType != NodeType.GOAL && targetType != NodeType.PROJECT)) {
                    throw new RuntimeException("SUPPORTS edges must connect PERSON to GOAL/PROJECT");
                }
            }
            case BELONGS_TO -> {
                boolean goalToVision = sourceType == NodeType.GOAL && targetType == NodeType.VISION;
                boolean projectToGoal = sourceType == NodeType.PROJECT && targetType == NodeType.GOAL;
                boolean personToCompany = sourceType == NodeType.PERSON && targetType == NodeType.COMPANY;
                if (!goalToVision && !projectToGoal && !personToCompany) {
                    throw new RuntimeException("BELONGS_TO edges must connect GOAL->VISION, PROJECT->GOAL or PERSON->COMPANY");
                }
                if (edgeRequest.getSortOrder() == null) {
                    edgeRequest.setSortOrder(0);
                }
            }
            default -> throw new IllegalArgumentException("Unsupported edge type: " + type);
        }
    }
}
