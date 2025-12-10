package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.NodeRequest;
import com.fahribilgen.networkcrm.payload.NodeResponse;

import java.util.List;
import java.util.UUID;

public interface NodeService {
    NodeResponse createNode(NodeRequest nodeRequest, User user);
    NodeResponse updateNode(UUID nodeId, NodeRequest nodeRequest, User user);
    void deleteNode(UUID nodeId, User user);
    NodeResponse getNode(UUID nodeId, User user);
    List<NodeResponse> getAllNodes(User user);
    List<NodeResponse> findSimilarNodes(String query, User user);
}
