package com.fahribilgen.networkcrm.service.impl;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.payload.GraphResponse;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.payload.VisionTreeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.GraphService;

@Service
public class GraphServiceImpl implements GraphService {

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Override
    @Transactional(readOnly = true)
    public GraphResponse getGraph(User user) {
        return getGraph(user, Integer.MAX_VALUE);
    }

    @Override
    @Transactional(readOnly = true)
    public GraphResponse getGraph(User user, int limit) {
        List<Node> nodes;
        if (limit < Integer.MAX_VALUE) {
            nodes = nodeRepository.findByUserId(user.getId(),
                    PageRequest.of(0, limit, Sort.by(Sort.Direction.DESC, "createdAt")));
        } else {
            nodes = nodeRepository.findByUserId(user.getId());
        }

        Set<UUID> nodeIds = nodes.stream().map(Node::getId).collect(Collectors.toSet());

        List<Edge> edges = edgeRepository.findBySourceNode_User_Id(user.getId());

        List<Edge> filteredEdges = edges.stream()
                .filter(e -> nodeIds.contains(e.getSourceNode().getId()) && nodeIds.contains(e.getTargetNode().getId()))
                .collect(Collectors.toList());

        List<NodeResponse> nodeResponses = nodes.stream().map(this::mapToNodeResponse).collect(Collectors.toList());
        List<EdgeResponse> edgeResponses = filteredEdges.stream().map(this::mapToEdgeResponse).collect(Collectors.toList());

        return GraphResponse.builder()
                .nodes(nodeResponses)
                .links(edgeResponses)
                .build();
    }

    @Override
    public VisionTreeResponse getVisionTree(User user) {
        List<Node> nodes = nodeRepository.findByUserId(user.getId());

        List<Edge> edges = edgeRepository.findBySourceNode_User_Id(user.getId());

        Map<UUID, List<Node>> goalsByVision = new HashMap<>();
        Map<UUID, List<Node>> projectsByGoal = new HashMap<>();
        Map<UUID, Integer> sortOrderByNodeId = new HashMap<>();

        for (Edge edge : edges) {
            if (edge.getType() != EdgeType.BELONGS_TO) {
                continue;
            }
            Node source = edge.getSourceNode();
            Node target = edge.getTargetNode();
            if (source == null || target == null) {
                continue;
            }

            if (source.getType() == NodeType.GOAL && target.getType() == NodeType.VISION) {
                goalsByVision.computeIfAbsent(target.getId(), id -> new ArrayList<>()).add(source);
                sortOrderByNodeId.put(source.getId(), edge.getSortOrder() == null ? 0 : edge.getSortOrder());
            } else if (source.getType() == NodeType.PROJECT && target.getType() == NodeType.GOAL) {
                projectsByGoal.computeIfAbsent(target.getId(), id -> new ArrayList<>()).add(source);
                sortOrderByNodeId.put(source.getId(), edge.getSortOrder() == null ? 0 : edge.getSortOrder());
            }
        }

        List<VisionTreeResponse.VisionNode> visionNodes = nodes.stream()
                .filter(node -> node.getType() == NodeType.VISION)
                .sorted(Comparator.comparing(node -> Optional.ofNullable(node.getName()).orElse(""), String.CASE_INSENSITIVE_ORDER))
                .map(vision -> VisionTreeResponse.VisionNode.builder()
                .vision(mapToNodeResponse(vision))
                .goals(buildGoalNodes(vision.getId(), goalsByVision, projectsByGoal, sortOrderByNodeId))
                .build())
                .collect(Collectors.toList());

        return VisionTreeResponse.builder()
                .visions(visionNodes)
                .build();
    }

    private List<VisionTreeResponse.GoalNode> buildGoalNodes(UUID visionId,
            Map<UUID, List<Node>> goalsByVision,
            Map<UUID, List<Node>> projectsByGoal,
            Map<UUID, Integer> sortOrderByNodeId) {
        List<Node> goals = goalsByVision.getOrDefault(visionId, List.of());
        return goals.stream()
                .sorted(Comparator.comparing((Node node) -> sortOrderByNodeId.getOrDefault(node.getId(), 0))
                        .thenComparing(node -> Optional.ofNullable(node.getName()).orElse(""), String.CASE_INSENSITIVE_ORDER))
                .map(goalNode -> VisionTreeResponse.GoalNode.builder()
                .goal(mapToNodeResponse(goalNode))
                .projects(buildProjectNodes(goalNode.getId(), projectsByGoal, sortOrderByNodeId))
                .build())
                .collect(Collectors.toList());
    }

    private List<NodeResponse> buildProjectNodes(UUID goalId,
            Map<UUID, List<Node>> projectsByGoal,
            Map<UUID, Integer> sortOrderByNodeId) {
        List<Node> projects = projectsByGoal.getOrDefault(goalId, List.of());
        return projects.stream()
                .sorted(Comparator.comparing((Node node) -> sortOrderByNodeId.getOrDefault(node.getId(), 0))
                        .thenComparing(node -> Optional.ofNullable(node.getName()).orElse(""), String.CASE_INSENSITIVE_ORDER))
                .map(this::mapToNodeResponse)
                .collect(Collectors.toList());
    }

    private NodeResponse mapToNodeResponse(Node node) {
        return NodeResponse.builder()
                .id(node.getId())
                .type(node.getType())
                .name(node.getName())
                .description(node.getDescription())
                .sector(node.getSector())
                .tags(node.getTags())
                .relationshipStrength(node.getRelationshipStrength())
                .company(node.getCompany())
                .role(node.getRole())
                .linkedinUrl(node.getLinkedinUrl())
                .notes(node.getNotes())
                .priority(node.getPriority())
                .dueDate(node.getDueDate())
                .startDate(node.getStartDate())
                .endDate(node.getEndDate())
                .status(node.getStatus())
                .properties(node.getProperties())
                .createdAt(node.getCreatedAt())
                .updatedAt(node.getUpdatedAt())
                .build();
    }

    private EdgeResponse mapToEdgeResponse(Edge edge) {
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
}
