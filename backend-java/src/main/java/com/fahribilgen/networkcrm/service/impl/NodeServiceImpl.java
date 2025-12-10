package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.payload.NodeFilterRequest;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EmbeddingService;
import com.fahribilgen.networkcrm.service.NodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class NodeServiceImpl implements NodeService {

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EmbeddingService embeddingService;

    @Override
    @Transactional
    public NodeResponse createNode(NodeRequest nodeRequest, User user) {
        Node node = Node.builder()
                .user(user)
                .type(nodeRequest.getType())
                .name(nodeRequest.getName())
                .description(nodeRequest.getDescription())
                .sector(nodeRequest.getSector())
                .tags(normalizeTags(nodeRequest.getTags()))
                .relationshipStrength(nodeRequest.getRelationshipStrength())
                .company(nodeRequest.getCompany())
                .role(nodeRequest.getRole())
                .linkedinUrl(nodeRequest.getLinkedinUrl())
                .notes(nodeRequest.getNotes())
                .priority(nodeRequest.getPriority())
                .dueDate(nodeRequest.getDueDate())
                .startDate(nodeRequest.getStartDate())
                .endDate(nodeRequest.getEndDate())
                .status(nodeRequest.getStatus())
                .properties(nodeRequest.getProperties())
                .embedding(null) // generateEmbeddingForRequest(nodeRequest)
                .build();

        Node savedNode = nodeRepository.save(node);
        return mapToResponse(savedNode);
    }

    @Override
    @Transactional
    public NodeResponse updateNode(UUID nodeId, NodeRequest nodeRequest, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        node.setType(nodeRequest.getType());
        node.setName(nodeRequest.getName());
        node.setDescription(nodeRequest.getDescription());
        node.setSector(nodeRequest.getSector());
        if (nodeRequest.getTags() != null) {
            node.setTags(normalizeTags(nodeRequest.getTags()));
        }
        node.setRelationshipStrength(nodeRequest.getRelationshipStrength());
        node.setCompany(nodeRequest.getCompany());
        node.setRole(nodeRequest.getRole());
        node.setLinkedinUrl(nodeRequest.getLinkedinUrl());
        node.setNotes(nodeRequest.getNotes());
        node.setPriority(nodeRequest.getPriority());
        node.setDueDate(nodeRequest.getDueDate());
        node.setStartDate(nodeRequest.getStartDate());
        node.setEndDate(nodeRequest.getEndDate());
        node.setStatus(nodeRequest.getStatus());
        node.setProperties(nodeRequest.getProperties());

        /*
        List<Double> embedding = generateEmbeddingForRequest(nodeRequest);
        if (embedding != null) {
            node.setEmbedding(embedding);
        }
        */

        Node updatedNode = nodeRepository.save(node);
        return mapToResponse(updatedNode);
    }

    @Override
    @Transactional
    public void deleteNode(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        nodeRepository.delete(node);
    }

    @Override
    public NodeResponse getNode(UUID nodeId, User user) {
        Node node = nodeRepository.findById(nodeId)
                .orElseThrow(() -> new RuntimeException("Node not found"));

        if (!node.getUser().getId().equals(user.getId())) {
            throw new RuntimeException("Unauthorized access to node");
        }

        return mapToResponse(node);
    }

    @Override
    public List<NodeResponse> getAllNodes(User user) {
        List<Node> nodes = nodeRepository.findByUserId(user.getId());
        return nodes.stream().map(this::mapToResponse).collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> getNodesByType(NodeType type, User user) {
        List<Node> nodes = nodeRepository.findByUserIdAndType(user.getId(), type);
        return nodes.stream().map(this::mapToResponse).collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> filterNodes(NodeFilterRequest filter, User user) {
        if (filter == null) {
            return getAllNodes(user);
        }
        List<Node> nodes = nodeRepository.findByUserId(user.getId());
        return nodes.stream()
                .filter(node -> matchesFilter(node, filter))
                .map(this::mapToResponse)
                .collect(Collectors.toList());
    }

    @Override
    public List<NodeResponse> findSimilarNodes(String query, User user) {
        if (query == null || query.isBlank()) {
            return List.of();
        }

        List<Double> queryEmbedding = embeddingService.generateEmbedding(query);
        if (queryEmbedding == null) {
            return List.of();
        }

        List<Node> nodes = nodeRepository.findByUserId(user.getId());

        return nodes.stream()
                .filter(node -> node.getEmbedding() != null)
                .sorted((n1, n2) -> {
                    double sim1 = cosineSimilarity(queryEmbedding, n1.getEmbedding());
                    double sim2 = cosineSimilarity(queryEmbedding, n2.getEmbedding());
                    return Double.compare(sim2, sim1); // Descending order
                })
                .limit(5)
                .map(this::mapToResponse)
                .collect(Collectors.toList());
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

    private NodeResponse mapToResponse(Node node) {
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

    private boolean matchesFilter(Node node, NodeFilterRequest filter) {
        if (filter.getType() != null && node.getType() != filter.getType()) {
            return false;
        }

        if (!CollectionUtils.isEmpty(filter.getTypes()) && filter.getTypes().stream().noneMatch(type -> type == node.getType())) {
            return false;
        }

        if (StringUtils.hasText(filter.getSector())) {
            if (!StringUtils.hasText(node.getSector()) || !node.getSector().equalsIgnoreCase(filter.getSector())) {
                return false;
            }
        }

        if (!CollectionUtils.isEmpty(filter.getTags())) {
            List<String> nodeTags = node.getTags();
            if (CollectionUtils.isEmpty(nodeTags)) {
                return false;
            }
            for (String requiredTag : filter.getTags()) {
                boolean match = nodeTags.stream()
                        .filter(Objects::nonNull)
                        .anyMatch(tag -> tag.equalsIgnoreCase(requiredTag));
                if (!match) {
                    return false;
                }
            }
        }

        Integer minStrength = filter.getMinRelationshipStrength();
        Integer maxStrength = filter.getMaxRelationshipStrength();
        Integer nodeStrength = node.getRelationshipStrength();
        if (minStrength != null && (nodeStrength == null || nodeStrength < minStrength)) {
            return false;
        }
        if (maxStrength != null && (nodeStrength == null || nodeStrength > maxStrength)) {
            return false;
        }

        if (StringUtils.hasText(filter.getSearchTerm())) {
            String searchTerm = filter.getSearchTerm().toLowerCase();
            boolean matches = containsIgnoreCase(node.getName(), searchTerm)
                    || containsIgnoreCase(node.getDescription(), searchTerm)
                    || containsIgnoreCase(node.getSector(), searchTerm)
                    || containsIgnoreCase(node.getCompany(), searchTerm)
                    || containsIgnoreCase(node.getRole(), searchTerm)
                    || containsIgnoreCase(node.getNotes(), searchTerm);

            if (!matches && !CollectionUtils.isEmpty(node.getTags())) {
                matches = node.getTags().stream()
                        .filter(Objects::nonNull)
                        .anyMatch(tag -> tag.toLowerCase().contains(searchTerm));
            }

            if (!matches) {
                return false;
            }
        }

        return true;
    }

    private boolean containsIgnoreCase(String value, String searchTerm) {
        return StringUtils.hasText(value) && value.toLowerCase().contains(searchTerm);
    }

    private List<String> normalizeTags(List<String> tags) {
        if (tags == null) {
            return new ArrayList<>();
        }
        return tags.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(tag -> !tag.isEmpty())
                .collect(Collectors.toList());
    }

    private List<Double> generateEmbeddingForRequest(NodeRequest nodeRequest) {
        String payload = buildEmbeddingPayload(nodeRequest);
        if (payload == null || payload.isBlank()) {
            return null;
        }
        return embeddingService.generateEmbedding(payload);
    }

    private String buildEmbeddingPayload(NodeRequest request) {
        StringBuilder builder = new StringBuilder();
        append(builder, request.getName());
        append(builder, request.getDescription());
        append(builder, request.getSector());
        if (request.getTags() != null) {
            request.getTags().forEach(tag -> append(builder, tag));
        }
        append(builder, request.getCompany());
        append(builder, request.getRole());
        append(builder, request.getNotes());
        if (request.getPriority() != null) {
            append(builder, String.valueOf(request.getPriority()));
        }
        if (request.getDueDate() != null) {
            append(builder, request.getDueDate().toString());
        }
        if (request.getStatus() != null) {
            append(builder, request.getStatus().name());
        }
        if (builder.length() == 0) {
            return null;
        }
        return builder.toString().trim();
    }

    private void append(StringBuilder builder, String value) {
        if (value == null) {
            return;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return;
        }
        builder.append(trimmed).append(" ");
    }
}
