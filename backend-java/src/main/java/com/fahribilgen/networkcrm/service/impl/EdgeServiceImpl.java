package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
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

        Edge edge = Edge.builder()
                .sourceNode(sourceNode)
                .targetNode(targetNode)
                .type(edgeRequest.getType())
                .weight(edgeRequest.getWeight())
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
                .build();
    }
}
