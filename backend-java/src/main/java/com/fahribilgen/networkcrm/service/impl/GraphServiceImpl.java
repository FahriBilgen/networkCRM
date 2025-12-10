package com.fahribilgen.networkcrm.service.impl;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.EdgeResponse;
import com.fahribilgen.networkcrm.payload.GraphResponse;
import com.fahribilgen.networkcrm.payload.NodeResponse;
import com.fahribilgen.networkcrm.repository.EdgeRepository;
import com.fahribilgen.networkcrm.repository.NodeRepository;
import com.fahribilgen.networkcrm.service.GraphService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class GraphServiceImpl implements GraphService {

    @Autowired
    private NodeRepository nodeRepository;

    @Autowired
    private EdgeRepository edgeRepository;

    @Override
    public GraphResponse getGraph(User user) {
        List<Node> nodes = nodeRepository.findByUserId(user.getId());
        List<Edge> edges = edgeRepository.findBySourceNode_User_Id(user.getId());

        List<NodeResponse> nodeResponses = nodes.stream().map(this::mapToNodeResponse).collect(Collectors.toList());
        List<EdgeResponse> edgeResponses = edges.stream().map(this::mapToEdgeResponse).collect(Collectors.toList());

        return GraphResponse.builder()
                .nodes(nodeResponses)
                .links(edgeResponses)
                .build();
    }

    private NodeResponse mapToNodeResponse(Node node) {
        return NodeResponse.builder()
                .id(node.getId())
                .type(node.getType())
                .name(node.getName())
                .description(node.getDescription())
                .properties(node.getProperties())
                .build();
    }

    private EdgeResponse mapToEdgeResponse(Edge edge) {
        return EdgeResponse.builder()
                .id(edge.getId())
                .sourceNodeId(edge.getSourceNode().getId())
                .targetNodeId(edge.getTargetNode().getId())
                .type(edge.getType())
                .weight(edge.getWeight())
                .build();
    }
}
