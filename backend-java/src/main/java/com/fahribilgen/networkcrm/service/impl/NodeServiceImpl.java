package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.EmbeddingService;
import com.fahribilgen.networkcrm.service.NodeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
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
        List<Double> embedding = embeddingService.generateEmbedding(nodeRequest.getDescription());

        Node node = Node.builder()
                .user(user)
                .type(nodeRequest.getType())
                .name(nodeRequest.getName())
                .description(nodeRequest.getDescription())
                .properties(nodeRequest.getProperties())
                .embedding(embedding)
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
        node.setProperties(nodeRequest.getProperties());

        if (nodeRequest.getDescription() != null && !nodeRequest.getDescription().equals(node.getDescription())) {
             List<Double> embedding = embeddingService.generateEmbedding(nodeRequest.getDescription());
             node.setEmbedding(embedding);
        } else if (node.getEmbedding() == null && nodeRequest.getDescription() != null) {
             List<Double> embedding = embeddingService.generateEmbedding(nodeRequest.getDescription());
             node.setEmbedding(embedding);
        }

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
    public List<NodeResponse> findSimilarNodes(String query, User user) {
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
                .properties(node.getProperties())
                .build();
    }
}
