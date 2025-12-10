package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.EdgeType;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.payload.GoalSuggestionResponse;
import com.fahribilgen.networkcrm.payload.LinkPersonToGoalRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EmbeddingService;
import com.fahribilgen.networkcrm.service.EdgeService;
import com.fahribilgen.networkcrm.service.RecommendationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class RecommendationServiceImpl implements RecommendationService {

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Autowired
    private EdgeService edgeService;

    @Autowired
    private EmbeddingService embeddingService;

    @Override
    public GoalSuggestionResponse suggestPeopleForGoal(UUID goalId, int limit, User user) {
        Node goal = getNode(goalId);
        validateOwnership(goal, user);
        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Node is not a goal");
        }

        ensureNodeEmbedding(goal);

        List<Node> people = nodeRepository.findByUserIdAndType(user.getId(), NodeType.PERSON);
        if (CollectionUtils.isEmpty(people)) {
            return GoalSuggestionResponse.builder()
                    .goalId(goalId)
                    .suggestions(List.of())
                    .build();
        }

        List<GoalSuggestionResponse.PersonSuggestion> suggestions = people.stream()
                .filter(person -> person.getEmbedding() != null)
                .map(person -> GoalSuggestionResponse.PersonSuggestion.builder()
                        .person(mapToNodeResponse(person))
                        .score(cosineSimilarity(goal.getEmbedding(), person.getEmbedding()))
                        .build())
                .filter(suggestion -> suggestion.getScore() > 0)
                .sorted(Comparator.comparingDouble(GoalSuggestionResponse.PersonSuggestion::getScore).reversed())
                .limit(Math.max(limit, 1))
                .collect(Collectors.toList());

        return GoalSuggestionResponse.builder()
                .goalId(goalId)
                .suggestions(suggestions)
                .build();
    }

    @Override
    @Transactional
    public EdgeResponse linkPersonToGoal(UUID goalId, LinkPersonToGoalRequest request, User user) {
        if (request.getPersonId() == null) {
            throw new RuntimeException("personId is required");
        }

        Node goal = getNode(goalId);
        Node person = getNode(request.getPersonId());

        validateOwnership(goal, user);
        validateOwnership(person, user);

        if (goal.getType() != NodeType.GOAL) {
            throw new RuntimeException("Target node is not a goal");
        }
        if (person.getType() != NodeType.PERSON) {
            throw new RuntimeException("Source node is not a person");
        }

        Optional<Edge> existing = edgeRepository.findFirstBySourceNodeIdAndTargetNodeIdAndType(person.getId(), goal.getId(), EdgeType.SUPPORTS);
        existing.ifPresent(edgeRepository::delete);

        EdgeRequest edgeRequest = new EdgeRequest();
        edgeRequest.setSourceNodeId(person.getId());
        edgeRequest.setTargetNodeId(goal.getId());
        edgeRequest.setType(EdgeType.SUPPORTS);
        edgeRequest.setWeight(request.getRelationshipStrength() == null ? 0 : request.getRelationshipStrength());
        edgeRequest.setRelevanceScore(request.getRelevanceScore());
        edgeRequest.setAddedByUser(request.getAddedByUser() == null ? Boolean.TRUE : request.getAddedByUser());
        edgeRequest.setNotes(request.getNotes());
        edgeRequest.setRelationshipStrength(request.getRelationshipStrength());

        return edgeService.createEdge(edgeRequest, user);
    }

    private void ensureNodeEmbedding(Node node) {
        if (node.getEmbedding() != null) {
            return;
        }
        StringBuilder builder = new StringBuilder();
        append(builder, node.getName());
        append(builder, node.getDescription());
        append(builder, node.getNotes());
        String payload = builder.toString().trim();
        if (payload.isEmpty()) {
            return;
        }
        List<Double> embedding = embeddingService.generateEmbedding(payload);
        node.setEmbedding(embedding);
        nodeRepository.save(node);
    }

    private void append(StringBuilder builder, String value) {
        if (value == null) {
            return;
        }
        String trimmed = value.trim();
        if (!trimmed.isEmpty()) {
            builder.append(trimmed).append(" ");
        }
    }

    private Node getNode(UUID nodeId) {
        return nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found: " + nodeId));
    }

    private void validateOwnership(Node node, User user) {
        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node " + node.getId());
        }
    }

    private double cosineSimilarity(List<Double> v1, List<Double> v2) {
        if (v1 == null || v2 == null || v1.size() != v2.size()) {
            return 0.0;
        }

        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < v1.size(); i++) {
            dotProduct += v1.get(i) * v2.get(i);
            normA += Math.pow(v1.get(i), 2);
            normB += Math.pow(v2.get(i), 2);
        }

        if (normA == 0 || normB == 0) {
            return 0.0;
        }

        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
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
                .build();
    }
}
